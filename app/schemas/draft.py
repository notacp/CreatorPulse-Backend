"""
Draft schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal


class DraftBase(BaseModel):
    """Base draft schema."""
    content: str = Field(..., min_length=50, max_length=3000, description="Draft content")
    status: Literal["pending", "approved", "rejected"] = Field(
        default="pending", 
        description="Draft status"
    )


class Draft(DraftBase):
    """Draft response schema."""
    id: str = Field(..., description="Draft ID (UUID)")
    user_id: str = Field(..., description="User ID (UUID)")
    source_content_id: Optional[str] = Field(None, description="Source content ID (UUID)")
    feedback_token: Optional[str] = Field(None, description="Feedback token")
    email_sent_at: Optional[datetime] = Field(None, description="Email sent timestamp")
    character_count: Optional[int] = Field(None, description="Character count")
    engagement_score: Optional[Decimal] = Field(None, description="Engagement score (0.0-10.0)")
    source_name: Optional[str] = Field(None, description="Source name for display")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class GenerateDraftsRequest(BaseModel):
    """Generate drafts request schema."""
    force: bool = Field(
        default=False, 
        description="Force generation even if recent drafts exist"
    )


class GenerateDraftsResponse(BaseModel):
    """Generate drafts response schema."""
    message: str = Field(..., description="Response message")
    drafts_generated: int = Field(..., ge=0, description="Number of drafts generated")