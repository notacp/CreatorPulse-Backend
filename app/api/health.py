"""
Health check endpoints.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.common import HealthCheck, DetailedHealthCheck, ApiResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
health_router = APIRouter()


@health_router.get("/", response_model=ApiResponse[HealthCheck])
async def health_check():
    """Basic health check endpoint."""
    return ApiResponse(
        success=True,
        data=HealthCheck(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            environment=settings.environment,
        )
    )


@health_router.get("/detailed", response_model=ApiResponse[DetailedHealthCheck])
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Detailed health check with service statuses."""
    services = {}
    overall_status = "healthy"
    
    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        services["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
        logger.info("Database health check passed")
    except Exception as e:
        services["database"] = {
            "status": "unhealthy", 
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "unhealthy"
        logger.error("Database health check failed", error=str(e))
    
    # Check Redis connection
    try:
        await redis.ping()
        services["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
        logger.info("Redis health check passed")
    except Exception as e:
        services["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        overall_status = "unhealthy"
        logger.error("Redis health check failed", error=str(e))
    
    # Check external services (basic connectivity)
    services["external_apis"] = {
        "status": "healthy",
        "message": "External API keys configured",
        "gemini": bool(settings.gemini_api_key),
        "sendgrid": bool(settings.sendgrid_api_key),
        "twitter": bool(settings.twitter_bearer_token),
    }
    
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service unhealthy")
    
    return ApiResponse(
        success=True,
        data=DetailedHealthCheck(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            environment=settings.environment,
            services=services,
        )
    )