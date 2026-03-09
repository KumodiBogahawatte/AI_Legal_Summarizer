"""
celery_app.py
Celery application and async ingestion task for the RAG pipeline.

Tasks:
- ingest_document_task(document_id): Full RAG ingestion pipeline for a document
  1. Load document from DB
  2. Chunk with LegalChunker
  3. Embed each chunk with EmbeddingService
  4. Save chunks to document_chunks table
  5. Add chunks to FAISS index via RAGServiceV2
  6. Index document in Elasticsearch
  7. Update RAGJob status throughout

Usage (start worker):
  celery -A celery_app worker --loglevel=info
"""

import os
import logging
from datetime import datetime

from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "legal_rag",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["celery_app"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Colombo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


def _update_job(db, job, status: str, progress: int, stage: str, message: str = None):
    """Helper to update RAGJob status in DB."""
    try:
        job.status = status
        job.progress = progress
        job.current_stage = stage
        job.updated_at = datetime.utcnow()
        if message:
            job.message = message
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update RAGJob: {e}")


@celery_app.task(bind=True, name="celery_app.ingest_document_task")
def ingest_document_task(self, document_id: int, job_id: int):
    """
    Full RAG ingestion pipeline for a legal document.

    Steps:
    1. Load document text from DB                    → 10%
    2. Chunk document with LegalChunker              → 25%
    3. Generate embeddings for each chunk            → 60%
    4. Save chunks to document_chunks table          → 75%
    5. Add chunks to FAISS index                     → 90%
    6. Index document in Elasticsearch               → 95%
    7. Mark job DONE                                 → 100%

    Args:
        document_id: ID of the LegalDocument to process
        job_id: ID of the RAGJob row for status tracking
    """
    from app.db import SessionLocal
    from app.models.document_model import LegalDocument
    from app.models.document_chunk_model import DocumentChunk, RAGJob
    from app.services.legal_chunker import LegalChunker
    from app.services.embedding_service import get_embedding_service
    from app.services.rag_service_v2 import get_rag_service_v2
    from app.services.elasticsearch_service import get_elasticsearch_service

    db = SessionLocal()
    job = None

    try:
        job = db.query(RAGJob).filter(RAGJob.id == job_id).first()
        if not job:
            logger.error(f"RAGJob {job_id} not found")
            return

        # ── Step 1: Load document ────────────────────────────────────────────
        _update_job(db, job, "PROCESSING", 5, "Loading document")
        document = db.query(LegalDocument).filter(LegalDocument.id == document_id).first()
        if not document:
            _update_job(db, job, "FAILED", 0, "Failed", f"Document {document_id} not found")
            return

        text = document.cleaned_text or document.raw_text
        if not text or len(text.strip()) < 50:
            _update_job(db, job, "FAILED", 0, "Failed", "Document has insufficient text")
            return

        _update_job(db, job, "PROCESSING", 10, "Text loaded")
        logger.info(f"[Job {job_id}] Loaded document {document_id}: {len(text)} chars")

        # ── Step 2: Chunk document ───────────────────────────────────────────
        _update_job(db, job, "PROCESSING", 15, "Chunking document")
        chunker = LegalChunker(chunk_size=512, overlap=128)
        chunks = chunker.chunk(text)

        if not chunks:
            _update_job(db, job, "FAILED", 0, "Failed", "No chunks created from document text")
            return

        _update_job(db, job, "PROCESSING", 25, f"Chunking complete: {len(chunks)} chunks")
        logger.info(f"[Job {job_id}] Created {len(chunks)} chunks")

        # ── Step 3: Generate embeddings ──────────────────────────────────────
        _update_job(db, job, "PROCESSING", 30, "Generating embeddings")
        embedding_service = get_embedding_service()
        chunk_texts = [c.text for c in chunks]

        # Batch encode
        embeddings = embedding_service.generate_embeddings_batch(chunk_texts, batch_size=16)
        _update_job(db, job, "PROCESSING", 60, "Embeddings generated")
        logger.info(f"[Job {job_id}] Generated {len(embeddings)} embeddings")

        # ── Step 4: Save chunks to DB ────────────────────────────────────────
        _update_job(db, job, "PROCESSING", 65, "Saving chunks to database")

        # Delete old chunks for this document (re-ingestion support)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

        chunk_rows = []
        chunks_for_faiss = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                section_type=chunk.section_type,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                embedding=embedding.tolist(),
                article_refs=chunk.article_refs,
                citation_refs=chunk.citation_refs,
            )
            db.add(db_chunk)
            chunk_rows.append(db_chunk)

        db.flush()  # Get IDs without committing

        # Prepare FAISS data
        for db_chunk in chunk_rows:
            idx = chunk_rows.index(db_chunk)
            chunks_for_faiss.append({
                "chunk_id": db_chunk.id,
                "document_id": document_id,
                "chunk_index": db_chunk.chunk_index,
                "text": db_chunk.text,
                "section_type": db_chunk.section_type,
                "article_refs": db_chunk.article_refs or [],
                "citation_refs": db_chunk.citation_refs or [],
                "embedding": embeddings[idx].tolist(),
                "case_name": document.file_name,
                "court": document.court,
                "year": document.year,
                "case_number": document.case_number,
            })

        # Update document chunk count
        document.chunk_count = len(chunks)
        db.commit()
        _update_job(db, job, "PROCESSING", 75, f"Saved {len(chunks)} chunks to DB")
        logger.info(f"[Job {job_id}] Saved chunks to DB")

        # ── Step 5: Add to FAISS index ───────────────────────────────────────
        _update_job(db, job, "PROCESSING", 80, "Updating vector index")
        rag_service = get_rag_service_v2()
        rag_service.add_chunks_to_index(chunks_for_faiss)
        _update_job(db, job, "PROCESSING", 90, "Vector index updated")
        logger.info(f"[Job {job_id}] Updated FAISS index")

        # ── Step 6: Index in Elasticsearch ──────────────────────────────────
        _update_job(db, job, "PROCESSING", 93, "Indexing in Elasticsearch")
        es_service = get_elasticsearch_service()
        if es_service.available:
            es_service.index_document({
                "document_id": document_id,
                "file_name": document.file_name,
                "case_number": document.case_number,
                "court": document.court,
                "year": document.year,
                "full_text": text[:50000],  # ES has field limits
                "cleaned_text": (document.cleaned_text or "")[:30000],
                "uploaded_at": document.created_at.isoformat() if document.created_at else None,
            })
            logger.info(f"[Job {job_id}] Indexed in Elasticsearch")
        else:
            logger.warning(f"[Job {job_id}] Elasticsearch not available, skipping ES indexing")

        # ── Step 7: Done ─────────────────────────────────────────────────────
        job.chunk_count = len(chunks)
        _update_job(db, job, "DONE", 100, "Processing complete")
        logger.info(f"✅ [Job {job_id}] Ingestion complete: {len(chunks)} chunks created")

    except Exception as e:
        logger.error(f"[Job {job_id}] Ingestion failed: {e}", exc_info=True)
        if job and db:
            try:
                _update_job(db, job, "FAILED", 0, "Failed", str(e))
            except Exception:
                pass
        raise

    finally:
        db.close()
