"""
Custom exceptions and error handlers.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from .logging import get_logger

logger = get_logger(__name__)


class CreatorPulseException(Exception):
    """Base exception for CreatorPulse application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(CreatorPulseException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationException(CreatorPulseException):
    """Authentication error exception."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="authentication_error",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationException(CreatorPulseException):
    """Authorization error exception."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="authorization_error",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundException(CreatorPulseException):
    """Resource not found exception."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            error_code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class RateLimitException(CreatorPulseException):
    """Rate limit exceeded exception."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="rate_limit_error",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


async def creatorpulse_exception_handler(request: Request, exc: CreatorPulseException) -> JSONResponse:
    """Handle CreatorPulse custom exceptions."""
    logger.error(
        "CreatorPulse exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors."""
    logger.error(
        "Validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "error": "validation_error",
                "message": "Invalid input data",
                "details": exc.errors(),
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    
    # Map status codes to error codes
    error_code_map = {
        401: "authentication_error",
        403: "authorization_error", 
        404: "not_found",
        429: "rate_limit_error",
        500: "server_error",
    }
    
    error_code = error_code_map.get(exc.status_code, "http_error")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "error": error_code,
                "message": exc.detail,
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "error": "server_error",
                "message": "An unexpected error occurred",
            }
        }
    )