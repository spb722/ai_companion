"""
Rate limiting service using Redis for API protection.

This service implements simple fixed-window rate limiting using Redis counters.
"""

import time
from typing import Tuple, Optional
from fastapi import Request
import redis.asyncio as redis
from app.services.redis import redis_service

class RateLimitService:
    """Simple Redis-based rate limiting service."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client, initialize if needed."""
        if self.redis is None:
            self.redis = await redis_service.get_client()
        return self.redis
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int = 10,
        window: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded for given key.
        
        Args:
            key: Unique identifier (e.g., IP address)
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 60)
        
        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        try:
            redis_client = await self.get_redis_client()
            
            # Create time bucket for fixed window
            current_time = int(time.time())
            bucket = current_time // window
            redis_key = f"rate:{key}:{bucket}"
            
            # Increment counter and get current value
            current_count = await redis_client.incr(redis_key)
            
            # Set TTL on first request in this bucket
            if current_count == 1:
                await redis_client.expire(redis_key, window)
            
            # Check if limit exceeded
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            
            return allowed, remaining
            
        except Exception as e:
            # Fail open - allow request if Redis unavailable
            print(f"Rate limit check failed: {e}")
            return True, limit
    
    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request headers.
        
        Checks X-Forwarded-For, X-Real-IP, and client host in order.
        
        Args:
            request: FastAPI request object
        
        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (multiple IPs, use first)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP if multiple (client IP)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header (single IP)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to client host
        client_host = request.client.host if request.client else "unknown"
        return client_host
    
    async def get_rate_limit_info(
        self,
        key: str,
        limit: int = 10,
        window: int = 60
    ) -> dict:
        """
        Get current rate limit status for a key.
        
        Args:
            key: Unique identifier
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            Dictionary with rate limit information
        """
        try:
            redis_client = await self.get_redis_client()
            
            current_time = int(time.time())
            bucket = current_time // window
            redis_key = f"rate:{key}:{bucket}"
            
            # Get current count
            current_count = await redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0
            
            # Calculate remaining and reset time
            remaining = max(0, limit - current_count)
            reset_time = (bucket + 1) * window
            
            return {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "window": window,
                "current": current_count
            }
            
        except Exception as e:
            print(f"Rate limit info check failed: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "reset": int(time.time()) + window,
                "window": window,
                "current": 0
            }

# Global instance
rate_limit_service = RateLimitService()