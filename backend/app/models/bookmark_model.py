# backend/app/models/bookmark_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class Bookmark(Base):
    """User bookmarks for documents"""
    __tablename__ = "bookmarks"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'document_id', name='unique_user_document_bookmark'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    
    # Optional bookmark metadata
    notes = Column(Text, nullable=True)
    tags = Column(String, nullable=True)  # Comma-separated tags
    collection_name = Column(String, nullable=True)  # For organizing bookmarks
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserAccount", back_populates="bookmarks")
    document = relationship("LegalDocument", back_populates="bookmarks")

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class BookmarkCreate(BaseModel):
    user_id: int
    document_id: int
    notes: Optional[str] = None
    tags: Optional[str] = None
    collection_name: Optional[str] = None

class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[str] = None
    collection_name: Optional[str] = None

class BookmarkResponse(BaseModel):
    id: int
    user_id: int
    document_id: int
    notes: Optional[str]
    tags: Optional[str]
    collection_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
