"""
Draft database models.
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, CheckConstraint, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class GeneratedDraft(Base):
    """Generated draft model matching the database schema."""
    
    __tablename__ = "generated_drafts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    source_content_id = Column(UUID(as_uuid=True), ForeignKey("source_content.id", ondelete="SET NULL"))
    status = Column(String, default="pending", nullable=False)
    feedback_token = Column(String, unique=True)
    email_sent_at = Column(DateTime(timezone=True))
    character_count = Column(Integer)
    engagement_score = Column(DECIMAL(3, 1))
    generation_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add check constraint for status
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_draft_status"),
    )
    
    # Relationships
    user = relationship("User", back_populates="drafts")
    feedback = relationship("DraftFeedback", back_populates="draft", cascade="all, delete-orphan")


class DraftFeedback(Base):
    """Draft feedback model matching the database schema."""
    
    __tablename__ = "draft_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("generated_drafts.id", ondelete="CASCADE"), nullable=False)
    feedback_type = Column(String, nullable=False)
    feedback_source = Column(String, default="email", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint("feedback_type IN ('positive', 'negative')", name="check_feedback_type"),
        CheckConstraint("feedback_source IN ('email', 'dashboard')", name="check_feedback_source"),
    )
    
    # Relationship
    draft = relationship("GeneratedDraft", back_populates="feedback")


# Add back reference to User model
from app.models.user import User
User.drafts = relationship("GeneratedDraft", back_populates="user", cascade="all, delete-orphan")