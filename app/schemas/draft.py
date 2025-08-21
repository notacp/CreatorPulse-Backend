"""
Draft schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
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


class GeneratedDraftResponse(BaseModel):
    """Schema for generated draft API response."""
    id: str
    user_id: str
    content: str
    source_content_id: Optional[str] = None
    status: str
    feedback_token: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    character_count: Optional[int] = None
    engagement_score: Optional[float] = None
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DraftGenerationRequest(BaseModel):
    """Schema for draft generation request."""
    max_drafts: Optional[int] = Field(default=5, ge=1, le=20, description="Maximum number of drafts to generate")
    content_age_hours: Optional[int] = Field(default=48, ge=1, le=168, description="Use content from the last N hours")
    force_regeneration: Optional[bool] = Field(default=False, description="Force regeneration even if recent drafts exist")


class DraftGenerationResponse(BaseModel):
    """Schema for draft generation response."""
    message: str
    drafts_requested: int
    drafts_generated: int
    processing_async: bool
    task_id: Optional[str] = None
    draft_ids: Optional[List[str]] = None


class DraftStatusResponse(BaseModel):
    """Schema for draft status response."""
    total_drafts: int
    pending_drafts: int
    sent_drafts: int
    recent_content_count: int
    last_generation: Optional[datetime] = None
    status_breakdown: Dict[str, int] = Field(default_factory=dict)