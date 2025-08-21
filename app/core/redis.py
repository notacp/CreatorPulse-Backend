"""
Redis configuration and connection management.
"""
import aioredis
from typing import Optional
from .config import settings


class RedisManager:
    """Redis connection manager."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis = aioredis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis:
            return None
        return await self.redis.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis."""
        if not self.redis:
            return False
        return await self.redis.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis:
            return False
        return bool(await self.redis.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis:
            return False
        return bool(await self.redis.exists(key))


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> aioredis.Redis:
    """
    Dependency to get Redis connection.
    
    Returns:
        aioredis.Redis: Redis connection
    """
    if not redis_manager.redis:
        await redis_manager.connect()
    return redis_manager.redis