# backend/app/models/document_version_model.py

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class DocumentVersion(Base):
    """Track versions of processed documents and their analyses"""
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    
    # Version info
    version_number = Column(Integer, nullable=False)
    version_type = Column(String, nullable=False)  # text, summary, analysis
    
    # Content snapshot
    content = Column(Text, nullable=True)
    version_metadata = Column(Text, nullable=True)  # JSON string
    
    # Change tracking
    changed_by = Column(String, nullable=True)  # User or system
    change_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("LegalDocument", back_populates="versions")

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class DocumentVersionCreate(BaseModel):
    document_id: int
    version_number: int
    version_type: str
    content: Optional[str] = None
    metadata: Optional[str] = None
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None

class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    version_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True
