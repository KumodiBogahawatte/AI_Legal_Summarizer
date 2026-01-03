from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class RightsViolation(Base):
    __tablename__ = "rights_violations"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    article = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Add relationship
    document = relationship("LegalDocument", back_populates="violations")

# Pydantic schemas
from pydantic import BaseModel

class RightsViolationCreate(BaseModel):
    document_id: int
    article: str
    details: dict = None

class RightsViolationResponse(BaseModel):
    id: int
    document_id: int
    article: str
    details: dict = None
    detected_at: datetime

    class Config:
        from_attributes = True