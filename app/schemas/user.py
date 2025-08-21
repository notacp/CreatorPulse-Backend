"""
User schemas that match frontend TypeScript interfaces.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User email address")
    timezone: str = Field(default="UTC", description="User timezone (IANA format)")
    delivery_time: str = Field(default="08:00:00", description="Email delivery time (HH:MM:SS)")
    active: bool = Field(default=True, description="Whether user account is active")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = Field(None, description="User email address")
    timezone: Optional[str] = Field(None, description="User timezone (IANA format)")
    delivery_time: Optional[str] = Field(None, description="Email delivery time (HH:MM:SS)")
    active: Optional[bool] = Field(None, description="Whether user account is active")


class User(UserBase):
    """User response schema."""
    id: str = Field(..., description="User ID (UUID)")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User settings schema."""
    timezone: str = Field(..., description="User timezone (IANA format)")
    delivery_time: str = Field(..., description="Email delivery time (HH:MM:SS)")
    email_notifications: bool = Field(default=True, description="Whether to receive email notifications")