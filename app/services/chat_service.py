"""
Main chat service with provider failover and streaming support
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, Tuple
from datetime import datetime

from app.models.character import Character
from app.models.user import User
from app.services.llm_service import llm_service
from app.services.conversation_context import conversation_context
from app.services.prompt_builder import prompt_builder
from app.services.character import character_service
from app.services.redis import redis_service

logger = logging.getLogger(__name__)


class ChatService:
    """Main chat service with provider failover and streaming"""
    
    def __init__(self):
        self.default_delay = 1.0  # Natural feeling delay in seconds
        self.max_retries = 2
        self.retry_delay = 1.0
    
    async def process_message(
        self,
        user: User,
        message_content: str,
        character_id: Optional[int] = None,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message and generate AI response with streaming
        
        Args:
            user: User instance
            message_content: User's message content
            character_id: Optional character ID (will use cached or default)
            stream: Whether to stream the response
            
        Yields:
            Dict[str, Any]: Streaming response chunks with metadata
        """
        start_time = datetime.utcnow()
        conversation_id = None
        provider_used = None
        
        try:
            # Validate character selection
            character = await self._get_user_character(user.id, character_id)
            if not character:
                yield {
                    "type": "error",
                    "error": "No character selected. Please select a character first.",
                    "code": "CHARACTER_NOT_SELECTED"
                }
                return
            
            # Get or create conversation
            conversation = await conversation_context.get_or_create_conversation(
                user.id, character.id
            )
            if not conversation:
                yield {
                    "type": "error", 
                    "error": "Failed to create conversation session.",
                    "code": "CONVERSATION_ERROR"
                }
                return
            
            conversation_id = conversation.id
            
            # Save user message
            user_message = await conversation_context.save_user_message(
                conversation_id, message_content
            )
            if not user_message:
                logger.warning(f"Failed to save user message for conversation {conversation_id}")
            
            # Get conversation context
            context_messages = await conversation_context.get_message_context(
                conversation_id, limit=5
            )
            
            # Get available provider
            provider_used = await llm_service.get_available_provider()
            if not provider_used:
                yield {
                    "type": "error",
                    "error": "AI service is currently unavailable. Please try again later.",
                    "code": "SERVICE_UNAVAILABLE"
                }
                return
            
            # Get user's language preference
            user_language = getattr(user, 'preferred_language', 'en') or 'en'
            
            # Build messages for LLM
            messages = prompt_builder.build_messages(
                character=character,
                context_messages=context_messages,
                user_message=message_content,
                language=user_language,
                provider=provider_used
            )
            
            # Validate token count
            estimated_tokens = prompt_builder.estimate_total_tokens(messages)
            if estimated_tokens > 4000:  # Safety limit
                # Reduce context and try again
                context_messages = context_messages[-2:]  # Keep only last 2 messages
                messages = prompt_builder.build_messages(
                    character=character,
                    context_messages=context_messages,
                    user_message=message_content,
                    language=user_language,
                    provider=provider_used
                )
                logger.warning(f"Reduced context for conversation {conversation_id} due to token limit")
            
            # Send initial metadata
            yield {
                "type": "metadata",
                "conversation_id": conversation_id,
                "character": {
                    "id": character.id,
                    "name": character.name,
                    "personality_type": character.personality_type
                },
                "provider": provider_used,
                "estimated_tokens": estimated_tokens
            }
            
            # Add natural delay for better UX
            await asyncio.sleep(self.default_delay)
            
            # Generate AI response
            response_content = ""
            async for chunk in self._generate_ai_response(
                messages, provider_used, stream
            ):
                if chunk["type"] == "content":
                    response_content += chunk["content"]
                    yield chunk
                elif chunk["type"] == "error":
                    yield chunk
                    return
            
            # Save assistant message
            if response_content.strip():
                assistant_message = await conversation_context.save_assistant_message(
                    conversation_id, response_content.strip()
                )
                if not assistant_message:
                    logger.warning(f"Failed to save assistant message for conversation {conversation_id}")
            
            # Send completion metadata
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            yield {
                "type": "complete",
                "conversation_id": conversation_id,
                "provider_used": provider_used,
                "duration_seconds": duration,
                "message_length": len(response_content),
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing message for user {user.id}: {e}")
            yield {
                "type": "error",
                "error": "An unexpected error occurred while processing your message.",
                "code": "PROCESSING_ERROR",
                "conversation_id": conversation_id,
                "provider": provider_used
            }
    
    async def _get_user_character(
        self, 
        user_id: int, 
        character_id: Optional[int] = None
    ) -> Optional[Character]:
        """Get user's selected character"""
        try:
            # If character_id provided, use it and cache the selection
            if character_id:
                character = await character_service.get_character_by_id(character_id)
                if character:
                    # Cache the selection
                    await redis_service.set_user_character(user_id, character_id)
                    return character
            
            # Try to get cached character selection
            cached_character_id = await redis_service.get_user_character(user_id)
            if cached_character_id:
                character = await character_service.get_character_by_id(cached_character_id)
                if character:
                    return character
            
            # If no character cached, get default character
            characters = await character_service.get_all_characters()
            if characters:
                default_character = characters[0]  # Use first character as default
                await redis_service.set_user_character(user_id, default_character.id)
                return default_character
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting character for user {user_id}: {e}")
            return None
    
    async def _generate_ai_response(
        self,
        messages: list,
        provider: str,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate AI response with provider failover"""
        retries = 0
        
        while retries <= self.max_retries:
            try:
                # Get LLM client and model
                client = llm_service.get_client(provider)
                model = llm_service.get_model(provider)
                
                logger.debug(f"Generating response with {provider} using model {model}")
                
                # Create completion with streaming
                completion = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=stream,
                    temperature=0.7,
                    max_tokens=500,  # Reasonable limit for chat responses
                    presence_penalty=0.6,
                    frequency_penalty=0.3
                )
                
                if stream:
                    # Handle streaming response
                    async for chunk in completion:
                        if chunk.choices and chunk.choices[0].delta:
                            content = chunk.choices[0].delta.content
                            if content:
                                yield {
                                    "type": "content",
                                    "content": content,
                                    "provider": provider
                                }
                        
                        # Check for finish reason
                        if chunk.choices and chunk.choices[0].finish_reason:
                            break
                else:
                    # Handle non-streaming response
                    if completion.choices and completion.choices[0].message:
                        content = completion.choices[0].message.content
                        if content:
                            yield {
                                "type": "content",
                                "content": content,
                                "provider": provider
                            }
                
                # If we get here, generation was successful
                return
                
            except Exception as e:
                logger.error(f"Error with {provider} provider (attempt {retries + 1}): {e}")
                retries += 1
                
                if retries <= self.max_retries:
                    # Try fallback provider
                    if provider == llm_service._current_provider and llm_service._fallback_provider:
                        provider = llm_service._fallback_provider
                        logger.info(f"Switching to fallback provider: {provider}")
                    else:
                        # Try any available provider
                        available_provider = await llm_service.get_available_provider()
                        if available_provider and available_provider != provider:
                            provider = available_provider
                            logger.info(f"Switching to alternative provider: {provider}")
                        else:
                            # No more providers to try
                            break
                    
                    # Small delay before retry
                    await asyncio.sleep(self.retry_delay)
                else:
                    break
        
        # If we reach here, all attempts failed
        yield {
            "type": "error",
            "error": "AI service is currently experiencing issues. Please try again in a moment.",
            "code": "GENERATION_FAILED",
            "provider": provider,
            "retries": retries
        }
    
    async def get_conversation_history(
        self,
        user_id: int,
        character_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get conversation history for user and character
        
        Args:
            user_id: User ID
            character_id: Character ID
            limit: Number of messages to return
            offset: Offset for pagination
            
        Returns:
            Dict[str, Any]: Conversation history with metadata
        """
        try:
            # Get conversation
            conversation = await conversation_context.get_or_create_conversation(
                user_id, character_id
            )
            
            if not conversation:
                return {"messages": [], "total": 0, "conversation_id": None}
            
            # Get messages with pagination
            messages = await conversation_context.get_message_context(
                conversation.id, limit=limit
            )
            
            # Get conversation stats
            stats = await conversation_context.get_conversation_stats(conversation.id)
            
            return {
                "conversation_id": conversation.id,
                "messages": messages,
                "total": stats.get("message_count", 0),
                "character_id": character_id,
                "user_id": user_id,
                "started_at": stats.get("started_at"),
                "last_message_at": stats.get("last_message_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation history for user {user_id}, character {character_id}: {e}")
            return {"messages": [], "total": 0, "conversation_id": None, "error": str(e)}
    
    async def switch_character(
        self,
        user_id: int,
        character_id: int
    ) -> Dict[str, Any]:
        """
        Switch user's selected character
        
        Args:
            user_id: User ID
            character_id: New character ID
            
        Returns:
            Dict[str, Any]: Operation result
        """
        try:
            # Validate character exists
            character = await character_service.get_character_by_id(character_id)
            if not character:
                return {
                    "success": False,
                    "error": "Character not found",
                    "code": "CHARACTER_NOT_FOUND"
                }
            
            # Update cached selection
            success = await redis_service.set_user_character(user_id, character_id)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to update character selection",
                    "code": "CACHE_ERROR"
                }
            
            return {
                "success": True,
                "character": {
                    "id": character.id,
                    "name": character.name,
                    "personality_type": character.personality_type,
                    "description": character.description
                }
            }
            
        except Exception as e:
            logger.error(f"Error switching character for user {user_id}: {e}")
            return {
                "success": False,
                "error": "An error occurred while switching characters",
                "code": "SWITCH_ERROR"
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get chat service status and provider information"""
        try:
            provider_info = llm_service.get_provider_info()
            available_provider = await llm_service.get_available_provider()
            
            return {
                "status": "healthy" if available_provider else "degraded",
                "current_provider": provider_info["current_provider"],
                "fallback_provider": provider_info["fallback_provider"],
                "available_providers": provider_info["available_providers"],
                "available_provider": available_provider,
                "current_model": provider_info["current_model"]
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global chat service instance
chat_service = ChatService()