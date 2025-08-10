"""
API routes module - Main router configuration
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Import route modules
from .health import router as health_router
# from .auth import router as auth_router  # Will be added in future tasks
# from .chat import router as chat_router  # Will be added in future tasks
# from .characters import router as characters_router  # Will be added in future tasks

# Register route modules
api_router.include_router(health_router, tags=["health"])
# api_router.include_router(auth_router, prefix="/auth", tags=["auth"])  # Future
# api_router.include_router(chat_router, prefix="/chat", tags=["chat"])  # Future  
# api_router.include_router(characters_router, prefix="/characters", tags=["characters"])  # Future

__all__ = ["api_router"]