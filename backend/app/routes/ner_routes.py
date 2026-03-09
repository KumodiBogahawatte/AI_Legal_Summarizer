# backend/app/routes/ner_routes.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from ..db import get_db
from ..models.document_model import LegalDocument
from ..models.legal_entity_model import LegalEntity
from ..services.legal_ner_service import get_ner_service

router = APIRouter(prefix="/api/ner", tags=["NER"])

# Request/Response Models
class NERRequest(BaseModel):
    text: str
    return_positions: bool = False

class NERResponse(BaseModel):
    entities: Dict[str, List]
    total_entities: int

class EntitySummaryResponse(BaseModel):
    total_entities: int
    entity_counts: Dict[str, int]
    unique_entities: Dict[str, List[str]]

class CaseMetadataResponse(BaseModel):
    case_names: List[str]
    courts: List[str]
    judges: List[str]
    statutes: List[str]
    articles: List[str]
    legal_principles: List[str]
    dates: List[str]
    citations: List[str]

# Endpoints
@router.post("/extract", response_model=NERResponse)
def extract_entities(request: NERRequest):
    """
    Extract legal entities from text
    
    - **text**: Input text to analyze
    - **return_positions**: If true, include character positions of entities
    """
    ner_service = get_ner_service()
    
    if not ner_service.is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="NER model not loaded. Please train the model first."
        )
    
    entities = ner_service.extract_entities(request.text, request.return_positions)
    total = sum(len(ent_list) for ent_list in entities.values())
    
    return {
        "entities": entities,
        "total_entities": total
    }

@router.post("/extract/summary", response_model=EntitySummaryResponse)
def get_entity_summary(request: NERRequest):
    """Get summary statistics about entities in text"""
    ner_service = get_ner_service()
    
    if not ner_service.is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="NER model not loaded"
        )
    
    summary = ner_service.get_entity_summary(request.text)
    return summary

@router.post("/extract/metadata", response_model=CaseMetadataResponse)
def extract_case_metadata(request: NERRequest):
    """Extract structured metadata from case text"""
    ner_service = get_ner_service()
    
    if not ner_service.is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="NER model not loaded"
        )
    
    metadata = ner_service.extract_case_metadata(request.text)
    return metadata

@router.get("/document/{document_id}/entities")
def get_document_entities(document_id: int, db: Session = Depends(get_db)):
    """Get all extracted entities for a document"""
    
    # Check if document exists
    document = db.query(LegalDocument).filter(LegalDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get entities
    entities = db.query(LegalEntity).filter(
        LegalEntity.document_id == document_id
    ).all()
    
    # Group by type
    entities_by_type = {}
    for entity in entities:
        if entity.entity_type not in entities_by_type:
            entities_by_type[entity.entity_type] = []
        
        entities_by_type[entity.entity_type].append({
            "id": entity.id,
            "text": entity.entity_text,
            "start": entity.start_pos,
            "end": entity.end_pos,
            "confidence": entity.confidence,
            "extracted_at": entity.extracted_at
        })
    
    return {
        "document_id": document_id,
        "total_entities": len(entities),
        "entities_by_type": entities_by_type
    }

@router.post("/document/{document_id}/extract")
def extract_and_save_entities(document_id: int, db: Session = Depends(get_db)):
    """
    Extract entities from document and save to database
    """
    ner_service = get_ner_service()
    
    if not ner_service.is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="NER model not loaded"
        )
    
    # Get document
    document = db.query(LegalDocument).filter(LegalDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Extract entities
    text = document.cleaned_text or document.raw_text
    if not text:
        raise HTTPException(status_code=400, detail="Document has no text content")
    
    entities_list = ner_service.extract_entities_list(text)
    
    # Delete existing entities
    db.query(LegalEntity).filter(LegalEntity.document_id == document_id).delete()
    
    # Save new entities
    for entity in entities_list:
        # Get context (50 chars before and after)
        context_start = max(0, entity["start"] - 50)
        context_end = min(len(text), entity["end"] + 50)
        context = text[context_start:context_end]
        
        db_entity = LegalEntity(
            document_id=document_id,
            entity_text=entity["text"],
            entity_type=entity["label"],
            start_pos=entity["start"],
            end_pos=entity["end"],
            context=context,
            confidence=None  # spaCy doesn't provide confidence scores by default
        )
        db.add(db_entity)
    
    db.commit()
    
    return {
        "document_id": document_id,
        "entities_extracted": len(entities_list),
        "message": f"Successfully extracted and saved {len(entities_list)} entities"
    }

@router.get("/status")
def get_ner_status():
    """Check if NER service is available"""
    ner_service = get_ner_service()
    
    return {
        "model_loaded": ner_service.is_model_loaded(),
        "model_path": str(ner_service.model_path) if ner_service.model_path else None,
        "status": "ready" if ner_service.is_model_loaded() else "not_available"
    }
