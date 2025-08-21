"""
Source schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class SourceBase(BaseModel):
    """Base source schema."""
    type: Literal["rss", "twitter"] = Field(..., description="Source type")
    url: str = Field(..., description="Source URL or Twitter handle")
    name: Optional[str] = Field(None, description="Custom name for the source")
    active: bool = Field(default=True, description="Whether source is active")


class SourceCreate(SourceBase):
    """Source creation schema."""
    
    @validator('url')
    def validate_url(cls, v, values):
        """Validate URL format based on source type."""
        source_type = values.get('type')
        
        if source_type == 'twitter':
            # Twitter handle validation
            if not v.startswith('@'):
                v = f"@{v}"
            # Remove @ for validation
            handle = v[1:] if v.startswith('@') else v
            if not handle.replace('_', '').isalnum() or len(handle) > 15:
                raise ValueError('Invalid Twitter handle format')
        elif source_type == 'rss':
            # Basic URL validation for RSS feeds
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError('RSS feed URL must start with http:// or https://')
        
        return v


class SourceUpdate(BaseModel):
    """Source update schema."""
    name: Optional[str] = Field(None, description="Custom name for the source")
    url: Optional[str] = Field(None, description="Source URL or Twitter handle")
    active: Optional[bool] = Field(None, description="Whether source is active")
    type: Optional[Literal["rss", "twitter"]] = Field(None, description="Source type")


class Source(SourceBase):
    """Source response schema."""
    id: UUID = Field(..., description="Source ID")
    user_id: UUID = Field(..., description="User ID who owns the source")
    last_checked: Optional[datetime] = Field(None, description="Last time source was checked")
    error_count: int = Field(default=0, description="Number of consecutive errors")
    created_at: datetime = Field(..., description="Source creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SourceStatus(BaseModel):
    """Source health status schema."""
    source_id: UUID = Field(..., description="Source ID")
    is_healthy: bool = Field(..., description="Whether source is currently healthy")
    last_checked: datetime = Field(..., description="When the check was performed")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    content_count: Optional[int] = Field(None, description="Number of items found in source")


class SourceValidationResult(BaseModel):
    """Result of source validation."""
    is_valid: bool = Field(..., description="Whether source is valid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    suggested_name: Optional[str] = Field(None, description="Suggested name for the source")
    
    
class SourceHealthCheck(BaseModel):
    """Result of source health check."""
    is_healthy: bool = Field(..., description="Whether source is healthy")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds") 
    content_count: Optional[int] = Field(None, description="Number of items found")
    last_content_date: Optional[datetime] = Field(None, description="Date of most recent content")