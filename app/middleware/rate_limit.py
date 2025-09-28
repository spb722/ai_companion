"""
Rate limiting middleware for FastAPI.

This middleware implements IP-based rate limiting using Redis.
"""

import time
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.rate_limit_service import rate_limit_service

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for IP-based rate limiting."""
    
    def __init__(self, app, requests_per_minute: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler
        
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for health check endpoint and CORS preflight requests
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)
        
        # Get client IP
        client_ip = rate_limit_service.get_client_ip(request)
        
        # Check rate limit
        allowed, remaining = await rate_limit_service.check_rate_limit(
            key=client_ip,
            limit=self.requests_per_minute,
            window=self.window_seconds
        )
        
        # Get rate limit info for headers
        rate_info = await rate_limit_service.get_rate_limit_info(
            key=client_ip,
            limit=self.requests_per_minute,
            window=self.window_seconds
        )
        
        # Prepare rate limit headers
        rate_headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(rate_info["reset"]),
            "X-RateLimit-Window": str(self.window_seconds)
        }
        
        # Block if rate limit exceeded
        if not allowed:
            retry_after = rate_info["reset"] - int(time.time())
            
            error_response = {
                "detail": {
                    "type": "error",
                    "error": "Rate limit exceeded. Please try again later.",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "limit": self.requests_per_minute,
                    "window_seconds": self.window_seconds,
                    "retry_after": max(1, retry_after)
                }
            }
            
            # Add retry-after header
            rate_headers["Retry-After"] = str(max(1, retry_after))

            # Add CORS headers for rate limit responses
            origin = request.headers.get("origin")
            if origin in [
                "https://ai-companion-inskade.web.app",
                "https://ai-companion-inskade.firebaseapp.com",
                "http://localhost:3000",
                "http://localhost:5173"
            ]:
                rate_headers.update({
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Expose-Headers": "*",
                    "Vary": "Origin"
                })

            return JSONResponse(
                status_code=429,
                content=error_response,
                headers=rate_headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for header_name, header_value in rate_headers.items():
            response.headers[header_name] = header_value
        
        return response