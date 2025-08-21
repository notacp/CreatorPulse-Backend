"""
Style training schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class StylePost(BaseModel):
    """Style post schema."""
    id: str = Field(..., description="Post ID (UUID)")
    user_id: str = Field(..., description="User ID (UUID)")
    content: str = Field(..., min_length=50, max_length=3000, description="Post content")
    processed: bool = Field(default=False, description="Whether post has been processed")
    word_count: Optional[int] = Field(None, description="Number of words in content")
    created_at: datetime = Field(..., description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    class Config:
        from_attributes = True


class StyleTrainingRequest(BaseModel):
    """Style training request schema."""
    posts: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=100,
        description="List of post content strings"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "posts": [
                    "Sample LinkedIn post 1 with enough content to meet minimum requirements...",
                    "Sample LinkedIn post 2 demonstrating writing style and voice...",
                ]
            }
        }


class AddStylePostRequest(BaseModel):
    """Add individual style post request schema."""
    content: str = Field(
        ..., 
        min_length=50, 
        max_length=3000,
        description="Post content"
    )


class StyleTrainingStatus(BaseModel):
    """Style training status schema."""
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., 
        description="Training status"
    )
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    total_posts: int = Field(..., ge=0, description="Total number of posts")
    processed_posts: int = Field(..., ge=0, description="Number of processed posts")
    message: Optional[str] = Field(None, description="Status message")


class StyleTrainingJobResponse(BaseModel):
    """Style training job response schema."""
    message: str = Field(..., description="Response message")
    job_id: str = Field(..., description="Job ID for tracking")