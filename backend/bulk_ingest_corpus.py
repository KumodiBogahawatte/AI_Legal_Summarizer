"""
bulk_ingest_corpus.py
─────────────────────
Bulk-ingest all NLR/SLR PDFs from data/raw_documents into the RAG system.

Usage (from backend/ directory):
    python bulk_ingest_corpus.py [--max-docs N] [--skip-existing] [--workers N]

Strategy:
- Extract text from each PDF with pdfplumber
- Chunk, embed, persist chunks to SQLite, update FAISS index
- Each volume is stored as a single LegalDocument entry
- Similar‑cases matching will then work across the whole corpus

Run with --max-docs 10 first to verify before processing all ~120 volumes.
"""

import os
import sys
import re
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Resolve backend root ──────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

RAW_DOCS = BACKEND_DIR.parent / "data" / "raw_documents"

# ── Import app internals after path is set ────────────────────────────────────
os.environ.setdefault("DATABASE_TYPE", "sqlite")
os.environ.setdefault("SQLITE_DB_PATH", str(BACKEND_DIR.parent / "ai_legal_summarizer.db"))


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 200) -> str:
    """Extract text from a PDF using pdfplumber, up to max_pages."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:max_pages]:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_path.name}: {e}")
        return ""


def extract_year_from_name(name: str) -> int:
    """Try to infer year from filename."""
    m = re.search(r'(19[0-9]{2}|20[0-2][0-9])', name)
    if m:
        return int(m.group(1))
    # Volume-based NLR: rough mapping
    m2 = re.search(r'[Vv]ol[.-]?(\d+)', name)
    if m2:
        vol = int(m2.group(1))
        # NLR Vol-1 ≈ 1881, roughly +5 years per volume
        return min(1881 + vol * 4, 1970)
    return 0


def infer_court(text: str) -> str:
    """Quick heuristic for court name."""
    t = text[:3000].upper()
    if "SUPREME COURT" in t:
        return "Supreme Court"
    if "COURT OF APPEAL" in t:
        return "Court of Appeal"
    if "HIGH COURT" in t:
        return "High Court"
    if "DISTRICT COURT" in t:
        return "District Court"
    if "PRIVY COUNCIL" in t:
        return "Privy Council"
    return "Supreme Court"  # default for NLR


def ingest_one(pdf_path: Path, db, rag, embedding_service, chunker,
               skip_existing: bool) -> bool:
    """Ingest a single PDF. Returns True if ingested, False if skipped/failed."""
    from app.models.document_model import LegalDocument
    from app.models.document_chunk_model import DocumentChunk

    # Check if already ingested
    existing = db.query(LegalDocument).filter(
        LegalDocument.file_name == pdf_path.name
    ).first()
    if existing and skip_existing:
        chunks_count = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == existing.id
        ).count()
        if chunks_count > 0:
            logger.info(f"  SKIP (already has {chunks_count} chunks): {pdf_path.name}")
            return False
        elif existing:
            # Re-ingest: existing doc but 0 chunks
            doc = existing
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).delete()
            db.commit()
    else:
        doc = None

    # Extract text
    logger.info(f"  Extracting text: {pdf_path.name}")
    text = extract_text_from_pdf(pdf_path)
    if len(text.strip()) < 200:
        logger.warning(f"  Skipping (too short): {pdf_path.name}")
        return False

    year = extract_year_from_name(pdf_path.name)
    court = infer_court(text)

    if doc is None:
        doc = LegalDocument(
            file_name=pdf_path.name,
            file_path=str(pdf_path),
            raw_text=text[:50000],   # store first 50k chars
            cleaned_text=text[:50000],
            court=court,
            year=year if year > 0 else None,
        )
        db.add(doc)
        db.flush()  # get doc.id

    # Chunk + embed
    logger.info(f"  Chunking: {pdf_path.name}")
    chunks = chunker.chunk(text)
    if not chunks:
        logger.warning(f"  No chunks produced: {pdf_path.name}")
        return False

    chunk_texts = [c.text for c in chunks]
    logger.info(f"  Embedding {len(chunks)} chunks...")
    embeddings = embedding_service.generate_embeddings_batch(chunk_texts, batch_size=32)

    # Save chunks to DB in small batches to minimise write-lock window
    BATCH_SIZE = 20
    db_chunks = []
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[batch_start: batch_start + BATCH_SIZE]
        batch_embs   = embeddings[batch_start: batch_start + BATCH_SIZE]
        for chunk, emb in zip(batch_chunks, batch_embs):
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                section_type=chunk.section_type,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                embedding=emb.tolist(),
                article_refs=chunk.article_refs or [],
                citation_refs=chunk.citation_refs or [],
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        # Small commit per batch → lock held for ~2-5s instead of 60s
        for attempt in range(8):
            try:
                db.commit()
                break
            except Exception as exc:
                if "database is locked" in str(exc).lower() and attempt < 7:
                    import time as _t
                    db.rollback()
                    _t.sleep(3)
                else:
                    raise
        import time as _time
        _time.sleep(0.3)  # yield to other writers between batches

    doc.chunk_count = len(chunks)
    for attempt in range(8):
        try:
            db.commit()
            break
        except Exception as exc:
            if "database is locked" in str(exc).lower() and attempt < 7:
                import time as _t2
                db.rollback()
                _t2.sleep(3)
            else:
                raise


    # Add to FAISS
    chunks_as_dicts = [
        {
            "id": c.id,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "text": c.text,
            "section_type": c.section_type,
            "embedding": c.embedding,
            "article_refs": c.article_refs or [],
            "citation_refs": c.citation_refs or [],
        }
        for c in db_chunks
    ]
    rag.add_chunks_to_index(chunks_as_dicts)

    logger.info(f"  ✅ Ingested {len(chunks)} chunks from {pdf_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Bulk-ingest NLR/SLR corpus")
    parser.add_argument("--max-docs", type=int, default=1000,
                        help="Maximum number of PDFs to ingest (default: all)")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="Skip PDFs already ingested with chunks (default: True)")
    parser.add_argument("--docs-dir", default=str(RAW_DOCS),
                        help="Directory containing raw PDFs")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    if not docs_dir.exists():
        logger.error(f"Raw documents directory not found: {docs_dir}")
        sys.exit(1)

    # Find all PDFs (skip ZIPs — only PDFs for now)
    all_pdfs = sorted(docs_dir.glob("*.pdf"))
    logger.info(f"Found {len(all_pdfs)} PDF files in {docs_dir}")
    all_pdfs = all_pdfs[: args.max_docs]

    # Import services
    from app.db import SessionLocal
    from app.services.rag_service_v2 import get_rag_service_v2
    from app.services.embedding_service import get_embedding_service
    from app.services.legal_chunker import LegalChunker

    db = SessionLocal()
    # Enable WAL on this connection so the FastAPI server can write concurrently
    db.execute(__import__('sqlalchemy').text("PRAGMA journal_mode=WAL"))
    db.execute(__import__('sqlalchemy').text("PRAGMA busy_timeout=30000"))
    db.commit()

    rag = get_rag_service_v2()
    embedding_service = get_embedding_service()
    chunker = LegalChunker()

    ingested = 0
    skipped = 0
    failed = 0

    for i, pdf_path in enumerate(all_pdfs, 1):
        logger.info(f"[{i}/{len(all_pdfs)}] {pdf_path.name}")
        try:
            ok = ingest_one(pdf_path, db, rag, embedding_service, chunker,
                            skip_existing=args.skip_existing)
            if ok:
                ingested += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"  FAILED {pdf_path.name}: {e}")
            failed += 1
            db.rollback()

    db.close()
    logger.info(
        f"\n✅ Done. Ingested: {ingested} | Skipped: {skipped} | Failed: {failed}"
    )
    logger.info(
        f"FAISS index now contains data from {ingested} new volumes."
    )


if __name__ == "__main__":
    main()
