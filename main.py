"""
AI Companion App - Main FastAPI Application Entry Point
"""

import logging
import time
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app import __version__
from app.config import settings
from app.routes import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and timing"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"- Time: {process_time:.3f}s "
            f"- Path: {request.url.path}"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

# Create FastAPI application instance
app = FastAPI(
    title="AI Companion API",
    description="Production-ready AI companion app backend for Indian audiences with multi-language support",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check operations"},
        {"name": "auth", "description": "Authentication operations"},
        {"name": "chat", "description": "Chat operations"},
        {"name": "characters", "description": "Character management"},
    ]
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",
        "http://localhost:8080",  # Alternative frontend port
        "https://localhost:3000", # HTTPS development
    ] if settings.app_env == "development" else [
        "https://your-domain.com",  # Add your production domain here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with structured error response"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with detailed field information"""
    logger.warning(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error" if settings.app_env == "production" else str(exc),
            "status_code": 500,
            "path": str(request.url.path)
        }
    )

@app.get("/", tags=["health"])
async def root() -> Dict[str, Any]:
    """Root endpoint returning basic API information"""
    return {
        "message": "AI Companion API",
        "version": __version__,
        "status": "running",
        "environment": settings.app_env,
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)