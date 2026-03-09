# backend/app/models/rights_model.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class DetectedRight(Base):
    __tablename__ = "detected_rights"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"))
    article_number = Column(Integer, nullable=False)  # 10, 11, ..., 18
    matched_text = Column(Text, nullable=False)       # excerpt from judgment
    explanation_en = Column(Text, nullable=True)
    explanation_si = Column(Text, nullable=True)
    explanation_ta = Column(Text, nullable=True)

    detected_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("LegalDocument", back_populates="rights")


# ------------------- Pydantic Schema -------------------

from pydantic import BaseModel

class DetectedRightCreate(BaseModel):
    document_id: int
    article_number: int
    matched_text: str
    explanation_en: str | None = None
    explanation_si: str | None = None
    explanation_ta: str | None = None

class DetectedRightResponse(BaseModel):
    id: int
    document_id: int
    article_number: int
    matched_text: str
    explanation_en: str | None
    explanation_si: str | None
    explanation_ta: str | None

    class Config:
        from_attributes = True
