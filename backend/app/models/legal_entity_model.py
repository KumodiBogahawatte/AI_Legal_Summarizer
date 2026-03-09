# backend/app/models/legal_entity_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class LegalEntity(Base):
    """Store extracted legal entities from documents"""
    __tablename__ = "legal_entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    
    # Entity details
    entity_text = Column(Text, nullable=False)
    entity_type = Column(String, nullable=False)  # CASE_NAME, COURT, JUDGE, etc.
    
    # Position in document
    start_pos = Column(Integer, nullable=True)
    end_pos = Column(Integer, nullable=True)
    
    # Context
    context = Column(Text, nullable=True)  # Surrounding text for context
    
    # Confidence score from NER model
    confidence = Column(Float, nullable=True)
    
    # Timestamps
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("LegalDocument", back_populates="legal_entities")
    
    def __repr__(self):
        return f"<LegalEntity(id={self.id}, type={self.entity_type}, text='{self.entity_text[:30]}...')>"
