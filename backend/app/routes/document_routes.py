from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os
import shutil
from app.db import get_db  # Use absolute import
from app.services.document_processor import DocumentProcessor
from app.services.sri_lanka_legal_engine import SriLankaLegalEngine

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-sri-lanka")
async def upload_sri_lanka_document(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files allowed")

        # Save file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Read file bytes for processing
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Process document (includes validation)
        try:
            doc = DocumentProcessor.process_and_save(
                db=db,
                file_name=file.filename,
                file_path=file_path,
                file_bytes=file_bytes,
            )
        except ValueError as ve:
            # Validation error - return 400 with clear message
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(400, str(ve))

        # Legal analysis
        rights = SriLankaLegalEngine.detect_fundamental_rights(
            db=db, doc_id=doc.id, text=doc.cleaned_text or ""
        )

        citations = SriLankaLegalEngine.extract_citations(
            db=db, doc_id=doc.id, text=doc.cleaned_text or ""
        )
        
        # Prepare response
        response = {
            "document_id": doc.id,
            "file_name": file.filename,
            "rights_detected": len(rights),
            "citations_detected": len(citations),
            "message": "Document processed successfully",
            "metadata": {
                "court": doc.court,
                "year": doc.year,
                "case_number": doc.case_number
            }
        }
        
        # Add structure analysis if available
        if hasattr(doc, 'structure_analysis') and doc.structure_analysis:
            response["structure_analysis"] = {
                "total_paragraphs": doc.structure_analysis['total_paragraphs'],
                "sections": doc.structure_analysis['section_distribution'],
                "classification_methods": doc.structure_analysis['method_distribution']
            }

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Upload failed: {str(e)}")