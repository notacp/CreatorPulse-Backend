"""
Monitoring, metrics, and observability for production.
"""

import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
import structlog

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'http_active_connections',
    'Active HTTP connections'
)

# System metrics
system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
system_memory_usage = Gauge('system_memory_usage_percent', 'System memory usage percentage')
system_disk_usage = Gauge('system_disk_usage_percent', 'System disk usage percentage')

# Application metrics
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

email_delivery_total = Counter(
    'email_delivery_total',
    'Total email deliveries',
    ['status']
)

draft_generation_total = Counter(
    'draft_generation_total',
    'Total draft generations',
    ['status']
)

user_activity_total = Counter(
    'user_activity_total',
    'Total user activities',
    ['activity_type']
)

# Database metrics
database_connections = Gauge('database_connections', 'Active database connections')
database_query_duration = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# Redis metrics
redis_connections = Gauge('redis_connections', 'Active Redis connections')
redis_operations = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)


class MetricsCollector:
    """Collects and manages application metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.system_stats_task = None
    
    async def start_collection(self):
        """Start metrics collection."""
        logger.info("Starting metrics collection")
        self.system_stats_task = asyncio.create_task(self._collect_system_stats())
    
    async def stop_collection(self):
        """Stop metrics collection."""
        if self.system_stats_task:
            self.system_stats_task.cancel()
            try:
                await self.system_stats_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collection stopped")
    
    async def _collect_system_stats(self):
        """Collect system statistics periodically."""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                system_cpu_usage.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                system_memory_usage.set(memory.percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                system_disk_usage.set(disk_percent)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error collecting system stats: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        request_count.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_celery_task(self, task_name: str, status: str):
        """Record Celery task metrics."""
        celery_tasks_total.labels(
            task_name=task_name,
            status=status
        ).inc()
    
    def record_email_delivery(self, status: str):
        """Record email delivery metrics."""
        email_delivery_total.labels(status=status).inc()
    
    def record_draft_generation(self, status: str):
        """Record draft generation metrics."""
        draft_generation_total.labels(status=status).inc()
    
    def record_user_activity(self, activity_type: str):
        """Record user activity metrics."""
        user_activity_total.labels(activity_type=activity_type).inc()
    
    def record_database_query(self, operation: str, duration: float):
        """Record database query metrics."""
        database_query_duration.labels(operation=operation).observe(duration)
    
    def record_redis_operation(self, operation: str, status: str):
        """Record Redis operation metrics."""
        redis_operations.labels(
            operation=operation,
            status=status
        ).inc()
    
    def get_app_info(self) -> Dict[str, Any]:
        """Get application information."""
        uptime = time.time() - self.start_time
        return {
            "app_name": "CreatorPulse Backend",
            "version": "1.0.0",
            "environment": settings.environment,
            "uptime_seconds": round(uptime, 2),
            "started_at": datetime.fromtimestamp(self.start_time).isoformat()
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware:
    """Middleware to collect HTTP request metrics."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        request = Request(scope, receive)
        
        # Track active connections
        active_connections.inc()
        
        status_code = 500  # Default
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.time() - start_time
            endpoint = self._get_endpoint_name(request.url.path)
            
            metrics_collector.record_request(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )
            
            active_connections.dec()
    
    def _get_endpoint_name(self, path: str) -> str:
        """Get normalized endpoint name for metrics."""
        # Remove IDs and tokens from paths for better grouping
        path_parts = path.split('/')
        normalized_parts = []
        
        for part in path_parts:
            if not part:
                continue
            # Replace UUIDs and tokens with placeholders
            if len(part) > 20 and ('-' in part or part.isalnum()):
                normalized_parts.append('{id}')
            else:
                normalized_parts.append(part)
        
        return '/' + '/'.join(normalized_parts) if normalized_parts else '/'


@asynccontextmanager
async def database_query_timer(operation: str):
    """Context manager to time database operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics_collector.record_database_query(operation, duration)


def setup_monitoring(app: FastAPI):
    """Set up monitoring and metrics for the application."""
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics", response_class=PlainTextResponse)
    async def get_metrics():
        """Prometheus metrics endpoint."""
        return generate_latest()
    
    logger.info("Monitoring middleware configured")


async def health_check_services() -> Dict[str, Any]:
    """Perform health checks on all services."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    overall_healthy = True
    
    # Check database
    try:
        from app.core.database import get_db
        async for session in get_db():
            await session.execute("SELECT 1")
            health_status["services"]["database"] = {"status": "healthy"}
            break
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check Redis
    try:
        from app.core.redis import get_redis
        redis_manager = await get_redis()
        if redis_manager and await redis_manager.ping():
            health_status["services"]["redis"] = {"status": "healthy"}
        else:
            raise Exception("Redis ping failed")
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check Celery (if available)
    try:
        from app.core.celery_app import celery_app
        stats = celery_app.control.inspect().stats()
        if stats:
            health_status["services"]["celery"] = {"status": "healthy"}
        else:
            raise Exception("No Celery workers available")
    except Exception as e:
        health_status["services"]["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Overall health
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    return health_status


def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        return {
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            },
            "process": {
                "pid": psutil.Process().pid,
                "memory_percent": psutil.Process().memory_percent(),
                "cpu_percent": psutil.Process().cpu_percent(interval=1),
                "num_threads": psutil.Process().num_threads(),
                "create_time": psutil.Process().create_time()
            }
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {"error": str(e)}
