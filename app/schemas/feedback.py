"""
Pydantic schemas for feedback operations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class FeedbackRequest(BaseModel):
    """Request schema for submitting feedback."""
    feedback_type: str = Field(..., pattern="^(positive|negative)$", description="Type of feedback")
    feedback_source: str = Field(default="dashboard", pattern="^(email|dashboard)$", description="Source of feedback")


class FeedbackResponse(BaseModel):
    """Response schema for feedback data."""
    id: UUID
    draft_id: UUID
    feedback_type: str
    feedback_source: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackTokenResponse(BaseModel):
    """Response schema for token-based feedback submission."""
    success: bool
    message: str
    draft_id: UUID
    feedback_type: str
    redirect_url: Optional[str] = None


class FeedbackAnalytics(BaseModel):
    """Analytics schema for feedback statistics."""
    total_feedback: int = Field(..., description="Total feedback received")
    positive_feedback: int = Field(..., description="Number of positive feedback")
    negative_feedback: int = Field(..., description="Number of negative feedback")
    positive_rate: float = Field(..., description="Percentage of positive feedback")
    negative_rate: float = Field(..., description="Percentage of negative feedback")
    email_feedback: int = Field(..., description="Feedback from email")
    dashboard_feedback: int = Field(..., description="Feedback from dashboard")
    email_engagement_rate: float = Field(..., description="Percentage of feedback from email")
    period_days: int = Field(..., description="Analysis period in days")


class EmailDeliveryRequest(BaseModel):
    """Request schema for email delivery."""
    user_id: UUID
    email_type: str = Field(default="daily_drafts", pattern="^(daily_drafts|welcome|verification|notification)$")
    draft_ids: Optional[list[UUID]] = None
    schedule_time: Optional[datetime] = None


class EmailDeliveryResponse(BaseModel):
    """Response schema for email delivery."""
    id: UUID
    user_id: UUID
    email_type: str
    sendgrid_message_id: Optional[str]
    status: str
    draft_ids: Optional[list[UUID]]
    sent_at: datetime
    delivered_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class EmailDeliveryStatusUpdate(BaseModel):
    """Schema for updating email delivery status (from webhooks)."""
    sendgrid_message_id: str
    status: str = Field(..., pattern="^(sent|delivered|bounced|spam|failed)$")
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None