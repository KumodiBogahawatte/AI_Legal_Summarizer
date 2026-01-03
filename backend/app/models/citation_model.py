# backend/app/models/citation_model.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class SLCitation(Base):
    __tablename__ = "sl_citations"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"))

    citation_text = Column(String, nullable=False)   # entire citation line
    year = Column(Integer, nullable=True)
    reporter = Column(String, nullable=True)         # NLR / SLR / SC Appeal etc.
    page = Column(Integer, nullable=True)

    extracted_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("LegalDocument", back_populates="citations")


# ------------------- Pydantic Schema -------------------

from pydantic import BaseModel

class SLCitationCreate(BaseModel):
    document_id: int
    citation_text: str
    year: int | None = None
    reporter: str | None = None
    page: int | None = None

class SLCitationResponse(BaseModel):
    id: int
    document_id: int
    citation_text: str
    year: int | None
    reporter: str | None
    page: int | None

    class Config:
        from_attributes = True
