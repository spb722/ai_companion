"""
Authentication API endpoints
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, validator

from app.services.auth import auth_service, AuthenticationError
from app.middleware.auth import get_current_user, get_client_ip
from app.models.user import User
from app.utils.auth_responses import response_factory, ErrorCode

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])


# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request model"""
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    username: Optional[str] = Field(None, min_length=3, max_length=20, description="Optional username")
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if not EMAIL_REGEX.match(v):
            raise ValueError('Please provide a valid email address')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            if not v.isalnum():
                raise ValueError('Username must contain only letters and numbers')
        return v


class LoginRequest(BaseModel):
    """User login request model"""
    email: str = Field(..., description="Valid email address")
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if not EMAIL_REGEX.match(v):
            raise ValueError('Please provide a valid email address')
        return v.lower()


class RefreshTokenRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str


class UserResponse(BaseModel):
    """User data response model"""
    id: int
    supabase_id: str
    email: str
    username: Optional[str]
    preferred_language: str
    subscription_tier: str
    is_premium: Optional[bool] = None
    daily_message_count: Optional[int] = None
    can_send_message: Optional[bool] = None
    created_at: str


class SessionResponse(BaseModel):
    """Session data response model"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    expires_at: int


class AuthResponse(BaseModel):
    """Complete authentication response model"""
    user: UserResponse
    session: SessionResponse


# Note: Rate limiting is handled by the auth service internally


@router.post("/register", response_model=dict)
async def register(request: Request, register_data: RegisterRequest):
    """
    Register a new user account
    
    Creates a new user in Supabase and syncs to local database.
    Returns user data and authentication tokens.
    """
    try:
        # Register user
        result = await auth_service.register_user(
            email=register_data.email,
            password=register_data.password,
            username=register_data.username
        )
        
        logger.info(f"User registered successfully: {register_data.email}")
        
        # Return success response
        return response_factory.create_success_response(
            data={
                "user": result["user"],
                "session": result["session"]
            },
            message="Account created successfully"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Registration failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode(e.code),
            e.message,
            e.details
        )
    except Exception as e:
        logger.error(f"Unexpected registration error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.REGISTRATION_FAILED,
            "Registration failed due to server error"
        )


@router.post("/login", response_model=dict)
async def login(request: Request, login_data: LoginRequest):
    """
    Authenticate user and return tokens
    
    Validates credentials and returns user data with access/refresh tokens.
    Rate limiting is handled internally by the auth service.
    """
    try:
        client_ip = get_client_ip(request)
        
        # Authenticate user
        result = await auth_service.login_user(
            email=login_data.email,
            password=login_data.password,
            ip_address=client_ip
        )
        
        logger.info(f"User logged in successfully: {login_data.email}")
        
        # Return success response
        return response_factory.create_success_response(
            data={
                "user": result["user"],
                "session": result["session"]
            },
            message="Login successful"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Login failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode.AUTH_ERROR,
            e.message,
            e.details,
            401 if e.code in ["INVALID_CREDENTIALS", "RATE_LIMITED"] else 400
        )
    except Exception as e:
        logger.error(f"Unexpected login error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.AUTH_ERROR,
            "Login failed due to server error"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    Provides new access and refresh tokens when current token is expired.
    """
    try:
        # Refresh tokens
        result = await auth_service.refresh_token(refresh_data.refresh_token)
        
        logger.info("Token refreshed successfully")
        
        # Return success response
        return response_factory.create_success_response(
            data={
                "session": result["session"]
            },
            message="Token refreshed successfully"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Token refresh failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode(e.code),
            e.message,
            e.details,
            401
        )
    except Exception as e:
        logger.error(f"Unexpected token refresh error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.TOKEN_REFRESH_FAILED,
            "Token refresh failed due to server error"
        )


@router.get("/me", response_model=dict)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile
    
    Protected endpoint that returns the current user's profile information.
    Requires valid JWT token in Authorization header.
    """
    try:
        user_data = {
            "id": current_user.id,
            "supabase_id": current_user.supabase_id,
            "email": current_user.email,
            "username": current_user.username,
            "preferred_language": current_user.preferred_language,
            "subscription_tier": current_user.subscription_tier,
            "is_premium": current_user.is_premium(),
            "daily_message_count": current_user.daily_message_count,
            "can_send_message": current_user.can_send_message(),
            "created_at": current_user.created_at.isoformat()
        }
        
        return response_factory.create_success_response(
            data={"user": user_data},
            message="User profile retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise response_factory.create_error_response(
            ErrorCode.SERVER_ERROR,
            "Failed to retrieve user profile"
        )


# Profile Management Endpoints

class UpdateProfileRequest(BaseModel):
    """User profile update request model"""
    username: Optional[str] = Field(None, min_length=3, max_length=20, description="New username")
    preferred_language: Optional[str] = Field(None, description="Preferred language (e.g., 'en', 'es', 'fr')")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            if not v.isalnum():
                raise ValueError('Username must contain only letters and numbers')
        return v
    
    @validator('preferred_language')
    def validate_language(cls, v):
        """Validate language code format"""
        if v is not None:
            # Simple validation for common language codes
            valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
            if v.lower() not in valid_languages:
                raise ValueError(f'Language must be one of: {", ".join(valid_languages)}')
        return v.lower() if v else v


class ChangePasswordRequest(BaseModel):
    """Password change request model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        return v


@router.patch("/profile", response_model=dict)
async def update_user_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile information
    
    Allows authenticated users to update their profile information
    such as username and preferred language.
    """
    try:
        # Update user profile in auth service
        updated_user = await auth_service.update_user_profile(
            user_id=current_user.id,
            username=profile_data.username,
            preferred_language=profile_data.preferred_language
        )
        
        user_data = {
            "id": updated_user.id,
            "supabase_id": updated_user.supabase_id,
            "email": updated_user.email,
            "username": updated_user.username,
            "preferred_language": updated_user.preferred_language,
            "subscription_tier": updated_user.subscription_tier,
            "is_premium": updated_user.is_premium(),
            "daily_message_count": updated_user.daily_message_count,
            "can_send_message": updated_user.can_send_message(),
            "created_at": updated_user.created_at.isoformat()
        }
        
        logger.info(f"User profile updated: {current_user.id}")
        
        return response_factory.create_success_response(
            data={"user": user_data},
            message="Profile updated successfully"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Profile update failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode(e.code),
            e.message,
            e.details
        )
    except Exception as e:
        logger.error(f"Unexpected profile update error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.SERVER_ERROR,
            "Failed to update profile"
        )


@router.post("/change-password", response_model=dict)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Change user password
    
    Allows authenticated users to change their password.
    Requires current password for verification.
    """
    try:
        # Change password in auth service
        await auth_service.change_user_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        logger.info(f"Password changed for user: {current_user.id}")
        
        return response_factory.create_success_response(
            message="Password changed successfully"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Password change failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode(e.code),
            e.message,
            e.details,
            401 if e.code == "INVALID_CREDENTIALS" else 400
        )
    except Exception as e:
        logger.error(f"Unexpected password change error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.SERVER_ERROR,
            "Failed to change password"
        )


class DeleteAccountRequest(BaseModel):
    """Account deletion request model"""
    password: str = Field(..., description="Current password for confirmation")


@router.delete("/account", response_model=dict)
async def delete_account(
    delete_data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Delete user account
    
    Permanently deletes the user account from both Supabase and local database.
    This action cannot be undone.
    """
    try:
        # Delete account in auth service
        await auth_service.delete_user_account(
            user_id=current_user.id,
            password=delete_data.password
        )
        
        logger.info(f"Account deleted for user: {current_user.id}")
        
        return response_factory.create_success_response(
            message="Account deleted successfully"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Account deletion failed: {e.code} - {e.message}")
        raise response_factory.create_error_response(
            ErrorCode(e.code),
            e.message,
            e.details,
            401 if e.code == "INVALID_CREDENTIALS" else 400
        )
    except Exception as e:
        logger.error(f"Unexpected account deletion error: {e}")
        raise response_factory.create_error_response(
            ErrorCode.SERVER_ERROR,
            "Failed to delete account"
        )