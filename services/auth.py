"""
Authentication and rate limiting service.
"""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from models.database import ApiKeyUsage


class AuthService:
    """Authentication and rate limiting service."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.api_keys = set(settings.api_keys)
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        return api_key in self.api_keys
    
    async def check_rate_limit(self, api_key: str) -> tuple[bool, dict]:
        """
        Check rate limit for API key.
        
        Returns:
            tuple: (is_allowed, rate_limit_info)
        """
        key = f"rate_limit:{api_key}"
        window_start = int(time.time()) // settings.rate_limit_window
        
        try:
            # Get current count
            current_count = await self.redis.get(f"{key}:{window_start}")
            current_count = int(current_count) if current_count else 0
            
            # Calculate reset time
            reset_time = (window_start + 1) * settings.rate_limit_window
            
            rate_limit_info = {
                "requests_remaining": max(0, settings.rate_limit_requests - current_count),
                "requests_limit": settings.rate_limit_requests,
                "window_reset_time": datetime.fromtimestamp(reset_time),
                "window_duration": settings.rate_limit_window
            }
            
            if current_count >= settings.rate_limit_requests:
                return False, rate_limit_info
            
            # Increment counter
            pipe = self.redis.pipeline()
            pipe.incr(f"{key}:{window_start}")
            pipe.expire(f"{key}:{window_start}", settings.rate_limit_window)
            await pipe.execute()
            
            rate_limit_info["requests_remaining"] -= 1
            return True, rate_limit_info
            
        except Exception as e:
            # If Redis is down, allow the request but log the error
            import logging
            logging.warning(f"Rate limiting failed: {e}")
            return True, {
                "requests_remaining": settings.rate_limit_requests,
                "requests_limit": settings.rate_limit_requests,
                "window_reset_time": datetime.utcnow() + timedelta(seconds=settings.rate_limit_window),
                "window_duration": settings.rate_limit_window
            }
    
    async def log_api_usage(
        self,
        db: AsyncSession,
        api_key: str,
        request: Request,
        response_status: int,
        response_time: float,
        file_size_uploaded: int = 0,
        processing_time: Optional[float] = None
    ):
        """Log API usage for analytics and monitoring."""
        try:
            # Hash API key for privacy
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            
            usage = ApiKeyUsage(
                api_key=api_key_hash,
                endpoint=str(request.url.path),
                method=request.method,
                response_status=response_status,
                response_time=response_time,
                user_agent=request.headers.get("user-agent"),
                ip_address=self._get_client_ip(request),
                file_size_uploaded=file_size_uploaded,
                processing_time=processing_time
            )
            
            db.add(usage)
            await db.commit()
            
        except Exception as e:
            # Don't fail the request if logging fails
            import logging
            logging.warning(f"Failed to log API usage: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


# Authentication dependency
async def get_api_key(request: Request) -> str:
    """
    Extract and validate API key from request.
    
    Supports Bearer token in Authorization header.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = auth_header[7:]  # Remove "Bearer " prefix
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Validate API key
    auth_service = AuthService(None)  # Redis client will be injected
    if not auth_service.validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return api_key


# Rate limiting dependency
async def check_rate_limit(request: Request, api_key: str = None) -> dict:
    """
    Check rate limit for the current request.
    
    Returns rate limit information and raises exception if exceeded.
    """
    if not api_key:
        api_key = await get_api_key(request)
    
    # Get Redis client from app state
    redis_client = request.app.state.redis
    auth_service = AuthService(redis_client)
    
    is_allowed, rate_limit_info = await auth_service.check_rate_limit(api_key)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit_info["requests_limit"]),
                "X-RateLimit-Remaining": str(rate_limit_info["requests_remaining"]),
                "X-RateLimit-Reset": str(int(rate_limit_info["window_reset_time"].timestamp())),
                "Retry-After": str(rate_limit_info["window_duration"])
            }
        )
    
    return rate_limit_info
