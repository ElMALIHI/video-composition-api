"""
Redis configuration and cache management.
"""

import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from core.settings import settings


class RedisManager:
    """Redis connection and cache manager."""

    def __init__(self):
        self.redis: Optional[Redis] = None

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=10,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            if not self.redis:
                await self.initialize()
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis:
            await self.initialize()
        return await self.redis.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False,
    ) -> bool:
        """Set value in Redis."""
        if not self.redis:
            await self.initialize()
        return await self.redis.set(key, value, ex=ex, nx=nx)

    async def delete(self, key: str) -> int:
        """Delete key from Redis."""
        if not self.redis:
            await self.initialize()
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis:
            await self.initialize()
        return bool(await self.redis.exists(key))

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value in Redis."""
        if not self.redis:
            await self.initialize()
        return await self.redis.incr(key, amount)

    async def expire(self, key: str, time: int) -> bool:
        """Set expiration for key."""
        if not self.redis:
            await self.initialize()
        return await self.redis.expire(key, time)

    async def ttl(self, key: str) -> int:
        """Get TTL for key."""
        if not self.redis:
            await self.initialize()
        return await self.redis.ttl(key)

    # JSON helpers
    async def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        nx: bool = False,
    ) -> bool:
        """Set JSON value in Redis."""
        json_value = json.dumps(value, default=str)
        return await self.set(key, json_value, ex=ex, nx=nx)

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from Redis."""
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    # Rate limiting helpers
    async def rate_limit_check(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Check rate limit for a key.
        
        Returns:
            tuple: (is_allowed, current_count, remaining_time)
        """
        if not self.redis:
            await self.initialize()

        current = await self.redis.get(key)
        
        if current is None:
            # First request
            await self.redis.setex(key, window, 1)
            return True, 1, window
        
        current_count = int(current)
        
        if current_count >= limit:
            # Rate limit exceeded
            ttl = await self.redis.ttl(key)
            return False, current_count, ttl
        
        # Increment counter
        new_count = await self.redis.incr(key)
        ttl = await self.redis.ttl(key)
        
        return True, new_count, ttl

    # Job queue helpers
    async def enqueue_job(self, queue_name: str, job_data: dict) -> bool:
        """Add job to queue."""
        if not self.redis:
            await self.initialize()
        return await self.redis.lpush(queue_name, json.dumps(job_data, default=str))

    async def dequeue_job(self, queue_name: str, timeout: int = 0) -> Optional[dict]:
        """Get job from queue."""
        if not self.redis:
            await self.initialize()
        
        result = await self.redis.brpop(queue_name, timeout=timeout)
        if result:
            _, job_data = result
            try:
                return json.loads(job_data)
            except json.JSONDecodeError:
                return None
        return None

    async def get_queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        if not self.redis:
            await self.initialize()
        return await self.redis.llen(queue_name)


# Global Redis manager instance
redis_manager = RedisManager()


# Startup function for FastAPI
async def initialize_redis():
    """Initialize Redis on application startup."""
    await redis_manager.initialize()


# Shutdown function for FastAPI
async def close_redis():
    """Close Redis connections on application shutdown."""
    await redis_manager.close()
