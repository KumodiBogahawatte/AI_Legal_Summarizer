# backend/app/models/processing_log_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class ProcessingLog(Base):
    """Log of all document processing activities"""
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=True)
    
    # Processing details
    operation = Column(String, nullable=False)  # upload, ocr, summarize, analyze, etc.
    status = Column(String, nullable=False)  # started, completed, failed
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Result info
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    processing_metadata = Column(Text, nullable=True)  # JSON string for additional info
    
    # Relationships
    document = relationship("LegalDocument", back_populates="processing_logs")

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class ProcessingLogCreate(BaseModel):
    document_id: Optional[int] = None
    operation: str
    status: str
    error_message: Optional[str] = None
    metadata: Optional[str] = None

class ProcessingLogResponse(BaseModel):
    id: int
    document_id: Optional[int]
    operation: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    success: bool
    
    class Config:
        from_attributes = True
