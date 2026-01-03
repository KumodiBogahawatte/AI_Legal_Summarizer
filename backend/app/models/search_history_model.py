# backend/app/models/search_history_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class SearchHistory(Base):
    """Track user search queries"""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True)  # Nullable for anonymous searches
    
    # Search details
    query = Column(Text, nullable=False)
    search_type = Column(String, nullable=False)  # full-text, semantic, advanced
    filters = Column(Text, nullable=True)  # JSON string of applied filters
    
    # Results
    results_count = Column(Integer, default=0)
    clicked_document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=True)
    
    # Timing
    searched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("UserAccount", back_populates="search_history")
    clicked_document = relationship("LegalDocument")

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class SearchHistoryCreate(BaseModel):
    user_id: Optional[int] = None
    query: str
    search_type: str
    filters: Optional[str] = None
    results_count: int = 0

class SearchHistoryResponse(BaseModel):
    id: int
    query: str
    search_type: str
    results_count: int
    searched_at: datetime
    
    class Config:
        from_attributes = True
