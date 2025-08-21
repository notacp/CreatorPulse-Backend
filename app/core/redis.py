"""
Redis configuration and connection management.
Temporarily simplified for Python 3.13 compatibility.
"""
from typing import Optional
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Simplified Redis connection manager for testing."""
    
    def __init__(self):
        self.connected = False
        logger.info("Redis manager initialized (mock mode for Python 3.13)")
    
    async def connect(self) -> None:
        """Mock connect to Redis."""
        logger.info("Redis connection established (mock)")
        self.connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnect from Redis."""
        logger.info("Redis connection closed (mock)")
        self.connected = False
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get value from Redis."""
        logger.debug(f"Redis GET {key} (mock)")
        return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """Mock set value in Redis."""
        logger.debug(f"Redis SET {key} (mock)")
        return True
    
    async def delete(self, key: str) -> bool:
        """Mock delete key from Redis."""
        logger.debug(f"Redis DELETE {key} (mock)")
        return True
    
    async def exists(self, key: str) -> bool:
        """Mock check if key exists in Redis."""
        logger.debug(f"Redis EXISTS {key} (mock)")
        return False


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis():
    """
    Mock dependency to get Redis connection.
    
    Returns:
        RedisManager: Mock Redis connection
    """
    if not redis_manager.connected:
        await redis_manager.connect()
    return redis_manager