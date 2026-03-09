"""
build_rag_index.py
==================
One-time script: chunk, embed and index all existing documents that
have cleaned_text but no DocumentChunk records.

Run from the backend directory:
    python scripts/build_rag_index.py

Flags:
    --limit N      Only process first N documents (for testing)
    --doc-id N     Process only one specific document
    --force        Re-process documents that already have chunks
"""

import sys
import argparse
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from app.models.document_chunk_model import DocumentChunk
from app.services.legal_chunker import LegalChunker
from app.services.embedding_service import get_embedding_service


def process_document(db, doc, emb_service, chunker, force=False):
    existing = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id
    ).count()

    if existing > 0 and not force:
        print(f"  ⏭  Doc {doc.id} already has {existing} chunks — skipping")
        return 0

    text = doc.cleaned_text or doc.raw_text or ""
    if len(text.strip()) < 100:
        print(f"  ⚠️  Doc {doc.id} has insufficient text — skipping")
        return 0

    if existing > 0 and force:
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id
        ).delete(synchronize_session="fetch")
        db.flush()

    try:
        chunks = chunker.chunk(text)
        for lc in chunks:
            embedding = emb_service.generate_embedding(lc.text)
            db.add(DocumentChunk(
                document_id=doc.id,
                chunk_index=lc.chunk_index,
                text=lc.text,
                char_start=lc.char_start,
                char_end=lc.char_end,
                section_type=lc.section_type,
                article_refs=lc.article_refs,
                citation_refs=lc.citation_refs,
                embedding=embedding.tolist(),
            ))
        db.commit()
        print(f"  ✅ Doc {doc.id} ({doc.file_name[:50]!r}) — {len(chunks)} chunks")
        return len(chunks)
    except Exception as e:
        db.rollback()
        print(f"  ❌ Doc {doc.id} failed: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--doc-id", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    chunker = LegalChunker(chunk_size=512, overlap=128)
    emb_service = get_embedding_service()

    try:
        if args.doc_id:
            docs = db.query(LegalDocument).filter(
                LegalDocument.id == args.doc_id
            ).all()
        else:
            query = db.query(LegalDocument)
            if not args.force:
                # Only documents with no chunks
                from sqlalchemy import select
                chunked_ids = select(DocumentChunk.document_id).distinct()
                query = query.filter(~LegalDocument.id.in_(chunked_ids))
            if args.limit:
                query = query.limit(args.limit)
            docs = query.all()

        print(f"\n📚 Processing {len(docs)} documents...\n")
        total_chunks = 0
        for i, doc in enumerate(docs, 1):
            print(f"[{i}/{len(docs)}] Doc {doc.id}:")
            total_chunks += process_document(db, doc, emb_service, chunker, force=args.force)

        print(f"\n✅ Done. Total chunks created: {total_chunks}")

        # Rebuild FAISS index from DB
        print("\n🔄 Rebuilding FAISS index from database...")
        try:
            from app.services.rag_service_v2 import get_rag_service_v2
            rag = get_rag_service_v2()
            rag.invalidate_index()
            total_indexed = rag.index.ntotal if rag.index else 0
            print(f"✅ FAISS index rebuilt: {total_indexed} vectors indexed")
        except Exception as e:
            print(f"⚠️  FAISS rebuild failed: {e}")
            print("   Install faiss: pip install faiss-cpu")

    finally:
        db.close()


if __name__ == "__main__":
    main()
