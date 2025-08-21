"""
FastAPI application main module.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.database import init_db, close_db
from app.core.redis import redis_manager
from app.core.middleware import LoggingMiddleware, RateLimitMiddleware
from app.core.exceptions import (
    CreatorPulseException,
    creatorpulse_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.api.v1.api import api_router
from app.api.health import health_router


# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CreatorPulse API", environment=settings.environment)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Connect to Redis
        await redis_manager.connect()
        logger.info("Redis connected")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down CreatorPulse API")
        
        # Close database connections
        await close_db()
        logger.info("Database connections closed")
        
        # Disconnect from Redis
        await redis_manager.disconnect()
        logger.info("Redis disconnected")


# Create FastAPI application
app = FastAPI(
    title="CreatorPulse API",
    description="AI-powered LinkedIn content generation API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["creatorpulse.com", "*.creatorpulse.com"]
    )

# Add custom middleware
app.add_middleware(LoggingMiddleware)

# Add rate limiting middleware if enabled
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# Add exception handlers
app.add_exception_handler(CreatorPulseException, creatorpulse_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(api_router, prefix="/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CreatorPulse API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation not available in production",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )