"""
Authentication service for user registration, login, and token management
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict

from supabase import Client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.services.supabase import get_supabase_client
from app.services.database import get_db_session
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RateLimiter:
    """Simple in-memory rate limiter for login attempts"""
    
    def __init__(self):
        self.attempts = defaultdict(list)
        self.max_attempts = 5
        self.window_minutes = 5
    
    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier (IP/email) is rate limited"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        # Clean old attempts
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier] 
            if attempt > cutoff
        ]
        
        # Check if over limit
        return len(self.attempts[identifier]) >= self.max_attempts
    
    def record_attempt(self, identifier: str):
        """Record a failed login attempt"""
        self.attempts[identifier].append(datetime.utcnow())


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.rate_limiter = RateLimiter()
    
    def _generate_username_from_email(self, email: str) -> str:
        """Generate a username from email address"""
        # Extract part before @ and clean it
        base = email.split('@')[0]
        # Remove non-alphanumeric characters and convert to lowercase
        clean_base = re.sub(r'[^a-zA-Z0-9]', '', base).lower()
        
        # Ensure minimum length
        if len(clean_base) < 3:
            clean_base = f"user{clean_base}"
            
        return clean_base[:20]  # Limit to 20 characters
    
    async def _sync_user_to_database(
        self, 
        supabase_user: Dict[str, Any], 
        username: Optional[str] = None
    ) -> User:
        """
        Sync Supabase user to local MySQL database
        
        Args:
            supabase_user: User data from Supabase
            username: Optional username, will be generated if not provided
            
        Returns:
            User object from local database
        """
        async with get_db_session() as db:
            try:
                # Check if user already exists
                stmt = select(User).where(User.supabase_id == supabase_user['id'])
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    return existing_user
                
                # Generate username if not provided
                if not username:
                    username = self._generate_username_from_email(supabase_user['email'])
                
                # Create new user in local database
                new_user = User(
                    supabase_id=supabase_user['id'],
                    email=supabase_user['email'],
                    username=username,
                    preferred_language="en",  # Default language
                    subscription_tier="free",  # Default tier
                    daily_message_count=0,
                    message_reset_at=datetime.utcnow() + timedelta(days=1)
                )
                
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                
                logger.info(f"Synced new user to database: {new_user.email}")
                return new_user
                
            except IntegrityError as e:
                await db.rollback()
                # Handle duplicate username
                if "username" in str(e):
                    # Try with a random suffix
                    import uuid
                    username = f"{username}_{uuid.uuid4().hex[:4]}"
                    new_user.username = username
                    db.add(new_user)
                    await db.commit()
                    await db.refresh(new_user)
                    return new_user
                else:
                    logger.error(f"Database sync error: {e}")
                    raise AuthenticationError(
                        "SYNC_ERROR",
                        "Failed to sync user to database",
                        {"error": str(e)}
                    )
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error during user sync: {e}")
                raise AuthenticationError(
                    "SYNC_ERROR", 
                    "Failed to sync user to database",
                    {"error": str(e)}
                )
    
    async def register_user(
        self, 
        email: str, 
        password: str, 
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user in Supabase and sync to local database
        
        Args:
            email: User's email address
            password: User's password
            username: Optional username (will be generated if not provided)
            
        Returns:
            Dict with user data and tokens
            
        Raises:
            AuthenticationError: For various registration failures
        """
        try:
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise AuthenticationError(
                    "INVALID_EMAIL",
                    "Please provide a valid email address"
                )
            
            # Validate password strength
            if len(password) < 8:
                raise AuthenticationError(
                    "WEAK_PASSWORD",
                    "Password must be at least 8 characters long"
                )
            
            # Register with Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user is None:
                raise AuthenticationError(
                    "REGISTRATION_FAILED",
                    "Failed to create user account"
                )
            
            # Sync to local database
            local_user = await self._sync_user_to_database(
                response.user.model_dump(), 
                username
            )
            
            # Prepare user data
            user_data = {
                "id": local_user.id,
                "supabase_id": local_user.supabase_id,
                "email": local_user.email,
                "username": local_user.username,
                "preferred_language": local_user.preferred_language,
                "subscription_tier": local_user.subscription_tier,
                "created_at": local_user.created_at.isoformat()
            }
            
            # Handle session data (might be None if email confirmation is required)
            session_data = None
            if response.session:
                session_data = {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                    "expires_in": response.session.expires_in,
                    "token_type": response.session.token_type
                }
            else:
                # Email confirmation required
                logger.info(f"User registered but email confirmation required: {email}")
            
            return {
                "user": user_data,
                "session": session_data,
                "email_confirmation_required": response.session is None
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            # Map Supabase errors to our error codes
            error_message = str(e)
            if "User already registered" in error_message:
                raise AuthenticationError(
                    "USER_EXISTS",
                    "An account with this email already exists"
                )
            elif "Password should be at least 6 characters" in error_message:
                raise AuthenticationError(
                    "WEAK_PASSWORD", 
                    "Password must be at least 6 characters long"
                )
            else:
                logger.error(f"Registration error: {e}")
                raise AuthenticationError(
                    "REGISTRATION_FAILED",
                    "Failed to create user account",
                    {"error": str(e)}
                )
    
    async def login_user(self, email: str, password: str, ip_address: str = "unknown") -> Dict[str, Any]:
        """
        Authenticate user and return tokens
        
        Args:
            email: User's email
            password: User's password  
            ip_address: Client IP for rate limiting
            
        Returns:
            Dict with user data and tokens
            
        Raises:
            AuthenticationError: For various login failures
        """
        try:
            # Check rate limiting
            if self.rate_limiter.is_rate_limited(ip_address):
                raise AuthenticationError(
                    "RATE_LIMITED",
                    "Too many login attempts. Please try again later."
                )
            
            # Attempt login with Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user or not response.session:
                self.rate_limiter.record_attempt(ip_address)
                raise AuthenticationError(
                    "INVALID_CREDENTIALS",
                    "Invalid email or password"
                )
            
            # Get user from local database
            async with get_db_session() as db:
                stmt = select(User).where(User.supabase_id == response.user.id)
                result = await db.execute(stmt)
                local_user = result.scalar_one_or_none()
                
                if not local_user:
                    # User exists in Supabase but not in local DB - sync them
                    local_user = await self._sync_user_to_database(
                        response.user.model_dump()
                    )
            
            return {
                "user": {
                    "id": local_user.id,
                    "supabase_id": local_user.supabase_id, 
                    "email": local_user.email,
                    "username": local_user.username,
                    "preferred_language": local_user.preferred_language,
                    "subscription_tier": local_user.subscription_tier,
                    "is_premium": local_user.is_premium(),
                    "daily_message_count": local_user.daily_message_count,
                    "can_send_message": local_user.can_send_message()
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                    "expires_in": response.session.expires_in,
                    "token_type": response.session.token_type
                }
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            self.rate_limiter.record_attempt(ip_address)
            logger.error(f"Login error: {e}")
            
            # Map common Supabase errors
            error_message = str(e)
            if "Invalid login credentials" in error_message:
                raise AuthenticationError(
                    "INVALID_CREDENTIALS",
                    "Invalid email or password"
                )
            else:
                raise AuthenticationError(
                    "LOGIN_FAILED",
                    "Login failed due to server error",
                    {"error": str(e)}
                )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dict with new tokens
            
        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if not response.session:
                raise AuthenticationError(
                    "TOKEN_INVALID",
                    "Invalid or expired refresh token"
                )
            
            return {
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                    "expires_in": response.session.expires_in,
                    "token_type": response.session.token_type
                }
            }
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise AuthenticationError(
                "TOKEN_REFRESH_FAILED",
                "Failed to refresh token",
                {"error": str(e)}
            )
    
    async def get_user_by_token(self, access_token: str) -> Optional[User]:
        """
        Get user by access token
        
        Args:
            access_token: Valid access token
            
        Returns:
            User object if token is valid, None otherwise
        """
        try:
            # Get user from Supabase using token
            user_response = self.supabase.auth.get_user(access_token)
            
            if not user_response.user:
                return None
            
            # Get user from local database
            async with get_db_session() as db:
                stmt = select(User).where(User.supabase_id == user_response.user.id)
                result = await db.execute(stmt)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Get user by token error: {e}")
            return None
    
    async def update_user_profile(
        self, 
        user_id: int, 
        username: Optional[str] = None,
        preferred_language: Optional[str] = None
    ) -> User:
        """
        Update user profile information
        
        Args:
            user_id: User's local database ID
            username: New username (optional)
            preferred_language: New preferred language (optional)
            
        Returns:
            Updated User object
            
        Raises:
            AuthenticationError: If user not found or update fails
        """
        try:
            async with get_db_session() as db:
                # Get user from database
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise AuthenticationError(
                        "USER_NOT_FOUND",
                        "User not found"
                    )
                
                # Update fields if provided
                if username is not None:
                    # Check if username is already taken
                    username_stmt = select(User).where(
                        User.username == username,
                        User.id != user_id
                    )
                    existing_user = await db.execute(username_stmt)
                    if existing_user.scalar_one_or_none():
                        raise AuthenticationError(
                            "USERNAME_TAKEN",
                            "Username is already taken"
                        )
                    user.username = username
                
                if preferred_language is not None:
                    user.preferred_language = preferred_language
                
                # Save changes
                await db.commit()
                await db.refresh(user)
                
                return user
                
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Update user profile error: {e}")
            raise AuthenticationError(
                "PROFILE_UPDATE_FAILED",
                "Failed to update user profile",
                {"error": str(e)}
            )
    
    async def change_user_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password
        
        Args:
            user_id: User's local database ID
            current_password: Current password for verification
            new_password: New password to set
            
        Raises:
            AuthenticationError: If verification fails or update fails
        """
        try:
            async with get_db_session() as db:
                # Get user from database
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise AuthenticationError(
                        "USER_NOT_FOUND",
                        "User not found"
                    )
                
                # Verify current password by attempting sign-in
                try:
                    response = self.supabase.auth.sign_in_with_password({
                        "email": user.email,
                        "password": current_password
                    })
                    
                    if not response.user or not response.session:
                        raise AuthenticationError(
                            "INVALID_CREDENTIALS",
                            "Current password is incorrect"
                        )
                    
                    # Update password in Supabase
                    self.supabase.auth.update_user({
                        "password": new_password
                    })
                    
                except Exception as supabase_error:
                    if "Invalid login credentials" in str(supabase_error):
                        raise AuthenticationError(
                            "INVALID_CREDENTIALS", 
                            "Current password is incorrect"
                        )
                    else:
                        raise AuthenticationError(
                            "PASSWORD_CHANGE_FAILED",
                            "Failed to change password",
                            {"error": str(supabase_error)}
                        )
                        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Change password error: {e}")
            raise AuthenticationError(
                "PASSWORD_CHANGE_FAILED",
                "Failed to change password",
                {"error": str(e)}
            )
    
    async def delete_user_account(
        self,
        user_id: int,
        password: str
    ) -> None:
        """
        Delete user account permanently
        
        Args:
            user_id: User's local database ID
            password: Current password for verification
            
        Raises:
            AuthenticationError: If verification fails or deletion fails
        """
        try:
            async with get_db_session() as db:
                # Get user from database
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise AuthenticationError(
                        "USER_NOT_FOUND",
                        "User not found"
                    )
                
                # Verify password by attempting sign-in
                try:
                    response = self.supabase.auth.sign_in_with_password({
                        "email": user.email,
                        "password": password
                    })
                    
                    if not response.user or not response.session:
                        raise AuthenticationError(
                            "INVALID_CREDENTIALS",
                            "Password is incorrect"
                        )
                    
                    # Delete user from Supabase
                    # Note: This requires admin privileges in Supabase
                    # For now, we'll mark the user as deleted in local DB
                    await db.delete(user)
                    await db.commit()
                    
                    # TODO: Implement Supabase user deletion when admin API is available
                    # self.supabase.auth.admin.delete_user(user.supabase_id)
                    
                except Exception as supabase_error:
                    if "Invalid login credentials" in str(supabase_error):
                        raise AuthenticationError(
                            "INVALID_CREDENTIALS",
                            "Password is incorrect"
                        )
                    else:
                        raise AuthenticationError(
                            "ACCOUNT_DELETION_FAILED",
                            "Failed to delete account",
                            {"error": str(supabase_error)}
                        )
                        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Delete account error: {e}")
            raise AuthenticationError(
                "ACCOUNT_DELETION_FAILED",
                "Failed to delete account",
                {"error": str(e)}
            )


# Global auth service instance
auth_service = AuthService()