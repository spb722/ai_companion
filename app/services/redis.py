"""
Redis service for caching and session management
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def get_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self.client:
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self.client
    
    async def set_user_character(
        self, 
        user_id: int, 
        character_id: int, 
        ttl_hours: int = 24
    ) -> bool:
        """
        Store user's selected character in Redis
        
        Args:
            user_id: User ID
            character_id: Selected character ID
            ttl_hours: Time to live in hours (default: 24)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = await self.get_client()
            key = f"user:{user_id}:character"
            
            # Store character selection with TTL
            await client.setex(
                key, 
                timedelta(hours=ttl_hours), 
                str(character_id)
            )
            
            logger.info(f"Stored character selection for user {user_id}: character {character_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store character selection for user {user_id}: {e}")
            return False
    
    async def get_user_character(self, user_id: int) -> Optional[int]:
        """
        Get user's selected character from Redis
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[int]: Character ID if found, None otherwise
        """
        try:
            client = await self.get_client()
            key = f"user:{user_id}:character"
            
            character_id_str = await client.get(key)
            if character_id_str:
                character_id = int(character_id_str)
                logger.debug(f"Retrieved character selection for user {user_id}: character {character_id}")
                return character_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve character selection for user {user_id}: {e}")
            return None
    
    async def clear_user_character(self, user_id: int) -> bool:
        """
        Clear user's character selection from Redis
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = await self.get_client()
            key = f"user:{user_id}:character"
            
            result = await client.delete(key)
            logger.info(f"Cleared character selection for user {user_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to clear character selection for user {user_id}: {e}")
            return False
    
    async def set_cache(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set a cached value
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = await self.get_client()
            
            # JSON serialize the value
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            
            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized_value)
            else:
                await client.set(key, serialized_value)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Get a cached value
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value if found, None otherwise
        """
        try:
            client = await self.get_client()
            value = await client.get(key)
            
            if value is None:
                return None
            
            # Try to JSON deserialize, fall back to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """
        Delete a cached value
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = await self.get_client()
            result = await client.delete(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None


# Global Redis service instance
redis_service = RedisService()