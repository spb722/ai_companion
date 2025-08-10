"""
Conversation model for tracking chat sessions
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """Conversation model for chat sessions between users and characters"""
    
    __tablename__ = "conversations"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    character_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("characters.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Conversation metadata
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        index=True
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    character: Mapped["Character"] = relationship("Character", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", 
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_conversations_user_id', 'user_id'),
        Index('ix_conversations_character_id', 'character_id'),
        Index('ix_conversations_started_at', 'started_at'),
        Index('ix_conversations_last_message_at', 'last_message_at'),
        Index('ix_conversations_user_started', 'user_id', 'started_at'),
        Index('ix_conversations_user_character', 'user_id', 'character_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, character_id={self.character_id}, messages={self.message_count})>"
    
    def update_last_message_at(self) -> None:
        """Update the last_message_at timestamp"""
        self.last_message_at = func.now()
    
    def increment_message_count(self) -> None:
        """Increment the message count"""
        self.message_count += 1
        self.update_last_message_at()