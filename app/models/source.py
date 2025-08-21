"""
Source database model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Source(Base):
    """Source model matching the database schema."""
    
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    last_checked = Column(DateTime(timezone=True))
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add check constraint for type
    __table_args__ = (
        CheckConstraint("type IN ('rss', 'twitter')", name="check_source_type"),
    )
    
    # Relationship to user
    user = relationship("User", back_populates="sources")


# Add back reference to User model
from app.models.user import User
User.sources = relationship("Source", back_populates="user", cascade="all, delete-orphan")