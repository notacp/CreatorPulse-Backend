"""
Pydantic schemas package.
"""
from .auth import LoginRequest, RegisterRequest, AuthResponse, PasswordResetRequest
from .user import User, UserCreate, UserUpdate, UserSettings
from .source import Source, SourceCreate, SourceUpdate, SourceStatus
from .source_content import SourceContent, SourceContentCreate
from .style import StylePost, StyleTrainingRequest, StyleTrainingStatus
from .draft import Draft, GenerateDraftsRequest, GenerateDraftsResponse
from .feedback import FeedbackRequest, FeedbackResponse
from .common import ApiResponse, PaginatedResponse, MessageResponse

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest", 
    "AuthResponse",
    "PasswordResetRequest",
    
    # User
    "User",
    "UserCreate",
    "UserUpdate", 
    "UserSettings",
    
    # Source
    "Source",
    "SourceCreate",
    "SourceUpdate",
    "SourceStatus",
    
    # Source Content
    "SourceContent", 
    "SourceContentCreate",
    
    # Style
    "StylePost",
    "StyleTrainingRequest",
    "StyleTrainingStatus",
    
    # Draft
    "Draft",
    "GenerateDraftsRequest",
    "GenerateDraftsResponse",
    
    # Feedback
    "FeedbackRequest",
    "FeedbackResponse",
    
    # Common
    "ApiResponse",
    "PaginatedResponse",
    "MessageResponse",
]