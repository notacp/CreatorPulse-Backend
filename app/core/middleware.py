"""
Custom middleware for the FastAPI application.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=round(process_time, 4),
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware."""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not request.client:
            return await call_next(request)
        
        client_ip = request.client.host
        now = time.time()
        
        # Clean old entries
        self.clients = {
            ip: timestamps for ip, timestamps in self.clients.items()
            if any(timestamp > now - self.period for timestamp in timestamps)
        }
        
        # Check rate limit
        if client_ip in self.clients:
            # Filter recent requests
            recent_requests = [
                timestamp for timestamp in self.clients[client_ip]
                if timestamp > now - self.period
            ]
            
            if len(recent_requests) >= self.calls:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    requests=len(recent_requests),
                    limit=self.calls,
                )
                return Response(
                    content='{"error": "Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + self.period)),
                    }
                )
            
            self.clients[client_ip] = recent_requests + [now]
        else:
            self.clients[client_ip] = [now]
        
        # Add rate limit headers
        remaining = max(0, self.calls - len(self.clients[client_ip]))
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response