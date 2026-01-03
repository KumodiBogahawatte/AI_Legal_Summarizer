# backend/app/models/case_similarity_model.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class CaseSimilarity(Base):
    """Store precomputed case similarity scores for precedent matching"""
    __tablename__ = "case_similarities"
    
    __table_args__ = (
        Index('idx_source_document', 'source_document_id'),
        Index('idx_similar_document', 'similar_document_id'),
        Index('idx_similarity_score', 'similarity_score'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Documents being compared
    source_document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    similar_document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    
    # Similarity metrics
    similarity_score = Column(Float, nullable=False)  # 0.0 to 1.0
    similarity_method = Column(String, nullable=False)  # cosine, jaccard, bert, etc.
    
    # Additional metadata
    facts_similarity = Column(Float, nullable=True)
    issues_similarity = Column(Float, nullable=True)
    reasoning_similarity = Column(Float, nullable=True)
    
    # Precedent hierarchy
    binding_authority = Column(String, nullable=True)  # binding, persuasive, none
    
    # Timestamps
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    source_document = relationship("LegalDocument", foreign_keys=[source_document_id])
    similar_document = relationship("LegalDocument", foreign_keys=[similar_document_id])

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class CaseSimilarityCreate(BaseModel):
    source_document_id: int
    similar_document_id: int
    similarity_score: float
    similarity_method: str
    facts_similarity: Optional[float] = None
    issues_similarity: Optional[float] = None
    reasoning_similarity: Optional[float] = None
    binding_authority: Optional[str] = None

class CaseSimilarityResponse(BaseModel):
    id: int
    source_document_id: int
    similar_document_id: int
    similarity_score: float
    similarity_method: str
    binding_authority: Optional[str]
    computed_at: datetime
    
    class Config:
        from_attributes = True
