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

# Import monitoring functions if available
try:
    from app.core.monitoring import health_check_services, get_system_metrics, metrics_collector
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring features not available")


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


@health_router.get("/system")
async def system_health_check():
    """System health check with resource usage metrics."""
    if not MONITORING_AVAILABLE:
        raise HTTPException(status_code=501, detail="Monitoring not available")
    
    try:
        system_metrics = get_system_metrics()
        app_info = metrics_collector.get_app_info()
        
        return {
            "status": "healthy",
            "system": system_metrics,
            "application": app_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": str(e)}
        )


@health_router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    if MONITORING_AVAILABLE:
        health_info = await health_check_services()
        
        # Check critical services only
        critical_services = ["database", "redis"]
        ready = True
        
        for service in critical_services:
            if service in health_info["services"]:
                if health_info["services"][service]["status"] != "healthy":
                    ready = False
                    break
        
        if not ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "message": "Critical services are not available"
                }
            )
    
    return {
        "status": "ready",
        "message": "Application is ready to serve requests"
    }


@health_router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "message": "Application process is alive"
    }