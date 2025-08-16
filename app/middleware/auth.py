"""
Authentication middleware and dependencies for FastAPI
"""

import logging
from functools import wraps
from typing import Optional, Tuple, TYPE_CHECKING

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import auth_service, AuthenticationError
from app.models.user import User
from app.models.character import Character

logger = logging.getLogger(__name__)

# FastAPI security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """
    Dependency to get current authenticated user
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials from header
        
    Returns:
        User object if authenticated, None otherwise
        
    Raises:
        HTTPException: For authentication failures
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "MISSING_TOKEN",
                    "message": "Authorization token is required"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extract token from credentials
        access_token = credentials.credentials
        
        # Get user using the token
        user = await auth_service.get_user_by_token(access_token)
        
        if not user:
            # Try to refresh token if possible
            # For now, we'll just return unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": "TOKEN_INVALID",
                        "message": "Invalid or expired token"
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_ERROR",
                    "message": "Authentication failed"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user
    Additional checks can be added here (e.g., account suspension, email verification)
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        Active user object
        
    Raises:
        HTTPException: If user is inactive
    """
    # For now, all users are considered active
    # Future: Add checks for suspended accounts, email verification, etc.
    return current_user


async def get_premium_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to require premium user
    
    Args:
        current_user: User from get_current_active_user dependency
        
    Returns:
        Premium user object
        
    Raises:
        HTTPException: If user is not premium
    """
    if not current_user.is_premium():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "PREMIUM_REQUIRED",
                    "message": "Premium subscription required for this feature"
                }
            }
        )
    
    return current_user


def get_user_with_character_dep():
    """Factory function for the dependency"""
    
    async def _get_user_with_character(
        current_user: User = Depends(get_current_user)
    ) -> Tuple[User, Optional[Character]]:
        """
        Dependency to get current user with their selected character
        
        Args:
            current_user: User from get_current_user dependency
            
        Returns:
            Tuple of (User, Optional[Character])
        """
        try:
            from app.services.character import character_service
            
            # Get user's selected character
            character = await character_service.get_user_selected_character(current_user.id)
            
            logger.debug(f"User {current_user.id} session includes character: {character.name if character else 'None'}")
            
            return current_user, character
            
        except Exception as e:
            logger.error(f"Error getting user character for user {current_user.id}: {e}")
            # Return user without character if there's an error
            return current_user, None
    
    return _get_user_with_character

# Create the dependency
get_user_with_character = get_user_with_character_dep()


def require_character_selection_dep():
    """Factory function for the dependency"""
    
    async def _require_character_selection(
        current_user: User = Depends(get_current_user)
    ) -> Tuple[User, Character]:
        """
        Dependency that requires user to have a character selected
        
        Args:
            current_user: User from get_current_user dependency
            
        Returns:
            Tuple of (User, Character)
            
        Raises:
            HTTPException: If no character is selected
        """
        try:
            from app.services.character import character_service
            
            # Ensure user has a character (assign default if needed)
            user_is_premium = current_user.subscription_tier == "pro"
            character = await character_service.ensure_user_has_character(
                user_id=current_user.id,
                user_is_premium=user_is_premium
            )
            
            if not character:
                logger.warning(f"Unable to assign character to user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "NO_CHARACTER_AVAILABLE",
                            "message": "No character available. Please contact support."
                        }
                    }
                )
            
            logger.debug(f"User {current_user.id} has character {character.id} selected for chat")
            
            return current_user, character
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error ensuring character for user {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "CHARACTER_ERROR",
                        "message": "Failed to get character information"
                    }
                }
            )
    
    return _require_character_selection

# Create the dependency
require_character_selection = require_character_selection_dep()


def require_auth(f):
    """
    Decorator to require authentication for route functions
    
    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(user: User = Depends(get_current_user)):
            return {"message": "Hello authenticated user"}
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        return await f(*args, **kwargs)
    
    return decorated_function


def require_premium(f):
    """
    Decorator to require premium subscription for route functions
    
    Usage:
        @router.get("/premium")
        @require_premium  
        async def premium_endpoint(user: User = Depends(get_premium_user)):
            return {"message": "Hello premium user"}
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        return await f(*args, **kwargs)
    
    return decorated_function


class AuthMiddleware:
    """
    Middleware class for handling authentication across the application
    """
    
    def __init__(self):
        pass
    
    async def authenticate_request(self, request: Request) -> Optional[User]:
        """
        Authenticate a request and return user if valid
        
        Args:
            request: FastAPI request object
            
        Returns:
            User object if authenticated, None otherwise
        """
        try:
            # Extract authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return None
            
            # Parse Bearer token
            if not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.replace("Bearer ", "")
            
            # Get user by token
            user = await auth_service.get_user_by_token(token)
            return user
            
        except Exception as e:
            logger.warning(f"Authentication middleware error: {e}")
            return None
    
    def create_auth_response(self, code: str, message: str, status_code: int = 401):
        """
        Create standardized authentication error response
        
        Args:
            code: Error code
            message: Error message
            status_code: HTTP status code
            
        Returns:
            HTTPException with standardized format
        """
        return HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": code,
                    "message": message
                }
            },
            headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        )


# Global middleware instance
auth_middleware = AuthMiddleware()


# Utility function to extract IP address
def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address string
    """
    # Check for forwarded headers first (for proxy/load balancer setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP if multiple are present
        return forwarded_for.split(",")[0].strip()
    
    # Check other common headers
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to client host
    if request.client:
        return request.client.host
    
    return "unknown"