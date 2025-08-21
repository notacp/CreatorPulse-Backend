"""
Source content database model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class SourceContent(Base):
    """Source content model matching the database schema."""
    
    __tablename__ = "source_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    title = Column(String)
    content = Column(Text, nullable=False)
    url = Column(String)
    published_at = Column(DateTime(timezone=True))
    processed = Column(Boolean, default=False, nullable=False)
    content_hash = Column(String, index=True)  # For deduplication
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    source = relationship("Source", back_populates="content")
    drafts = relationship("GeneratedDraft", back_populates="source_content")


# Add back reference to Source model
from app.models.source import Source
Source.content = relationship("SourceContent", back_populates="source", cascade="all, delete-orphan")

# Add back reference to GeneratedDraft model  
from app.models.draft import GeneratedDraft
GeneratedDraft.source_content = relationship("SourceContent", back_populates="drafts")
