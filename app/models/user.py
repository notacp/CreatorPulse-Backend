"""
User database model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import time

from app.core.database import Base


class User(Base):
    """User model matching the database schema."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    delivery_time = Column(Time, default=time(8, 0, 0), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())