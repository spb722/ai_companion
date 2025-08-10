"""
Health check API endpoints
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.services.health import health_service
from app import __version__

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> JSONResponse:
    """
    Comprehensive health check endpoint
    
    Returns:
        JSON response with health status of all services
        - 200: All services healthy
        - 503: One or more services unhealthy
    """
    try:
        health_data = await health_service.perform_full_health_check()
        
        # Add application version info
        health_data["version"] = __version__
        health_data["application"] = "AI Companion API"
        
        # Return appropriate HTTP status code
        if health_data["status"] == "healthy":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=health_data
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_data
            )
            
    except Exception as e:
        # Return error response for unexpected failures
        error_data = {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": health_data.get("timestamp") if 'health_data' in locals() else None,
            "version": __version__,
            "application": "AI Companion API"
        }
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_data
        )

@router.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check() -> JSONResponse:
    """
    Readiness check - lighter weight check for container orchestration
    
    Returns:
        JSON response indicating if the service is ready to accept requests
    """
    try:
        # Quick check of critical services only
        redis_health = await health_service.check_redis_health()
        db_health = await health_service.check_database_health()
        
        is_ready = (redis_health["status"] == "healthy" and 
                   db_health["status"] == "healthy")
        
        response_data = {
            "status": "ready" if is_ready else "not_ready",
            "redis": redis_health["status"] == "healthy",
            "database": db_health["status"] == "healthy",
            "version": __version__
        }
        
        status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": str(e),
                "version": __version__
            }
        )

@router.get("/health/live", response_model=Dict[str, Any])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check - minimal check to verify the application is running
    
    Returns:
        Simple JSON response indicating the application is alive
    """
    return {
        "status": "alive",
        "version": __version__,
        "application": "AI Companion API"
    }

@router.get("/health/services/{service_name}", response_model=Dict[str, Any])
async def individual_service_health(service_name: str) -> JSONResponse:
    """
    Check health of individual service
    
    Args:
        service_name: Name of service to check (redis, database, environment)
    
    Returns:
        JSON response with health status of specified service
    """
    try:
        if service_name.lower() == "redis":
            health_data = await health_service.check_redis_health()
        elif service_name.lower() == "database":
            health_data = await health_service.check_database_health()
        elif service_name.lower() == "environment":
            health_data = health_service.check_environment_health()
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found. Available services: redis, database, environment"
            )
        
        status_code = (status.HTTP_200_OK if health_data["status"] == "healthy" 
                      else status.HTTP_503_SERVICE_UNAVAILABLE)
        
        return JSONResponse(
            status_code=status_code,
            content={
                "service": service_name,
                "health": health_data,
                "version": __version__
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": service_name,
                "status": "error",
                "message": str(e),
                "version": __version__
            }
        )