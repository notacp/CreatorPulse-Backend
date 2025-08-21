"""
Rate limiting and security middleware for production.
"""

import time
from typing import Callable, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis.asyncio as redis
from limits.storage import RedisStorage
from limits.strategies import MovingWindowRateLimiter

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Rate limiter instance - initialize with basic limiter
limiter = Limiter(key_func=get_remote_address)
redis_client = None


async def init_rate_limiter():
    """Initialize rate limiter with Redis backend."""
    global limiter, redis_client
    
    try:
        if settings.rate_limit_enabled:
            # Initialize Redis client for rate limiting
            redis_client = redis.from_url(
                settings.rate_limit_storage_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test Redis connection
            await redis_client.ping()
            
            # Initialize limiter with Redis storage
            storage = RedisStorage(settings.rate_limit_storage_url)
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=settings.rate_limit_storage_url,
                strategy="moving-window"
            )
            
            logger.info("Rate limiter initialized with Redis backend")
        else:
            # Create a dummy limiter for testing even when disabled
            limiter = Limiter(key_func=get_remote_address)
            logger.info("Rate limiting disabled - using dummy limiter")
            
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {e}")
        # Create a dummy limiter if Redis is not available
        limiter = Limiter(key_func=get_remote_address)
        logger.info("Rate limiter fallback to in-memory")


async def close_rate_limiter():
    """Close rate limiter connections."""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Rate limiter Redis connection closed")


def get_rate_limiter():
    """Get the rate limiter instance."""
    return limiter


def setup_rate_limiting(app: FastAPI):
    """Set up rate limiting middleware for the application."""
    if not settings.rate_limit_enabled or limiter is None:
        logger.info("Rate limiting is disabled or not initialized")
        return
    
    # Add SlowAPI middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting middleware configured")


async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit error handler."""
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after
        },
        headers={"Retry-After": str(exc.retry_after)}
    )
    
    # Log rate limit violations
    client_ip = get_remote_address(request)
    logger.warning(
        f"Rate limit exceeded for IP {client_ip}: {exc.detail}",
        extra={
            "client_ip": client_ip,
            "path": request.url.path,
            "method": request.method,
            "retry_after": exc.retry_after
        }
    )
    
    return response


# Rate limiting decorators for different endpoint types
def rate_limit_auth(requests: str = "10/minute"):
    """Rate limiting for authentication endpoints."""
    return limiter.limit(requests)


def rate_limit_api(requests: str = "100/minute"):
    """Rate limiting for general API endpoints."""
    return limiter.limit(requests)


def rate_limit_heavy(requests: str = "10/minute"):
    """Rate limiting for heavy operations (AI generation, etc.)."""
    return limiter.limit(requests)


def rate_limit_feedback(requests: str = "60/hour"):
    """Rate limiting for feedback endpoints (no auth required)."""
    return limiter.limit(requests)


# Security middleware
class SecurityHeadersMiddleware:
    """Add security headers to all responses."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add security headers
                security_headers = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"x-xss-protection": b"1; mode=block",
                    b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"geolocation=(), microphone=(), camera=()",
                    b"content-security-policy": b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
                }
                
                headers.update(security_headers)
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """Log all requests with timing and metadata."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        request = Request(scope, receive)
        client_ip = get_remote_address(request)
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "client_ip": client_ip,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        status_code = 500  # Default in case of error
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            logger.error(
                "Request failed with exception",
                extra={
                    "client_ip": client_ip,
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                },
                exc_info=True
            )
            raise
        finally:
            # Log request completion
            process_time = time.time() - start_time
            logger.info(
                "Request completed",
                extra={
                    "client_ip": client_ip,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": status_code,
                    "process_time": round(process_time, 4),
                }
            )


def setup_security_middleware(app: FastAPI):
    """Set up security middleware for the application."""
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("Security middleware configured")
