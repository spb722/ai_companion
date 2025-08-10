"""
Health check service for validating core application dependencies
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

import redis.asyncio as redis
import aiomysql
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

class HealthCheckService:
    """Service for checking health of application dependencies"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.db_engine = None
    
    async def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self.redis_client
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and basic operations"""
        try:
            client = await self.get_redis_client()
            
            # Test ping
            ping_result = await client.ping()
            if not ping_result:
                raise Exception("Redis ping failed")
            
            # Test set/get operations
            test_key = f"health_check_{uuid.uuid4().hex[:8]}"
            test_value = "health_test_value"
            
            await client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = await client.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Redis set/get test failed")
            
            # Clean up test key
            await client.delete(test_key)
            
            return {
                "status": "healthy",
                "ping": True,
                "set_get_test": True,
                "message": "Redis is operational"
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "ping": False,
                "set_get_test": False,
                "message": f"Redis error: {str(e)}"
            }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check MySQL database connectivity"""
        try:
            # Create async engine for testing
            engine = create_async_engine(
                settings.database_url,
                pool_timeout=5,
                pool_pre_ping=True
            )
            
            # Test basic connection and query
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                
                if not row or row.health_check != 1:
                    raise Exception("Database query test failed")
            
            await engine.dispose()
            
            return {
                "status": "healthy", 
                "connection": True,
                "query_test": True,
                "message": "MySQL database is operational"
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "connection": False,
                "query_test": False, 
                "message": f"Database error: {str(e)}"
            }
    
    def check_environment_health(self) -> Dict[str, Any]:
        """Check critical environment variables"""
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "OPENAI_API_KEY",
            "SECRET_KEY"
        ]
        
        missing_vars = []
        present_vars = []
        
        for var_name in required_vars:
            try:
                # Check if the variable exists in settings
                var_value = getattr(settings, var_name.lower(), None)
                if var_value and str(var_value).strip():
                    present_vars.append(var_name)
                else:
                    missing_vars.append(var_name)
            except Exception:
                missing_vars.append(var_name)
        
        is_healthy = len(missing_vars) == 0
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "required_vars_present": present_vars,
            "missing_vars": missing_vars,
            "total_required": len(required_vars),
            "total_present": len(present_vars),
            "message": "All environment variables present" if is_healthy else f"Missing {len(missing_vars)} required variables"
        }
    
    async def perform_full_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all services"""
        timestamp = datetime.utcnow().isoformat()
        
        # Run all health checks concurrently
        redis_task = asyncio.create_task(self.check_redis_health())
        db_task = asyncio.create_task(self.check_database_health())
        env_check = self.check_environment_health()  # Synchronous
        
        # Wait for async tasks
        redis_health, db_health = await asyncio.gather(redis_task, db_task)
        
        # Determine overall health status
        all_services = [redis_health, db_health, env_check]
        overall_healthy = all(service["status"] == "healthy" for service in all_services)
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": timestamp,
            "services": {
                "redis": redis_health,
                "database": db_health,
                "environment": env_check
            },
            "overall": {
                "healthy": overall_healthy,
                "services_checked": len(all_services),
                "healthy_services": sum(1 for s in all_services if s["status"] == "healthy")
            }
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        
        if self.db_engine:
            await self.db_engine.dispose()
            self.db_engine = None


# Global health check service instance
health_service = HealthCheckService()