"""
Email delivery and feedback tracking models.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class EmailDeliveryLog(Base):
    """Email delivery log model matching the database schema."""
    
    __tablename__ = "email_delivery_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email_type = Column(String, default="daily_drafts", nullable=False)
    sendgrid_message_id = Column(String)
    status = Column(String, default="sent", nullable=False)
    draft_ids = Column(ARRAY(UUID(as_uuid=True)))
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint(
            "email_type IN ('daily_drafts', 'welcome', 'verification', 'notification')", 
            name="check_email_type"
        ),
        CheckConstraint(
            "status IN ('sent', 'delivered', 'bounced', 'spam', 'failed')", 
            name="check_email_status"
        ),
    )
    
    # Relationship
    user = relationship("User", back_populates="email_logs")


# DraftFeedback model is defined in app.models.draft


# Add back reference to User model
from app.models.user import User
User.email_logs = relationship("EmailDeliveryLog", back_populates="user", cascade="all, delete-orphan")