"""
Common Pydantic schemas that match frontend TypeScript interfaces.
"""
from typing import Generic, TypeVar, Optional, Any, Dict, List
from pydantic import BaseModel, Field


T = TypeVar('T')


class ApiError(BaseModel):
    """API error response schema."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper that matches frontend expectations."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ApiError] = Field(None, description="Error information")


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str = Field(..., description="Response message")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema."""
    data: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    
    
class DetailedHealthCheck(HealthCheck):
    """Detailed health check with service statuses."""
    services: Dict[str, Dict[str, Any]] = Field(..., description="Service health status")