# backend/app/models/audit_log_model.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db import Base

class AuditLog(Base):
    """Audit trail for security and compliance"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True)
    username = Column(String, nullable=True)  # Store username for reference
    ip_address = Column(String, nullable=True)
    
    # What
    action = Column(String, nullable=False)  # login, upload, delete, search, etc.
    resource_type = Column(String, nullable=True)  # document, user, system
    resource_id = Column(Integer, nullable=True)
    
    # Details
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)  # For update operations
    new_value = Column(Text, nullable=True)  # For update operations
    
    # When
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Result
    status = Column(String, nullable=False)  # success, failure, warning
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("UserAccount")

# Pydantic Schema
from pydantic import BaseModel
from typing import Optional

class AuditLogCreate(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    description: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None

class AuditLogResponse(BaseModel):
    id: int
    username: Optional[str]
    action: str
    resource_type: Optional[str]
    timestamp: datetime
    status: str
    
    class Config:
        from_attributes = True
