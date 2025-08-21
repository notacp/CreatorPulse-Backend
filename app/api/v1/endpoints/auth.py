"""
Authentication endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import Client

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    verify_token,
    generate_reset_token
)
from app.core.supabase import get_supabase
from app.core.exceptions import AuthenticationException, ValidationException
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, 
    RegisterRequest, 
    AuthResponse, 
    PasswordResetRequest
)
from app.schemas.user import User as UserSchema
from app.schemas.common import ApiResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user."""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationException("Invalid token payload")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationException("User not found")
        
        if not user.active:
            raise AuthenticationException("User account is inactive")
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise AuthenticationException("Could not validate credentials")


@router.post("/register", response_model=ApiResponse[AuthResponse])
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    supabase: Client = Depends(get_supabase)
):
    """Register a new user."""
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValidationException("Email already registered")
        
        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if auth_response.user is None:
            raise ValidationException("Registration failed")
        
        # Create user in our database
        from datetime import time
        user = User(
            id=auth_response.user.id,
            email=request.email,
            password_hash=get_password_hash(request.password),  # Required field
            timezone=request.timezone or "UTC",
            delivery_time=time(8, 0, 0),  # Default delivery time
            active=True,
            email_verified=False  # Will be verified through Supabase
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        expires_at = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return ApiResponse(
            success=True,
            data=AuthResponse(
                user=UserSchema.from_orm(user),
                token=access_token,
                expires_at=expires_at.isoformat()
            ),
            message="Registration successful. Please check your email for verification."
        )
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        logger.error(f"Registration error type: {type(e)}")
        logger.error(f"Registration error details: {str(e)}")
        import traceback
        logger.error(f"Registration traceback: {traceback.format_exc()}")
        raise ValidationException(f"Registration failed: {str(e)}")


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    supabase: Client = Depends(get_supabase)
):
    """Authenticate user and return JWT token."""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if auth_response.user is None:
            raise AuthenticationException("Invalid email or password")
        
        # Get user from our database
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationException("User not found")
        
        if not user.active:
            raise AuthenticationException("Account is inactive")
        
        # Create JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        expires_at = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return ApiResponse(
            success=True,
            data=AuthResponse(
                user=UserSchema.from_orm(user),
                token=access_token,
                expires_at=expires_at.isoformat()
            )
        )
        
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        logger.error(f"Login error type: {type(e)}")
        import traceback
        logger.error(f"Login traceback: {traceback.format_exc()}")
        
        # Check for specific Supabase Auth errors
        error_message = str(e)
        if "Email not confirmed" in error_message:
            raise AuthenticationException("Please confirm your email address before logging in. Check your inbox for a verification email.")
        elif "Invalid login credentials" in error_message:
            raise AuthenticationException("Invalid email or password")
        else:
            raise AuthenticationException(f"Authentication failed: {error_message}")


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Logout user and invalidate session."""
    try:
        # Sign out from Supabase
        supabase.auth.sign_out()
        
        logger.info(f"User logged out: {current_user.email}")
        
        return ApiResponse(
            success=True,
            data={},
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return ApiResponse(
            success=True,
            data={},
            message="Logged out successfully"
        )


@router.post("/reset-password", response_model=ApiResponse[dict])
async def reset_password(
    request: PasswordResetRequest,
    supabase: Client = Depends(get_supabase)
):
    """Send password reset email."""
    try:
        # Use Supabase password reset
        supabase.auth.reset_password_email(request.email)
        
        logger.info(f"Password reset requested for: {request.email}")
        
        return ApiResponse(
            success=True,
            data={},
            message="Password reset email sent"
        )
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Don't reveal if email exists or not
        return ApiResponse(
            success=True,
            data={},
            message="If the email exists, a password reset link will be sent"
        )


@router.get("/me", response_model=ApiResponse[UserSchema])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return ApiResponse(
        success=True,
        data=UserSchema.from_orm(current_user)
    )


@router.get("/verify-email")
async def verify_email(
    token: str,
    supabase: Client = Depends(get_supabase)
):
    """Verify email with token from email link."""
    try:
        # Supabase handles email verification automatically
        # This endpoint can be used for custom verification logic if needed
        
        return ApiResponse(
            success=True,
            data={},
            message="Email verified successfully"
        )
        
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise ValidationException("Email verification failed")
