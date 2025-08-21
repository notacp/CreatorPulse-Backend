"""
Feedback schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class FeedbackRequest(BaseModel):
    """Feedback request schema."""
    feedback_type: Literal["positive", "negative"] = Field(
        ..., 
        description="Type of feedback"
    )


class FeedbackResponse(BaseModel):
    """Feedback response schema."""
    id: str = Field(..., description="Feedback ID (UUID)")
    draft_id: str = Field(..., description="Draft ID (UUID)")
    feedback_type: Literal["positive", "negative"] = Field(..., description="Type of feedback")
    feedback_source: Literal["email", "dashboard"] = Field(
        default="email", 
        description="Source of feedback"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True