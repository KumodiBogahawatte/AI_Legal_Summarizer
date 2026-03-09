"""
document_chunk_model.py
SQLAlchemy model for storing document chunks used in RAG retrieval.
Each chunk is a semantically meaningful sub-section of a legal document,
with embeddings and metadata for retrieval and generation.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Position within document
    chunk_index = Column(Integer, nullable=False)          # 0-based order
    char_start = Column(Integer, nullable=True)            # character offset start
    char_end = Column(Integer, nullable=True)              # character offset end

    # Content
    text = Column(Text, nullable=False)
    section_type = Column(String(50), nullable=True)       # FACTS/ISSUES/REASONING/ORDERS/LEGAL_ANALYSIS/JUDGMENT/OTHER

    # Embedding (BGE base: 768-dim)
    embedding = Column(JSON, nullable=True)                # List[float] of length 768

    # Legal metadata per chunk
    article_refs = Column(JSON, nullable=True)             # ["12", "13", "14A"]
    citation_refs = Column(JSON, nullable=True)            # ["(2000) 1 SLR 123", ...]

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    document = relationship("LegalDocument", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index} section={self.section_type}>"


class RAGJob(Base):
    """
    Tracks async ingestion jobs (Celery tasks).
    Frontend polls /api/rag/process/{job_id} using this table.
    """
    __tablename__ = "rag_jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=True, index=True)
    celery_task_id = Column(String(255), nullable=True)
    status = Column(String(20), default="PENDING")         # PENDING / PROCESSING / DONE / FAILED
    progress = Column(Integer, default=0)                  # 0–100
    current_stage = Column(String(100), nullable=True)     # "Extracting text", "Chunking", etc.
    message = Column(Text, nullable=True)                  # Error detail if FAILED
    chunk_count = Column(Integer, default=0)               # Chunks created
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RAGJob id={self.id} doc={self.document_id} status={self.status} progress={self.progress}%>"
