"""
User model for managing user accounts and subscriptions
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model for storing user account information"""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Supabase integration
    supabase_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # User information
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    
    # Localization
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    
    # Subscription and usage tracking
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)  # free, pro
    daily_message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message_reset_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )
    
    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_users_supabase_id', 'supabase_id'),
        Index('ix_users_email', 'email'),
        Index('ix_users_subscription_tier', 'subscription_tier'),
        Index('ix_users_message_reset_at', 'message_reset_at'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', tier='{self.subscription_tier}')>"
    
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.subscription_tier == "pro"
    
    def can_send_message(self, daily_limit_free: int = 50, daily_limit_pro: int = 500) -> bool:
        """Check if user can send another message based on daily limits"""
        # Reset daily count if needed
        if datetime.utcnow() >= self.message_reset_at:
            return True
            
        # Check against tier limits
        limit = daily_limit_pro if self.is_premium() else daily_limit_free
        return self.daily_message_count < limit
    
    def increment_message_count(self) -> None:
        """Increment daily message count"""
        # Reset count if it's a new day
        if datetime.utcnow() >= self.message_reset_at:
            self.daily_message_count = 1
            # Set next reset to tomorrow at same time
            self.message_reset_at = datetime.utcnow() + timedelta(days=1)
        else:
            self.daily_message_count += 1