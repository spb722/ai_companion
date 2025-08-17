"""
Message quota service for tracking daily usage limits.

This service manages daily message quotas using Redis with automatic midnight reset.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import redis.asyncio as redis
from app.services.redis import redis_service

# Quota limits by tier
QUOTA_LIMITS = {
    'free': 20,
    'pro': 500
}

class QuotaService:
    """Redis-based daily message quota tracking service."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client, initialize if needed."""
        if self.redis is None:
            self.redis = await redis_service.get_client()
        return self.redis
    
    def get_date_key(self, user_id: int) -> str:
        """
        Generate Redis key for today's usage.
        
        Args:
            user_id: User ID
        
        Returns:
            Redis key in format 'quota:{user_id}:{YYYY-MM-DD}'
        """
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        return f"quota:{user_id}:{today}"
    
    def get_midnight_utc_timestamp(self) -> int:
        """
        Get Unix timestamp for next midnight UTC.
        
        Returns:
            Unix timestamp for next midnight UTC
        """
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return int(next_midnight.timestamp())
    
    async def increment_daily_messages(self, user_id: int) -> int:
        """
        Increment daily message count for user.
        
        Args:
            user_id: User ID
        
        Returns:
            New message count for today
        """
        try:
            redis_client = await self.get_redis_client()
            key = self.get_date_key(user_id)
            
            # Increment counter
            count = await redis_client.incr(key)
            
            # Set expiration to midnight UTC on first increment
            if count == 1:
                expire_at = self.get_midnight_utc_timestamp()
                await redis_client.expireat(key, expire_at)
            
            return count
            
        except Exception as e:
            print(f"Failed to increment daily messages: {e}")
            return 1  # Assume first message if Redis fails
    
    async def get_daily_usage(self, user_id: int) -> int:
        """
        Get current daily message count for user.
        
        Args:
            user_id: User ID
        
        Returns:
            Current message count for today
        """
        try:
            redis_client = await self.get_redis_client()
            key = self.get_date_key(user_id)
            
            count = await redis_client.get(key)
            return int(count) if count else 0
            
        except Exception as e:
            print(f"Failed to get daily usage: {e}")
            return 0
    
    async def check_quota(self, user_id: int, tier: str) -> Tuple[bool, int]:
        """
        Check if user has remaining quota.
        
        Args:
            user_id: User ID
            tier: User subscription tier ('free' or 'pro')
        
        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        try:
            current_usage = await self.get_daily_usage(user_id)
            limit = QUOTA_LIMITS.get(tier, QUOTA_LIMITS['free'])
            
            allowed = current_usage < limit
            remaining = max(0, limit - current_usage)
            
            return allowed, remaining
            
        except Exception as e:
            print(f"Failed to check quota: {e}")
            # Fail open - allow message if Redis unavailable
            return True, QUOTA_LIMITS.get(tier, QUOTA_LIMITS['free'])
    
    async def get_quota_info(self, user_id: int, tier: str) -> dict:
        """
        Get comprehensive quota information for user.
        
        Args:
            user_id: User ID
            tier: User subscription tier
        
        Returns:
            Dictionary with quota information
        """
        try:
            current_usage = await self.get_daily_usage(user_id)
            limit = QUOTA_LIMITS.get(tier, QUOTA_LIMITS['free'])
            remaining = max(0, limit - current_usage)
            
            # Calculate reset time (next midnight UTC)
            reset_timestamp = self.get_midnight_utc_timestamp()
            
            return {
                "tier": tier,
                "limit": limit,
                "used": current_usage,
                "remaining": remaining,
                "reset_at": reset_timestamp,
                "reset_in_seconds": max(0, reset_timestamp - int(time.time()))
            }
            
        except Exception as e:
            print(f"Failed to get quota info: {e}")
            limit = QUOTA_LIMITS.get(tier, QUOTA_LIMITS['free'])
            return {
                "tier": tier,
                "limit": limit,
                "used": 0,
                "remaining": limit,
                "reset_at": self.get_midnight_utc_timestamp(),
                "reset_in_seconds": 86400  # 24 hours
            }
    
    async def reset_daily_quota(self, user_id: int) -> bool:
        """
        Manually reset daily quota for user (useful for tier upgrades).
        
        Args:
            user_id: User ID
        
        Returns:
            True if reset successful
        """
        try:
            redis_client = await self.get_redis_client()
            key = self.get_date_key(user_id)
            
            # Delete the key to reset count
            await redis_client.delete(key)
            return True
            
        except Exception as e:
            print(f"Failed to reset daily quota: {e}")
            return False
    
    def get_tier_limits(self) -> dict:
        """
        Get all tier limits.
        
        Returns:
            Dictionary of tier limits
        """
        return QUOTA_LIMITS.copy()

# Global instance
quota_service = QuotaService()