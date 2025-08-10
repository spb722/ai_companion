"""
Character model for AI companions
"""

from typing import Optional, List
from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Character(Base, TimestampMixin):
    """Character model for AI companion personalities"""
    
    __tablename__ = "characters"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Character information
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    base_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Character classification
    personality_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Premium features
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", 
        back_populates="character"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_characters_name', 'name'),
        Index('ix_characters_personality_type', 'personality_type'),
        Index('ix_characters_is_premium', 'is_premium'),
        Index('ix_characters_premium_personality', 'is_premium', 'personality_type'),
    )
    
    def __repr__(self) -> str:
        return f"<Character(id={self.id}, name='{self.name}', type='{self.personality_type}')>"
    
    def can_be_used_by_user(self, user_is_premium: bool) -> bool:
        """Check if character can be used by user based on subscription"""
        if self.is_premium and not user_is_premium:
            return False
        return True