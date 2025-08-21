"""
Authentication schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from .user import User


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    """Registration request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    timezone: Optional[str] = Field(default="UTC", description="User timezone (IANA format)")


class AuthResponse(BaseModel):
    """Authentication response schema."""
    user: User = Field(..., description="User information")
    token: str = Field(..., description="JWT access token")
    expires_at: str = Field(..., description="Token expiration timestamp")


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="User email address")