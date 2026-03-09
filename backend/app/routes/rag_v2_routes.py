"""
rag_v2_routes.py
RAG API endpoints — upload, process status, retrieve, summarize, constitutional, compare, chat.
All under /api/rag/ prefix (registered in main.py).
"""

import os
import shutil
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.document_model import LegalDocument
from app.models.document_chunk_model import DocumentChunk, RAGJob
from app.services.rag_service_v2 import get_rag_service_v2
from app.services.constitutional_rag_module import get_constitutional_rag
from app.services.precedent_rag_engine import get_precedent_rag
from app.services.llm_generation_service import get_llm_service
from app.services.document_ingestion_pipeline import run_ingestion_pipeline

router = APIRouter(tags=["RAG"])

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Request / Response Models ─────────────────────────────────────────────────

class RetrieveRequest(BaseModel):
    query: str
    doc_id: Optional[int] = None
    top_k: int = 5
    section_filter: Optional[str] = None


class ChatRequest(BaseModel):
    doc_id: int
    question: str
    top_k: int = 5


# ─── Helper: run the full ingestion pipeline in background ──────────────────────


def _run_full_ingestion(job_id: int, file_name: str, file_path: str, file_bytes: bytes):
    """
    Background task that runs the canonical ingestion pipeline for an upload.

    Uses run_ingestion_pipeline to perform:
      - text extraction + validation,
      - rights / citations / NER,
      - chunking + embeddings + FAISS,
      - Elasticsearch indexing,
      - LLM summaries + constitutional RAG.

    Updates the associated RAGJob with status, progress and document_id.
    """
    from app.db import SessionLocal

    db = SessionLocal()
    job = None
    try:
        job = db.query(RAGJob).filter(RAGJob.id == job_id).first()
        if not job:
            return

        job.status = "PROCESSING"
        job.progress = 5
        job.current_stage = "Ingestion pipeline"
        db.commit()

        # Run the unified ingestion pipeline
        document, result = run_ingestion_pipeline(
            db=db,
            file_name=file_name,
            file_path=file_path,
            file_bytes=file_bytes,
        )

        job.document_id = document.id
        job.chunk_count = int(result.get("chunks_created") or 0)
        job.progress = 100
        job.current_stage = "Complete"

        failed_stages = result.get("stages_failed") or []
        if failed_stages:
            job.status = "DONE"
            job.message = f"Pipeline finished with partial failures: {failed_stages}"
        else:
            job.status = "DONE"
            job.message = "Ingestion pipeline completed successfully."

        db.commit()

    except ValueError as ve:
        if job:
            job.status = "FAILED"
            job.progress = 100
            job.current_stage = "Failed"
            job.message = str(ve)
            db.commit()
    except Exception as e:
        if job:
            job.status = "FAILED"
            job.progress = 100
            job.current_stage = "Failed"
            job.message = str(e)
            db.commit()
    finally:
        db.close()


# ─── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/upload")
async def rag_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ):
    """
    Upload a PDF legal document and queue it for full ingestion.
    Every file is validated; only original NLR/SLR reports are accepted.

    This now uses the canonical run_ingestion_pipeline behind a RAGJob:
      - the response returns a job_id immediately,
      - the background task populates document_id and all RAG artefacts,
      - clients should poll /api/rag/process/{job_id} to obtain the document_id.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file with a unique on-disk name
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    file_bytes = await file.read()

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Create RAGJob record (document_id will be filled in by the pipeline)
    job = RAGJob(
        document_id=None,
        status="PENDING",
        progress=0,
        current_stage="Queued",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue ingestion in background using the unified pipeline
    background_tasks.add_task(
        _run_full_ingestion,
        job.id,
        file.filename,
        file_path,
        file_bytes,
    )

    return {
        "job_id": job.id,
        "document_id": job.document_id,
        "file_name": file.filename,
        "status": job.status,
        "message": "Document uploaded. Full ingestion pipeline started.",
    }


@router.get("/process/{job_id}")
def get_process_status(job_id: int, db: Session = Depends(get_db)):
    """Poll ingestion job status. Returns progress 0–100 and current stage."""
    job = db.query(RAGJob).filter(RAGJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job.id,
        "document_id": job.document_id,
        "status": job.status,
        "progress": job.progress,
        "current_stage": job.current_stage,
        "chunk_count": job.chunk_count,
        "message": job.message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("/retrieve")
def rag_retrieve(request: RetrieveRequest, db: Session = Depends(get_db)):
    """
    Retrieve top-k relevant chunks for a query.
    Optionally scoped to a specific document (doc_id).
    """
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    rag = get_rag_service_v2()
    # When doc_id is set, search only within that document (DB) so the user's doc always answers
    chunks = rag.retrieve(
        query=query,
        top_k=request.top_k,
        doc_id_filter=request.doc_id,
        section_filter=request.section_filter,
        db=db if request.doc_id is not None else None,
    )

    return {
        "query": request.query,
        "retrieved_count": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
    }


@router.get("/summarize/{doc_id}")
def rag_summarize(doc_id: int, db: Session = Depends(get_db)):
    """
    Generate RAG-grounded multi-level summaries for a document.
    Returns executive (150w) + detailed (700w) summaries.
    """
    document = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    chunks_in_db = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc_id
    ).order_by(DocumentChunk.chunk_index).all()

    if not chunks_in_db:
        raise HTTPException(
            status_code=404,
            detail="No chunks found. Please ensure the document has been processed via /api/rag/upload"
        )

    # Use retrieval to get the most representative chunks for summarization
    rag = get_rag_service_v2()
    summary_chunks = rag.retrieve(
        query="facts legal issues judicial reasoning judgment orders",
        top_k=8,
        doc_id_filter=doc_id,
    )

    # Fall back to DB chunks if retrieval fails
    if not summary_chunks:
        from app.services.rag_service_v2 import ChunkResult
        summary_chunks = [
            ChunkResult(
                chunk_id=c.id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                text=c.text,
                section_type=c.section_type or "OTHER",
                article_refs=c.article_refs or [],
                citation_refs=c.citation_refs or [],
                similarity=1.0,
                case_name=document.file_name,
                court=document.court,
                year=document.year,
                case_number=document.case_number,
            )
            for c in chunks_in_db[:8]
        ]

    chunks_dicts = [c.to_dict() for c in summary_chunks]
    case_metadata = {
        "case_name": document.file_name,
        "court": document.court or "Unknown",
        "year": document.year or "Unknown",
        "case_number": document.case_number,
    }

    llm = get_llm_service()

    return {
        "document_id": doc_id,
        "case_name": document.file_name,
        "court": document.court,
        "year": document.year,
        "llm_mode": llm.get_mode(),
        "executive_summary": llm.generate_executive_summary(chunks_dicts, case_metadata),
        "detailed_summary": llm.generate_detailed_summary(chunks_dicts, case_metadata),
        "retrieved_chunks": chunks_dicts,
        "total_chunks": len(chunks_in_db),
    }


@router.get("/constitutional/{doc_id}")
def rag_constitutional(doc_id: int, db: Session = Depends(get_db)):
    """
    Run constitutional RAG analysis for a document.
    Matches document text against Chapter III articles (10-18 + 126, 140).
    Uses keyword matching + FAISS semantic matching.
    """
    import re
    document = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    # ── Use full document text directly ─────────────────────────────────────
    full_text = document.cleaned_text or document.raw_text or ""
    if not full_text.strip():
        raise HTTPException(status_code=422, detail="Document has no extracted text.")

    # ── Match against constitutional articles (keyword + FAISS) ─────────────
    const_rag = get_constitutional_rag()

    # Run matching on first 8000 chars of full text (covers headnotes + facts + reasoning)
    search_text = full_text[:8000]
    matched_articles = const_rag.match_articles(search_text, top_k=8)

    # If text is long, also search the final section (judgment/order section)
    if len(full_text) > 10000:
        tail_matches = const_rag.match_articles(full_text[-4000:], top_k=5)
        seen_arts = {a["article_number"] for a in matched_articles}
        for m in tail_matches:
            if m["article_number"] not in seen_arts:
                matched_articles.append(m)
                seen_arts.add(m["article_number"])

    # Sort final results by similarity descending
    matched_articles = sorted(matched_articles, key=lambda x: x["similarity"], reverse=True)

    # ── Build safe chunk excerpts from DB ────────────────────────────────────
    from app.models.document_chunk_model import DocumentChunk
    db_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc_id
    ).limit(6).all()

    chunks_dicts = [
        {"text": c.text, "section": getattr(c, "section_type", ""), "document_id": doc_id}
        for c in db_chunks
        if c.text
    ]

    # ── Generate LLM analysis ────────────────────────────────────────────────
    llm = get_llm_service()
    analysis_text = llm.generate_constitutional_analysis(chunks_dicts, matched_articles)

    # ── Detect constitutional keywords for has_constitutional_issues flag ────
    has_issues = len(matched_articles) > 0 or bool(
        re.search(
            r'fundamental rights?|article\s+1[0-8]|article\s+126|habeas corpus'
            r'|freedom of speech|freedom of assembly|right to equality|arbitrary arrest',
            full_text[:6000],
            re.IGNORECASE,
        )
    )

    return {
        "document_id": doc_id,
        "case_name": document.file_name,
        "court": document.court,
        "year": document.year,
        "constitutional_analysis": analysis_text,
        "matched_articles": matched_articles,
        "retrieved_chunks": chunks_dicts[:4],
        "has_constitutional_issues": has_issues,
        "total_articles_matched": len(matched_articles),
    }




@router.get("/compare/{doc_id}")
def rag_compare(
    doc_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
):
    """
    Find and compare top-k similar precedent cases using chunk-level RAG.
    Returns structured comparison per case.
    """
    document = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    precedent_engine = get_precedent_rag()
    similar_cases = precedent_engine.find_similar_cases(
        document_id=doc_id,
        source_court=document.court,
        source_year=document.year,
        top_k=top_k,
    )

    return {
        "document_id": doc_id,
        "source_case": document.file_name,
        "source_court": document.court,
        "source_year": document.year,
        "similar_cases": similar_cases,
        "total_compared": len(similar_cases),
    }


@router.post("/chat")
def rag_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Q&A over a specific case. Retrieves relevant chunks then generates a grounded answer.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    document = db.query(LegalDocument).filter(LegalDocument.id == request.doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {request.doc_id} not found")

    rag = get_rag_service_v2()
    retrieved = rag.retrieve(
        query=request.question,
        top_k=request.top_k,
        doc_id_filter=request.doc_id,
    )

    if not retrieved:
        return {
            "question": request.question,
            "answer": "No relevant content found in this document for your query.",
            "retrieved_chunks": [],
        }

    chunks_dicts = [c.to_dict() for c in retrieved]
    llm = get_llm_service()
    answer = llm.answer_question(request.question, chunks_dicts)

    return {
        "question": request.question,
        "answer": answer,
        "doc_id": request.doc_id,
        "case_name": document.file_name,
        "retrieved_chunks": chunks_dicts,
        "llm_mode": llm.get_mode(),
    }
