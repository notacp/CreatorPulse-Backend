"""
Source content schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SourceContentBase(BaseModel):
    """Base source content schema."""
    title: Optional[str] = Field(None, description="Content title")
    content: str = Field(..., min_length=10, max_length=10000, description="Content text")
    url: Optional[str] = Field(None, description="Original content URL")
    published_at: Optional[datetime] = Field(None, description="Published timestamp")


class SourceContentCreate(SourceContentBase):
    """Source content creation schema."""
    source_id: str = Field(..., description="Source ID (UUID)")


class SourceContent(SourceContentBase):
    """Source content response schema."""
    id: str = Field(..., description="Content ID (UUID)")
    source_id: str = Field(..., description="Source ID (UUID)")
    processed: bool = Field(default=False, description="Whether content has been processed")
    content_hash: Optional[str] = Field(None, description="Content hash for deduplication")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
