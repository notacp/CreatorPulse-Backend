"""
Style training database models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class UserStylePost(Base):
    """User style post model matching the database schema."""
    
    __tablename__ = "user_style_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    word_count = Column(Integer)
    character_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))
    
    # Relationship to user
    user = relationship("User", back_populates="style_posts")


class StyleVector(Base):
    """Style vector model for embeddings."""
    
    __tablename__ = "style_vectors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    style_post_id = Column(UUID(as_uuid=True), ForeignKey("user_style_posts.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    # Note: embedding column will be added when pg_vector is set up
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="style_vectors")
    style_post = relationship("UserStylePost", back_populates="vectors")


# Add back references
from app.models.user import User
User.style_posts = relationship("UserStylePost", back_populates="user", cascade="all, delete-orphan")
User.style_vectors = relationship("StyleVector", back_populates="user", cascade="all, delete-orphan")

UserStylePost.vectors = relationship("StyleVector", back_populates="style_post", cascade="all, delete-orphan")