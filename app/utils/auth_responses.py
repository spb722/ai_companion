"""
Standardized authentication response system
"""

import uuid
from enum import Enum
from typing import Dict, Any, Optional, Union
from datetime import datetime

from pydantic import BaseModel
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """Standardized error codes for authentication operations"""
    
    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_MISSING = "TOKEN_MISSING"
    TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"
    
    # Registration errors
    USER_EXISTS = "USER_EXISTS"
    WEAK_PASSWORD = "WEAK_PASSWORD"
    INVALID_EMAIL = "INVALID_EMAIL"
    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    
    # Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN" 
    PREMIUM_REQUIRED = "PREMIUM_REQUIRED"
    
    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    
    # Profile management errors
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    PROFILE_UPDATE_FAILED = "PROFILE_UPDATE_FAILED"
    PASSWORD_CHANGE_FAILED = "PASSWORD_CHANGE_FAILED"
    ACCOUNT_DELETION_FAILED = "ACCOUNT_DELETION_FAILED"
    
    # General errors
    AUTH_ERROR = "AUTH_ERROR"
    SYNC_ERROR = "SYNC_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SERVER_ERROR = "SERVER_ERROR"


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standardized error response model"""
    success: bool = False
    error: ErrorDetail
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure consistent format"""
        data = super().model_dump(**kwargs)
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        if not data.get("request_id"):
            data["request_id"] = str(uuid.uuid4())
        return data


class SuccessResponse(BaseModel):
    """Standardized success response model"""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure consistent format"""
        data = super().model_dump(**kwargs)
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        if not data.get("request_id"):
            data["request_id"] = str(uuid.uuid4())
        return data


class AuthResponseFactory:
    """Factory for creating standardized authentication responses"""
    
    @staticmethod
    def create_error_response(
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create standardized error response
        
        Args:
            code: Error code from ErrorCode enum
            message: Human-readable error message
            details: Additional error details
            status_code: HTTP status code
            request_id: Optional request ID for tracking
            
        Returns:
            HTTPException with standardized error format
        """
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
                details=details
            ),
            request_id=request_id
        )
        
        return HTTPException(
            status_code=status_code,
            detail=error_response.model_dump(),
            headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        )
    
    @staticmethod
    def create_success_response(
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized success response
        
        Args:
            data: Response data
            message: Success message
            request_id: Optional request ID for tracking
            
        Returns:
            Dict with standardized success format
        """
        success_response = SuccessResponse(
            data=data,
            message=message,
            request_id=request_id
        )
        
        return success_response.model_dump()
    
    # Convenience methods for common authentication errors
    
    @staticmethod
    def invalid_credentials(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Invalid email or password"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.INVALID_CREDENTIALS,
            "Invalid email or password",
            details,
            status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def token_expired(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Token has expired"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.TOKEN_EXPIRED,
            "Token has expired",
            details,
            status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def token_invalid(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Token is invalid or malformed"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.TOKEN_INVALID,
            "Invalid or malformed token",
            details,
            status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def token_missing() -> HTTPException:
        """Authorization token is missing"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.TOKEN_MISSING,
            "Authorization token is required",
            None,
            status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def user_exists(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """User already exists with this email"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.USER_EXISTS,
            "An account with this email already exists",
            details,
            status.HTTP_409_CONFLICT
        )
    
    @staticmethod
    def weak_password(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Password does not meet requirements"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.WEAK_PASSWORD,
            "Password does not meet security requirements",
            details,
            status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def invalid_email(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Invalid email format"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.INVALID_EMAIL,
            "Please provide a valid email address",
            details,
            status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def rate_limited(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Too many requests"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.RATE_LIMITED,
            "Too many requests. Please try again later.",
            details,
            status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    @staticmethod
    def unauthorized(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """User is not authorized"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.UNAUTHORIZED,
            "You are not authorized to access this resource",
            details,
            status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Access is forbidden"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.FORBIDDEN,
            "Access to this resource is forbidden",
            details,
            status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def premium_required(details: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Premium subscription required"""
        return AuthResponseFactory.create_error_response(
            ErrorCode.PREMIUM_REQUIRED,
            "Premium subscription required for this feature",
            details,
            status.HTTP_403_FORBIDDEN
        )


def map_supabase_error(error_message: str) -> ErrorCode:
    """
    Map Supabase error messages to our error codes
    
    Args:
        error_message: Error message from Supabase
        
    Returns:
        Appropriate ErrorCode
    """
    error_lower = error_message.lower()
    
    if "user already registered" in error_lower:
        return ErrorCode.USER_EXISTS
    elif "invalid login credentials" in error_lower:
        return ErrorCode.INVALID_CREDENTIALS
    elif "password should be at least" in error_lower:
        return ErrorCode.WEAK_PASSWORD
    elif "invalid email" in error_lower:
        return ErrorCode.INVALID_EMAIL
    elif "token" in error_lower and ("expired" in error_lower or "invalid" in error_lower):
        return ErrorCode.TOKEN_INVALID
    else:
        return ErrorCode.AUTH_ERROR


# Global response factory instance
response_factory = AuthResponseFactory()