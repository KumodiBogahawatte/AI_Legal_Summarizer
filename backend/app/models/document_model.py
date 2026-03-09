# backend/app/models/document_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)

    court = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    case_number = Column(String, nullable=True)
    embedding = Column(JSON, nullable=True)  # Document-level embedding (backward compat)
    chunk_count = Column(Integer, default=0)  # Number of RAG chunks created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Summaries (populated by ingestion pipeline or on-demand; migration adds DB columns)
    executive_summary = Column(Text, nullable=True)
    detailed_summary = Column(Text, nullable=True)  # JSON string or plain text

    # Relations
    rights = relationship("DetectedRight", back_populates="document")
    citations = relationship("SLCitation", back_populates="document")
    violations = relationship("RightsViolation", back_populates="document")
    processing_logs = relationship("ProcessingLog", back_populates="document")
    bookmarks = relationship("Bookmark", back_populates="document")
    versions = relationship("DocumentVersion", back_populates="document")
    legal_entities = relationship("LegalEntity", back_populates="document")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


# ------------------- Pydantic Schema -------------------

from pydantic import BaseModel

class LegalDocumentCreate(BaseModel):
    file_name: str
    file_path: str
    raw_text: str | None = None
    cleaned_text: str | None = None

class LegalDocumentResponse(BaseModel):
    id: int
    file_name: str
    court: str | None
    year: int | None
    case_number: str | None
    created_at: datetime

    class Config:
        from_attributes = True
