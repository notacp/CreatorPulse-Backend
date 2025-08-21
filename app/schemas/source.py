"""
Source schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Literal
from datetime import datetime


class SourceBase(BaseModel):
    """Base source schema."""
    type: Literal["rss", "twitter"] = Field(..., description="Source type")
    url: str = Field(..., description="Source URL")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    active: bool = Field(default=True, description="Whether source is active")


class SourceCreate(SourceBase):
    """Source creation schema."""
    pass


class SourceUpdate(BaseModel):
    """Source update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Display name")
    active: Optional[bool] = Field(None, description="Whether source is active")


class Source(SourceBase):
    """Source response schema."""
    id: str = Field(..., description="Source ID (UUID)")
    user_id: str = Field(..., description="User ID (UUID)")
    last_checked: Optional[datetime] = Field(None, description="Last check timestamp")
    error_count: int = Field(default=0, description="Number of consecutive errors")
    last_error: Optional[str] = Field(None, description="Last error message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SourceStatus(BaseModel):
    """Source status schema."""
    status: Literal["active", "inactive", "error"] = Field(..., description="Source status")
    last_error: Optional[str] = Field(None, description="Last error message if status is error")