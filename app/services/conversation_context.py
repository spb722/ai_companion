"""
Conversation context manager for efficient chat context handling
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import desc, select

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.database import get_db_session
from app.services.redis import redis_service

logger = logging.getLogger(__name__)


class ConversationContext:
    """Conversation context manager with efficient caching"""
    
    async def get_or_create_conversation(
        self,
        user_id: int,
        character_id: int
    ) -> Optional[Conversation]:
        """
        Get existing conversation or create new one
        
        Args:
            user_id: User ID
            character_id: Character ID
            
        Returns:
            Optional[Conversation]: Conversation instance or None if error
        """
        try:
            async with get_db_session() as session:
                # Try to find existing conversation
                stmt = select(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.character_id == character_id
                ).order_by(desc(Conversation.last_message_at)).limit(1)
                
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()
                
                if conversation:
                    logger.debug(f"Found existing conversation {conversation.id} for user {user_id} and character {character_id}")
                    return conversation
                
                # Create new conversation
                new_conversation = Conversation(
                    user_id=user_id,
                    character_id=character_id,
                    started_at=datetime.utcnow(),
                    message_count=0
                )
                
                session.add(new_conversation)
                await session.commit()
                await session.refresh(new_conversation)
                
                logger.info(f"Created new conversation {new_conversation.id} for user {user_id} and character {character_id}")
                return new_conversation
                
        except Exception as e:
            logger.error(f"Failed to get or create conversation for user {user_id} and character {character_id}: {e}")
            return None
    
    async def get_conversation_cache_key(
        self,
        conversation_id: int
    ) -> Optional[str]:
        """
        Get the cache key for a conversation by looking up user and character IDs
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Optional[str]: Cache key or None if conversation not found
        """
        try:
            async with get_db_session() as session:
                conversation = await session.get(Conversation, conversation_id)
                if conversation:
                    return f"conv:{conversation.user_id}:{conversation.character_id}"
                return None
        except Exception as e:
            logger.error(f"Failed to get cache key for conversation {conversation_id}: {e}")
            return None
    
    async def get_message_context(
        self,
        conversation_id: int,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get recent messages for conversation context
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve (default: 5)
            
        Returns:
            List[Dict[str, str]]: List of messages in OpenAI format
        """
        # Try to get from cache first (original method)
        cache_key = f"conv:{conversation_id}:ctx:{limit}"
        cached_context = await redis_service.get_cache(cache_key)
        
        if cached_context:
            logger.debug(f"Retrieved cached context for conversation {conversation_id}")
            return cached_context
        
        # Also try conversation-level cache (new caching method)
        if limit == 5:  # Our conversation cache stores 5 messages
            conversation_cache_key = await self.get_conversation_cache_key(conversation_id)
            if conversation_cache_key:
                conversation_cached = await redis_service.get_cache(conversation_cache_key)
                if conversation_cached:
                    # Convert to OpenAI format
                    context = []
                    for msg in conversation_cached:
                        role = "user" if msg.get("sender_type") == "user" else "assistant"
                        context.append({
                            "role": role,
                            "content": msg.get("content", "")
                        })
                    logger.debug(f"Retrieved conversation-level cached context for conversation {conversation_id}")
                    return context
        
        try:
            async with get_db_session() as session:
                # Get recent messages
                stmt = select(Message).where(
                    Message.conversation_id == conversation_id
                ).order_by(desc(Message.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                # Convert to OpenAI format (oldest first)
                context = []
                for message in reversed(messages):
                    role = "user" if message.sender_type == "user" else "assistant"
                    context.append({
                        "role": role,
                        "content": message.content
                    })
                
                # Cache the context for 1 hour
                await redis_service.set_cache(cache_key, context, ttl_seconds=3600)
                
                logger.debug(f"Retrieved {len(context)} messages for conversation {conversation_id}")
                return context
                
        except Exception as e:
            logger.error(f"Failed to get message context for conversation {conversation_id}: {e}")
            return []
    
    def format_for_llm(
        self,
        system_prompt: str,
        context_messages: List[Dict[str, str]],
        user_message: str
    ) -> List[Dict[str, str]]:
        """
        Format messages for LLM consumption
        
        Args:
            system_prompt: System prompt for the character
            context_messages: Previous conversation messages
            user_message: Current user message
            
        Returns:
            List[Dict[str, str]]: Formatted messages for LLM
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context messages
        messages.extend(context_messages)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def estimate_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for messages using simple heuristic
        
        Args:
            messages: List of messages
            
        Returns:
            int: Estimated token count
        """
        total_chars = sum(len(msg["content"]) for msg in messages)
        # Rough estimate: 1 token ≈ 4 characters (works for most languages)
        estimated_tokens = total_chars // 4
        
        # Add overhead for message structure (role, formatting, etc.)
        overhead = len(messages) * 10
        
        return estimated_tokens + overhead
    
    async def save_user_message(
        self,
        conversation_id: int,
        content: str
    ) -> Optional[Message]:
        """
        Save user message to database
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            
        Returns:
            Optional[Message]: Saved message or None if error
        """
        try:
            async with get_db_session() as session:
                message = Message(
                    conversation_id=conversation_id,
                    sender_type="user",
                    content=content
                )
                
                session.add(message)
                
                # Update conversation metadata
                conversation = await session.get(Conversation, conversation_id)
                if conversation:
                    conversation.increment_message_count()
                
                await session.commit()
                await session.refresh(message)
                
                # Clear cached context
                await self._clear_conversation_cache(conversation_id)
                
                logger.debug(f"Saved user message {message.id} to conversation {conversation_id}")
                return message
                
        except Exception as e:
            logger.error(f"Failed to save user message to conversation {conversation_id}: {e}")
            return None
    
    async def save_assistant_message(
        self,
        conversation_id: int,
        content: str
    ) -> Optional[Message]:
        """
        Save assistant message to database
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            
        Returns:
            Optional[Message]: Saved message or None if error
        """
        try:
            async with get_db_session() as session:
                message = Message(
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    content=content
                )
                
                session.add(message)
                
                # Update conversation metadata
                conversation = await session.get(Conversation, conversation_id)
                if conversation:
                    conversation.increment_message_count()
                
                await session.commit()
                await session.refresh(message)
                
                # Clear cached context
                await self._clear_conversation_cache(conversation_id)
                
                logger.debug(f"Saved assistant message {message.id} to conversation {conversation_id}")
                return message
                
        except Exception as e:
            logger.error(f"Failed to save assistant message to conversation {conversation_id}: {e}")
            return None
    
    async def _clear_conversation_cache(self, conversation_id: int) -> None:
        """Clear cached context for conversation"""
        try:
            # Clear common cache keys
            cache_patterns = [
                f"conv:{conversation_id}:ctx:5",
                f"conv:{conversation_id}:ctx:10",
                f"conv:{conversation_id}:ctx:20"
            ]
            
            for pattern in cache_patterns:
                await redis_service.delete_cache(pattern)
                
        except Exception as e:
            logger.error(f"Failed to clear conversation cache for {conversation_id}: {e}")
    
    async def get_conversation_stats(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get conversation statistics
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict[str, Any]: Conversation statistics
        """
        try:
            async with get_db_session() as session:
                conversation = await session.get(Conversation, conversation_id)
                
                if not conversation:
                    return {}
                
                return {
                    "id": conversation.id,
                    "user_id": conversation.user_id,
                    "character_id": conversation.character_id,
                    "message_count": conversation.message_count,
                    "started_at": conversation.started_at.isoformat(),
                    "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get conversation stats for {conversation_id}: {e}")
            return {}


# Global conversation context instance
conversation_context = ConversationContext()