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
    """Register a new user with Supabase authentication."""
    try:
        # Check if user already exists in our database
        result = await db.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValidationException("Email already registered")
        
        # Register with Supabase Auth (required)
        logger.info(f"Registering user with Supabase: {request.email}")
        
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise ValidationException("Supabase registration failed")
        
        if auth_response.user.email_confirmed_at is None:
            logger.info(f"User needs email confirmation: {request.email}")
        
        # Create user in our database using Supabase user ID
        from datetime import time
        user = User(
            id=auth_response.user.id,
            email=request.email,
            password_hash=get_password_hash(request.password),  # Store for backup auth
            timezone=request.timezone or "UTC",
            delivery_time=time(8, 0, 0),  # Default delivery time
            active=True,
            email_verified=auth_response.user.email_confirmed_at is not None
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        expires_at = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        logger.info(f"User registered successfully with Supabase: {user.email}")
        
        message = "Registration successful. Please check your email for verification."
        if auth_response.user.email_confirmed_at:
            message = "Registration successful and email verified."
        
        return ApiResponse(
            success=True,
            data=AuthResponse(
                user=UserSchema.from_orm(user),
                token=access_token,
                expires_at=expires_at.isoformat()
            ),
            message=message
        )
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Supabase registration error: {e}")
        logger.error(f"Registration error type: {type(e)}")
        logger.error(f"Registration error details: {str(e)}")
        import traceback
        logger.error(f"Registration traceback: {traceback.format_exc()}")
        
        # Check for specific Supabase errors
        error_message = str(e)
        if "User already registered" in error_message:
            raise ValidationException("Email already registered")
        elif "Invalid email" in error_message:
            raise ValidationException("Invalid email address")
        elif "Weak password" in error_message:
            raise ValidationException("Password is too weak. Please use a stronger password.")
        else:
            raise ValidationException(f"Registration failed: {error_message}")


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    supabase: Client = Depends(get_supabase)
):
    """Authenticate user with Supabase and return JWT token."""
    try:
        # Authenticate with Supabase first (required)
        logger.info(f"Authenticating user with Supabase: {request.email}")
        
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise AuthenticationException("Invalid email or password")
        
        # Check if email is confirmed
        if not auth_response.user.email_confirmed_at:
            raise AuthenticationException("Please confirm your email address before logging in. Check your inbox for a verification email.")
        
        # Get user from our database
        result = await db.execute(select(User).where(User.id == auth_response.user.id))
        user = result.scalar_one_or_none()
        
        if user is None:
            # User exists in Supabase but not in our database - this shouldn't happen
            # but let's handle it gracefully
            logger.warning(f"User {request.email} exists in Supabase but not in database")
            raise AuthenticationException("User account not found. Please contact support.")
        
        if not user.active:
            raise AuthenticationException("Account is inactive")
        
        # Update email verification status if it changed
        if not user.email_verified and auth_response.user.email_confirmed_at:
            user.email_verified = True
            await db.commit()
            logger.info(f"Updated email verification status for user: {user.email}")
        
        # Create JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        expires_at = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        logger.info(f"User logged in successfully with Supabase: {user.email}")
        
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
        logger.error(f"Supabase login error: {e}")
        logger.error(f"Login error type: {type(e)}")
        import traceback
        logger.error(f"Login traceback: {traceback.format_exc()}")
        
        # Check for specific Supabase Auth errors
        error_message = str(e)
        if "Email not confirmed" in error_message:
            raise AuthenticationException("Please confirm your email address before logging in. Check your inbox for a verification email.")
        elif "Invalid login credentials" in error_message:
            raise AuthenticationException("Invalid email or password")
        elif "Email not confirmed" in error_message:
            raise AuthenticationException("Please confirm your email address before logging in.")
        else:
            raise AuthenticationException(f"Authentication failed: {error_message}")


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Logout user and invalidate Supabase session."""
    try:
        # Sign out from Supabase (required)
        supabase.auth.sign_out()
        logger.info(f"User signed out from Supabase: {current_user.email}")
        
        return ApiResponse(
            success=True,
            data={},
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Supabase logout error: {e}")
        # Even if Supabase logout fails, we still consider it a success
        # since the JWT token will expire anyway
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
    """Send password reset email via Supabase."""
    try:
        # Use Supabase password reset (required)
        supabase.auth.reset_password_email(request.email)
        logger.info(f"Supabase password reset sent for: {request.email}")
        
        return ApiResponse(
            success=True,
            data={},
            message="If the email exists, a password reset link will be sent"
        )
        
    except Exception as e:
        logger.error(f"Supabase password reset error: {e}")
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
    """Verify email with token from email link via Supabase."""
    try:
        # Supabase handles email verification automatically
        # This endpoint can be used for custom verification logic if needed
        logger.info(f"Email verification via Supabase for token: {token[:8]}...")
        
        # You can add additional verification logic here if needed
        # For now, we trust that Supabase handles the verification
        
        return ApiResponse(
            success=True,
            data={},
            message="Email verified successfully"
        )
        
    except Exception as e:
        logger.error(f"Supabase email verification error: {e}")
        raise ValidationException("Email verification failed")
