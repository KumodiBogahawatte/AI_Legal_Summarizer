# backend/app/models/user_model.py

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..db import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), unique=True, nullable=True)  # FK to user_accounts
    device_id = Column(String, nullable=True)  # For anonymous users
    preferred_language = Column(String, default="en")  # en, si, ta
    
    # Relationship
    user = relationship("UserAccount", back_populates="preferences")


# ------------------- Pydantic Schema -------------------

from pydantic import BaseModel

class UserPreferenceCreate(BaseModel):
    user_id: str
    preferred_language: str

class UserPreferenceResponse(BaseModel):
    id: int
    user_id: str
    preferred_language: str

    class Config:
        from_attributes = True
