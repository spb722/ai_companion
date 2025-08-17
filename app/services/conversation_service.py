"""
Conversation management service for handling user conversations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import desc, select

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.database import get_db_session
from app.services.redis import redis_service

logger = logging.getLogger(__name__)


class ConversationService:
    """Conversation management service for handling user conversations"""
    
    async def get_or_create_conversation(
        self,
        user_id: int,
        character_id: int
    ) -> Optional[Conversation]:
        """
        Get existing conversation or create new one.
        Finds existing conversation for user-character pair or creates new one.
        
        Args:
            user_id: User ID
            character_id: Character ID
            
        Returns:
            Optional[Conversation]: Conversation instance or None if error
        """
        try:
            async with get_db_session() as session:
                # Try to find existing conversation (get most recent one)
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
    
    async def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for a conversation.
        Fetches the last N messages from the conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve (default: 20)
            
        Returns:
            List[Dict[str, Any]]: List of messages with metadata
        """
        try:
            async with get_db_session() as session:
                # Get recent messages ordered by creation time (most recent first)
                stmt = select(Message).where(
                    Message.conversation_id == conversation_id
                ).order_by(desc(Message.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                # Convert to dict format (reverse to get chronological order)
                message_list = []
                for message in reversed(messages):
                    message_list.append({
                        "id": message.id,
                        "conversation_id": message.conversation_id,
                        "sender_type": message.sender_type,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                        "is_from_user": message.is_from_user(),
                        "is_from_assistant": message.is_from_assistant()
                    })
                
                logger.debug(f"Retrieved {len(message_list)} messages for conversation {conversation_id}")
                return message_list
                
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []
    
    async def add_message(
        self,
        conversation_id: int,
        sender_type: str,
        content: str
    ) -> Optional[Message]:
        """
        Add a new message to the conversation.
        Saves message and updates conversation metadata.
        
        Args:
            conversation_id: Conversation ID
            sender_type: Type of sender ("user" or "assistant")
            content: Message content
            
        Returns:
            Optional[Message]: Saved message or None if error
        """
        try:
            # Validate sender_type
            if sender_type not in ["user", "assistant"]:
                logger.error(f"Invalid sender_type: {sender_type}. Must be 'user' or 'assistant'")
                return None
            
            async with get_db_session() as session:
                # Create new message
                message = Message(
                    conversation_id=conversation_id,
                    sender_type=sender_type,
                    content=content
                )
                
                session.add(message)
                
                # Update conversation metadata
                conversation = await session.get(Conversation, conversation_id)
                if conversation:
                    conversation.increment_message_count()
                    conversation.update_last_message_at()
                
                await session.commit()
                await session.refresh(message)
                
                logger.debug(f"Added {sender_type} message {message.id} to conversation {conversation_id}")
                return message
                
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return None
    
    async def get_conversation_info(
        self,
        conversation_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get basic conversation information.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Optional[Dict[str, Any]]: Conversation info or None if not found
        """
        try:
            async with get_db_session() as session:
                conversation = await session.get(Conversation, conversation_id)
                
                if not conversation:
                    return None
                
                return {
                    "id": conversation.id,
                    "user_id": conversation.user_id,
                    "character_id": conversation.character_id,
                    "message_count": conversation.message_count,
                    "started_at": conversation.started_at.isoformat(),
                    "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get conversation info for {conversation_id}: {e}")
            return None
    
    async def cache_conversation_context(
        self,
        user_id: int,
        character_id: int,
        conversation_id: int
    ) -> bool:
        """
        Cache conversation context in Redis.
        Stores last 5 messages for quick access.
        
        Args:
            user_id: User ID
            character_id: Character ID
            conversation_id: Conversation ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get last 5 messages
            messages = await self.get_conversation_messages(conversation_id, limit=5)
            
            if not messages:
                # Cache empty context if no messages
                messages = []
            
            # Create cache key
            cache_key = f"conv:{user_id}:{character_id}"
            
            # Cache with 1 hour TTL (3600 seconds)
            success = await redis_service.set_cache(
                key=cache_key,
                value=messages,
                ttl_seconds=3600
            )
            
            if success:
                logger.debug(f"Cached conversation context for user {user_id}, character {character_id} ({len(messages)} messages)")
            else:
                logger.warning(f"Failed to cache conversation context for user {user_id}, character {character_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching conversation context for user {user_id}, character {character_id}: {e}")
            return False
    
    async def get_cached_context(
        self,
        user_id: int,
        character_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached conversation context from Redis.
        
        Args:
            user_id: User ID
            character_id: Character ID
            
        Returns:
            Optional[List[Dict[str, Any]]]: Cached messages or None if not found
        """
        try:
            cache_key = f"conv:{user_id}:{character_id}"
            
            cached_messages = await redis_service.get_cache(cache_key)
            
            if cached_messages is not None:
                logger.debug(f"Retrieved cached context for user {user_id}, character {character_id} ({len(cached_messages)} messages)")
                return cached_messages
            
            logger.debug(f"No cached context found for user {user_id}, character {character_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached context for user {user_id}, character {character_id}: {e}")
            return None
    
    async def clear_conversation_cache(
        self,
        user_id: int,
        character_id: int
    ) -> bool:
        """
        Clear cached conversation context.
        
        Args:
            user_id: User ID
            character_id: Character ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_key = f"conv:{user_id}:{character_id}"
            
            success = await redis_service.delete_cache(cache_key)
            
            if success:
                logger.debug(f"Cleared conversation cache for user {user_id}, character {character_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error clearing conversation cache for user {user_id}, character {character_id}: {e}")
            return False
    
    async def add_message_with_cache_update(
        self,
        conversation_id: int,
        sender_type: str,
        content: str,
        user_id: int,
        character_id: int
    ) -> Optional[Message]:
        """
        Add a message and update the conversation cache.
        This is a convenience method that combines message addition with cache updates.
        
        Args:
            conversation_id: Conversation ID
            sender_type: Type of sender ("user" or "assistant")
            content: Message content
            user_id: User ID (for cache key)
            character_id: Character ID (for cache key)
            
        Returns:
            Optional[Message]: Saved message or None if error
        """
        try:
            # Add the message using the regular method
            message = await self.add_message(conversation_id, sender_type, content)
            
            if message:
                # Update the cache in the background
                # Use try/except to ensure message saving isn't affected by cache failures
                try:
                    await self.cache_conversation_context(user_id, character_id, conversation_id)
                except Exception as cache_error:
                    logger.warning(f"Failed to update cache after adding message {message.id}: {cache_error}")
                
            return message
            
        except Exception as e:
            logger.error(f"Error adding message with cache update for conversation {conversation_id}: {e}")
            return None


# Global conversation service instance
conversation_service = ConversationService()