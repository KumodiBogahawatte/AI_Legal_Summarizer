from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import os
import shutil
import json

from app.db import get_db  # Use absolute import
from app.services.document_ingestion_pipeline import run_ingestion_pipeline


router = APIRouter(prefix="/documents", tags=["Documents"])

@router.options("/upload-sri-lanka")
async def options_upload_sri_lanka():
    return Response(status_code=204)

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load Google Drive PDF mapping once at startup
GDRIVE_PDF_MAP_PATH = os.path.join(os.path.dirname(__file__), '../../../data/gdrive_pdf_urls_recursive.json')
if os.path.exists(GDRIVE_PDF_MAP_PATH):
    with open(GDRIVE_PDF_MAP_PATH, encoding='utf-8') as f:
        GDRIVE_PDF_URLS = json.load(f)
else:
    GDRIVE_PDF_URLS = {}

@router.post("/upload-sri-lanka")
async def upload_sri_lanka_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a Sri Lankan legal PDF (NLR/SLR) and run the full ingestion pipeline.
    Every file is validated; only original NLR/SLR reports are accepted.

    This uses run_ingestion_pipeline as the canonical path, which:
      - extracts & validates text,
      - detects fundamental rights and citations,
      - chunks & embeds for RAG,
      - indexes in Elasticsearch (if available),
      - generates executive/detailed summaries and constitutional analysis.
    """
    file_path = None
    try:
        print(f"[upload-sri-lanka] Incoming file: {getattr(file, 'filename', None)}")
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        # Normalize duplicate .pdf.pdf -> .pdf
        file_name = file.filename.strip()
        while file_name.lower().endswith(".pdf.pdf"):
            file_name = file_name[:-4]  # strip trailing .pdf
        if not file_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        # Save file to disk
        file_path = os.path.join(UPLOAD_DIR, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Read file bytes for pipeline (needed for OCR fallback, etc.)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Run the canonical ingestion pipeline (validation + all downstream stages)
        try:
            print(f"[upload-sri-lanka] Starting run_ingestion_pipeline for: {file_name}")
            document, result = run_ingestion_pipeline(
                db=db,
                file_name=file_name,
                file_path=file_path,
                file_bytes=file_bytes,
            )
            print(f"[upload-sri-lanka] Pipeline completed for: {file_name} (doc_id={document.id})")
        except ValueError as ve:
            # Validation error - return 400 with clear message
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail=str(ve))

        # Prepare response using pipeline outputs
        rights_detected = len(result.get("rights_detected", []))
        citations_found = len(result.get("citations_found", []))

        response = {
            "document_id": document.id,
            "file_name": file_name,
            "rights_detected": rights_detected,
            "citations_detected": citations_found,
            "message": "Document processed successfully",
            "metadata": {
                "court": document.court,
                "year": document.year,
                "case_number": document.case_number,
            },
            "pipeline": {
                "stages_completed": result.get("stages_completed", []),
                "stages_failed": result.get("stages_failed", []),
                "warnings": result.get("warnings", []),
            },
            "text_length": result.get("text_length", 0),
            "extraction_quality": result.get("extraction_quality", "ok"),
        }

        # Add structure analysis if available (DocumentProcessor attaches this in-memory)
        if hasattr(document, "structure_analysis") and document.structure_analysis:
            response["structure_analysis"] = {
                "total_paragraphs": document.structure_analysis.get("total_paragraphs"),
                "sections": document.structure_analysis.get("section_distribution"),
                "classification_methods": document.structure_analysis.get(
                    "method_distribution"
                ),
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/past-case-pdf")
def get_past_case_pdf(path: str):
    """
    Get the Google Drive direct link for a past case PDF by relative path (e.g., 'NLR_All_Volumes/Case1.pdf').
    """
    url = GDRIVE_PDF_URLS.get(path)
    if not url:
        raise HTTPException(status_code=404, detail="PDF not found")
    return {"url": url}