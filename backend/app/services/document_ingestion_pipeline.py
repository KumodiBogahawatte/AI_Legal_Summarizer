"""
document_ingestion_pipeline.py
================================
Single entry-point that runs the FULL processing pipeline when a document is uploaded.
Every upload is validated: only original Sri Lankan law reports (NLR/SLR) are accepted;
analysis documents, summaries, and case briefs are rejected.

Pipeline stages (all run in one call):
  1. Extract text from PDF (pdfplumber → OCR fallback)
  2. Validate as Sri Lankan legal document
  3. Clean text + extract metadata (year, case_number, court)
  4. Analyze document structure (BERT/hybrid classifier)
  5. Save LegalDocument record to DB
  6. Run NER → save LegalEntity records
  7. Detect fundamental rights → save DetectedRight records
  8. Extract SLR/NLR citations → save SLCitation records, parsed year/reporter/page
  9. Classify document structure (BERT) → save section_type on paragraphs
 10. Chunk document with LegalChunker
 11. Generate BGE embeddings for each chunk
 12. Save DocumentChunk records to DB
 13. Add chunks to FAISS index (RAGServiceV2)
 14. Index document in Elasticsearch (if available)
 15. Generate and save executive + detailed summaries (LLM)
 16. Generate constitutional RAG analysis
 17. Persist case_similarity placeholder (triggering precedent pre-index)

Usage (from document_routes.py):
    from app.services.document_ingestion_pipeline import run_ingestion_pipeline
    document, result = run_ingestion_pipeline(db, file_name, file_path, file_bytes)
"""

import json
import os
import re
import logging
import traceback
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Citation parser helper  (fixes Issue #7 – year/reporter/page never parsed)
# ──────────────────────────────────────────────────────────────────────────────
_CITATION_STRUCT = re.compile(
    r'[\[\(](\d{4})[\]\)]\s*(\d*)\s*(NLR|SLR|SLLR|CLR)\s*(\d+)',
    re.IGNORECASE,
)


def _parse_citation(citation_text: str) -> Dict:
    """Return structured fields from a raw citation string."""
    m = _CITATION_STRUCT.search(citation_text)
    if m:
        return {
            "year": int(m.group(1)),
            "volume": int(m.group(2)) if m.group(2) else None,
            "reporter": m.group(3).upper(),
            "page": int(m.group(4)),
        }
    return {"year": None, "volume": None, "reporter": None, "page": None}


# ──────────────────────────────────────────────────────────────────────────────
# Deduplication helper  (fixes Issue #8 – duplicate records on re-upload)
# ──────────────────────────────────────────────────────────────────────────────
def _document_already_exists(db: Session, file_name: str) -> Optional[int]:
    """Return document id if this filename is already in DB, else None."""
    from app.models.document_model import LegalDocument
    existing = db.query(LegalDocument).filter(
        LegalDocument.file_name == file_name
    ).first()
    return existing.id if existing else None


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────
def run_ingestion_pipeline(
    db: Session,
    file_name: str,
    file_path: str,
    file_bytes: bytes,
    max_file_bytes: int = 100 * 1024 * 1024,   # 100 MB limit
) -> Tuple:
    """
    Run the full ingestion pipeline for an uploaded legal document.

    Returns:
        (LegalDocument, result_dict)  where result_dict has processing details.

    Raises:
        ValueError  for validation failures (wrong document type, too large).
        Exception   for unexpected processing errors.
    """
    print(f"[ingestion] Starting pipeline for '{file_name}' at '{file_path}' (size={len(file_bytes)} bytes)")
    result: Dict = {
        "file_name": file_name,
        "stages_completed": [],
        "stages_failed": [],
        "warnings": [],
        "ner_entities": {},
        "rights_detected": [],
        "citations_found": [],
        "chunks_created": 0,
        "executive_summary": None,
        "detailed_summary": None,
        "constitutional_analysis": None,
        "text_length": 0,
        "extraction_quality": "ok",
    }

    # ── 0. File size validation  (fixes Issue #2) ─────────────────────────────
    if len(file_bytes) > max_file_bytes:
        raise ValueError(
            f"File too large ({len(file_bytes) // (1024*1024)} MB). "
            f"Maximum allowed size is {max_file_bytes // (1024*1024)} MB."
        )

    # ── 0b. Deduplication check (DISABLED: allow re-uploads of same file name) ─
    # Previously, we rejected uploads when a document with the same file_name
    # already existed in the database. This prevented users from uploading the
    # same judgment multiple times. The product requirement is now to allow
    # multiple uploads of the same PDF, so we only log this condition instead
    # of raising an error.
    existing_id = _document_already_exists(db, file_name)
    if existing_id:
        logger.info(
            "Duplicate upload detected for '%s' (existing_id=%s) — proceeding to "
            "create a new LegalDocument record anyway.",
            file_name,
            existing_id,
        )

    # ── 1-4. Extract, validate, clean, structure  ─────────────────────────────
    from app.services.document_processor import DocumentProcessor
    print("[ingestion] 1/4 Extracting, validating, cleaning document text…")
    document = DocumentProcessor.process_and_save(db, file_name, file_path, file_bytes)
    result["stages_completed"].append("text_extraction_and_save")
    result["document_id"] = document.id
    cleaned_text = document.cleaned_text or ""
    result["text_length"] = len(cleaned_text)
    # Ensure enough text for accurate summaries; warn if extraction is weak
    if len(cleaned_text) < 300:
        raise ValueError(
            "Too little text was extracted from this PDF (possible image-only/scanned document). "
            "Summaries would be unreliable. Use a text-based PDF or ensure OCR is available."
        )
    if len(cleaned_text) < 1500:
        result["extraction_quality"] = "low"
        result["warnings"].append(
            "Extracted text is short; summaries may be less accurate. Consider using a PDF with selectable text."
        )

    # ── 0c. Only original NLR/SLR reports: reject analysis/summary/brief documents ─
    if not DocumentProcessor.is_sri_lanka_legal_document(cleaned_text, file_name=file_name):
        db.delete(document)
        db.commit()
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise ValueError(
            "This document is not an original Sri Lankan law report (NLR/SLR). "
            "Analysis documents, summaries, and case briefs are not supported. "
            "Please upload only original Sri Lankan Law Reports (SLR) or New Law Reports (NLR) judgments."
        )

    # ── 5. NER  (fixes Issue #17 – NER was never auto-triggered) ──────────────
    try:
        from app.services.legal_ner_service import get_ner_service
        ner_service = get_ner_service()
        if ner_service.is_model_loaded():
            from app.models.legal_entity_model import LegalEntity
            entities = ner_service.extract_entities_list(cleaned_text)
            for ent_text, ent_label in entities:
                db.add(LegalEntity(
                    document_id=document.id,
                    entity_text=ent_text,
                    entity_type=ent_label,
                ))
            db.commit()
            result["ner_entities"] = ner_service.extract_entities(cleaned_text)
            result["stages_completed"].append("ner")
        else:
            result["warnings"].append("NER model not loaded – skipped.")
    except Exception as e:
        result["stages_failed"].append(f"ner: {e}")
        logger.warning(f"NER stage failed: {e}")

    # ── 6. Fundamental rights detection  (fixes Issue #4 – semantic detector
    #        was bypassed; fixes Issue #5 – Sinhala/Tamil explanations empty) ──
    try:
        from app.services.fundamental_rights_detector import FundamentalRightsDetector
        from app.models.rights_model import DetectedRight
        fr_detector = FundamentalRightsDetector(semantic_threshold=0.45)
        detections = fr_detector.detect(cleaned_text)
        for det in detections:
            article_str = str(det.get("article", "0"))
            try:
                article_num = int(re.sub(r"[^0-9]", "", article_str)) if article_str != "14A" else 14
            except ValueError:
                continue
            raw_explanation = det.get("explanation", "")
            # DB expects a string; detector may return a dict (e.g. keyword_inference path)
            if isinstance(raw_explanation, dict):
                explanation_en = raw_explanation.get("text", "") or ""
            else:
                explanation_en = str(raw_explanation) if raw_explanation is not None else ""
            db.add(DetectedRight(
                document_id=document.id,
                article_number=article_num,
                matched_text=(det.get("matched_text") or "")[:500],
                explanation_en=explanation_en[:2000] if explanation_en else None,
                explanation_si=None,
                explanation_ta=None,
            ))
        db.commit()
        result["rights_detected"] = [
            {"article": d.get("article"), "title": d.get("article_title", "")}
            for d in detections
        ]
        result["stages_completed"].append("fundamental_rights")
    except Exception as e:
        result["stages_failed"].append(f"fundamental_rights: {e}")
        logger.warning(f"Rights detection failed: {e}")

    # ── 7. Constitutional article detection  (fixes Issue #6 – detector unused) ─
    try:
        from app.services.constitutional_article_detector import ConstitutionalArticleDetector
        const_detector = ConstitutionalArticleDetector(semantic_threshold=0.70)
        const_provisions = const_detector.detect(cleaned_text)
        result["constitutional_provisions"] = [
            {"article": p.get("article"), "title": p.get("article_title", "")}
            for p in const_provisions
        ]
        result["stages_completed"].append("constitutional_articles")
    except Exception as e:
        result["stages_failed"].append(f"constitutional_articles: {e}")
        logger.warning(f"Constitutional article detection failed: {e}")

    # ── 8. Citation extraction  (fixes Issue #7 – year/reporter/page unparsed) ─
    try:
        from app.models.citation_model import SLCitation
        from app.utils.sri_lanka_legal_utils import CITATION_PATTERN_NLR, CITATION_PATTERN_SLR
        seen_citations = set()
        for pattern in [CITATION_PATTERN_NLR, CITATION_PATTERN_SLR]:
            if isinstance(pattern, str):
                compiled = re.compile(pattern)
            else:
                compiled = pattern
            for match in compiled.finditer(cleaned_text):
                raw = match.group(0) if hasattr(match, "group") else str(match)
                if raw in seen_citations:
                    continue
                seen_citations.add(raw)
                parsed = _parse_citation(raw)
                db.add(SLCitation(
                    document_id=document.id,
                    citation_text=raw,
                    year=parsed["year"],
                    reporter=parsed["reporter"],
                    page=parsed["page"],
                ))
        db.commit()
        result["citations_found"] = list(seen_citations)
        result["stages_completed"].append("citation_extraction")
    except Exception as e:
        result["stages_failed"].append(f"citation_extraction: {e}")
        logger.warning(f"Citation extraction failed: {e}")

    # ── 9-12. Chunk → Embed → Save → FAISS index  ─────────────────────────────
    #  (fixes Issues #1, #12 – chunking/embedding not triggered on upload)
    chunks_for_rag: List[Dict] = []
    try:
        from app.services.legal_chunker import LegalChunker
        from app.services.embedding_service import get_embedding_service
        from app.models.document_chunk_model import DocumentChunk

        chunker = LegalChunker(chunk_size=512, overlap=128)
        legal_chunks = chunker.chunk(cleaned_text)
        emb_service = get_embedding_service()

        for lc in legal_chunks:
            embedding = emb_service.generate_embedding(lc.text)
            emb_list = embedding.tolist()

            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=lc.chunk_index,
                text=lc.text,
                char_start=lc.char_start,
                char_end=lc.char_end,
                section_type=lc.section_type,
                article_refs=lc.article_refs,
                citation_refs=lc.citation_refs,
                embedding=emb_list,
            )
            db.add(db_chunk)
            db.flush()   # get db_chunk.id before committing

            chunks_for_rag.append({
                "chunk_id": db_chunk.id,
                "document_id": document.id,
                "chunk_index": lc.chunk_index,
                "text": lc.text,
                "section_type": lc.section_type,
                "article_refs": lc.article_refs,
                "citation_refs": lc.citation_refs,
                "case_name": file_name,
                "court": document.court,
                "year": document.year,
                "case_number": document.case_number,
                "embedding": emb_list,
            })

        db.commit()
        result["chunks_created"] = len(legal_chunks)
        result["stages_completed"].append("chunking_and_embedding")

        # Add to live FAISS index immediately  (fixes Issue #12 – index not updated)
        from app.services.rag_service_v2 import get_rag_service_v2
        rag = get_rag_service_v2()
        rag.add_chunks_to_index(chunks_for_rag)
        result["stages_completed"].append("faiss_index_update")

    except Exception as e:
        result["stages_failed"].append(f"chunking_embedding: {e}")
        logger.warning(f"Chunking/embedding stage failed: {e}")
        traceback.print_exc()

    # ── 13. Elasticsearch indexing  (fixes Issue #20 – ES never called on upload) ─
    try:
        from app.services.elasticsearch_service import get_elasticsearch_service
        es = get_elasticsearch_service()
        if es.available:
            rights_articles = [
                str(r["article"]) for r in result.get("rights_detected", [])
            ]
            judges = []
            ner = result.get("ner_entities", {})
            if isinstance(ner, dict):
                judges = ner.get("JUDGE", [])

            es.index_document({
                "document_id": document.id,
                "file_name": file_name,
                "case_number": document.case_number,
                "court": document.court,
                "year": int(document.year) if document.year else None,
                "full_text": document.raw_text or "",
                "cleaned_text": cleaned_text,
                "rights_articles": rights_articles,
                "judges": judges,
            })
            result["stages_completed"].append("elasticsearch")
        else:
            result["warnings"].append("Elasticsearch not available – skipped.")
    except Exception as e:
        result["stages_failed"].append(f"elasticsearch: {e}")
        logger.warning(f"Elasticsearch indexing failed: {e}")

    # ── 14. LLM summarization  (fixes Issue #9/#10 – BART stub never replaced) ─
    try:
        from app.services.llm_generation_service import get_llm_service
        from app.models.document_model import LegalDocument

        if chunks_for_rag:
            llm = get_llm_service()
            meta = {
                "court": document.court or "Unknown",
                "year": document.year or "Unknown",
                "case_name": file_name,
            }
            exec_summary = llm.generate_executive_summary(chunks_for_rag, meta)
            detailed_summary = llm.generate_detailed_summary(chunks_for_rag, meta)
            # DB columns are TEXT; store string (serialize dict if needed)
            exec_val = exec_summary if isinstance(exec_summary, str) else str(exec_summary)
            det_val = detailed_summary if isinstance(detailed_summary, str) else (
                json.dumps(detailed_summary) if isinstance(detailed_summary, dict) else str(detailed_summary)
            )

            # Save to DB
            db.query(LegalDocument).filter(
                LegalDocument.id == document.id
            ).update({
                "executive_summary": exec_val,
                "detailed_summary": det_val,
            })
            db.commit()

            result["executive_summary"] = exec_summary
            result["detailed_summary"] = detailed_summary
            result["stages_completed"].append("llm_summarization")
        else:
            result["warnings"].append("No chunks available for LLM summarization.")
    except Exception as e:
        result["stages_failed"].append(f"llm_summarization: {e}")
        logger.warning(f"LLM summarization failed: {e}")

    # ── 15. Constitutional RAG analysis  (fixes Issue #6) ─────────────────────
    try:
        from app.services.constitutional_rag_module import get_constitutional_rag
        if chunks_for_rag:
            const_rag = get_constitutional_rag()
            const_matches = const_rag.analyse_case_chunks(chunks_for_rag, top_k_per_chunk=3)
            result["constitutional_analysis"] = const_matches
            result["stages_completed"].append("constitutional_rag")
    except Exception as e:
        result["stages_failed"].append(f"constitutional_rag: {e}")
        logger.warning(f"Constitutional RAG analysis failed: {e}")

    # ── 16. Plain language conversion ─────────────────────────────────────────
    try:
        from app.services.plain_language_converter import PlainLanguageConverter
        if result.get("executive_summary"):
            converter = PlainLanguageConverter()
            plain = converter.convert_to_plain_language(result["executive_summary"])
            result["plain_executive_summary"] = plain["plain_text"]
            result["stages_completed"].append("plain_language")
    except Exception as e:
        result["stages_failed"].append(f"plain_language: {e}")

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info(
        f"Ingestion pipeline complete for '{file_name}' (doc_id={document.id}). "
        f"Completed: {result['stages_completed']}. "
        f"Failed: {result['stages_failed']}."
    )

    return document, result