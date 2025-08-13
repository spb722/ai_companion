"""
Supabase client service for authentication and user management
"""

import logging
from typing import Optional, Dict, Any

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for managing Supabase client and operations"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client with configuration"""
        try:
            # Validate configuration
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise ValueError("Missing required Supabase configuration")
            
            # Create client options for better error handling
            options = ClientOptions(
                postgrest_client_timeout=10,
                storage_client_timeout=10,
                schema="public",
            )
            
            # Initialize client
            self.client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key,
                options=options
            )
            
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
            raise
    
    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Supabase connectivity and service health
        
        Returns:
            Dict with health status information
        """
        try:
            if not self.client:
                return {
                    "status": "unhealthy",
                    "error": "Client not initialized",
                    "message": "Supabase client failed to initialize"
                }
            
            # Test connection by checking auth status
            # This is a lightweight operation that validates connectivity
            try:
                # Try to get the current session (will return None if no user, but validates connection)
                session = self.client.auth.get_session()
                connection_ok = True
            except Exception as conn_error:
                logger.warning(f"Supabase connection test failed: {conn_error}")
                connection_ok = False
            
            if connection_ok:
                return {
                    "status": "healthy",
                    "connection": True,
                    "message": "Supabase service is operational",
                    "url": settings.supabase_url[:30] + "..." if len(settings.supabase_url) > 30 else settings.supabase_url
                }
            else:
                return {
                    "status": "unhealthy", 
                    "connection": False,
                    "error": "connection_failed",
                    "message": "Unable to connect to Supabase service"
                }
                
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": False,
                "error": str(e),
                "message": "Supabase health check encountered an error"
            }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate Supabase configuration on startup
        
        Returns:
            Dict with validation results
        """
        issues = []
        
        # Check required environment variables
        if not settings.supabase_url:
            issues.append("SUPABASE_URL not configured")
        elif not settings.supabase_url.startswith('https://'):
            issues.append("SUPABASE_URL should start with https://")
            
        if not settings.supabase_anon_key:
            issues.append("SUPABASE_ANON_KEY not configured")
        elif len(settings.supabase_anon_key) < 100:  # JWT tokens are typically much longer
            issues.append("SUPABASE_ANON_KEY appears invalid (too short)")
            
        # Check if service key is available (optional but recommended)
        if not settings.supabase_service_key:
            logger.warning("SUPABASE_SERVICE_KEY not configured - some admin operations may not be available")
        
        if issues:
            return {
                "valid": False,
                "issues": issues,
                "message": f"Configuration validation failed: {', '.join(issues)}"
            }
        else:
            return {
                "valid": True,
                "issues": [],
                "message": "Supabase configuration is valid"
            }
    
    def get_jwt_secret(self) -> str:
        """
        Get JWT secret for token validation
        For Supabase, this is typically derived from the project settings
        """
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        # For Supabase, we'll use the built-in JWT validation
        # The secret is managed by Supabase internally
        return settings.supabase_anon_key


# Global Supabase service instance
supabase_service = SupabaseService()

# Convenience function to get client
def get_supabase_client() -> Client:
    """Get the global Supabase client instance"""
    return supabase_service.get_client()