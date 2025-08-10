"""
Message model for storing chat messages
"""

from sqlalchemy import Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Message model for individual chat messages"""
    
    __tablename__ = "messages"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    conversation_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("conversations.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Message metadata
    sender_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        index=True  # 'user' or 'assistant'
    )
    
    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_messages_conversation_id', 'conversation_id'),
        Index('ix_messages_sender_type', 'sender_type'),
        Index('ix_messages_created_at', 'created_at'),
        Index('ix_messages_conversation_created', 'conversation_id', 'created_at'),
        Index('ix_messages_conversation_sender', 'conversation_id', 'sender_type'),
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender='{self.sender_type}', content='{content_preview}')>"
    
    def is_from_user(self) -> bool:
        """Check if message is from user"""
        return self.sender_type == "user"
    
    def is_from_assistant(self) -> bool:
        """Check if message is from assistant"""
        return self.sender_type == "assistant"