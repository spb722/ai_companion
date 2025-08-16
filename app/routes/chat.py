"""
Chat API endpoints with Server-Sent Events support
"""

import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.chat_service import chat_service
from app.services.llm_service import llm_service
from app.services.character import character_service
from app.middleware.auth import get_current_user
from app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response Models
class ChatMessageRequest(BaseModel):
    """Request model for sending chat messages"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message content")
    stream: bool = Field(True, description="Whether to stream the response")


class ChatHistoryRequest(BaseModel):
    """Request model for chat history"""
    limit: int = Field(20, ge=1, le=100, description="Number of messages to retrieve")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class SwitchCharacterRequest(BaseModel):
    """Request model for switching characters"""
    character_id: int = Field(..., description="New character ID")


# Utility functions
def format_sse_message(data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Events message"""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


async def sse_generator(user: User, message_content: str, stream: bool):
    """Generate SSE stream for chat responses"""
    try:
        # Get user's selected character
        character = await character_service.get_user_selected_character(user.id)
        if not character:
            yield format_sse_message({
                "type": "error",
                "error": "No character selected. Please select a character first.",
                "code": "CHARACTER_NOT_SELECTED"
            })
            return
        
        async for chunk in chat_service.process_message(
            user=user,
            message_content=message_content,
            character_id=character.id,
            stream=stream
        ):
            yield format_sse_message(chunk)
        
        # Send end-of-stream marker
        yield format_sse_message({"type": "end"})
        
    except Exception as e:
        logger.error(f"Error in SSE generator: {e}")
        yield format_sse_message({
            "type": "error",
            "error": "Stream connection error",
            "code": "SSE_ERROR"
        })


# Chat Endpoints
@router.post("/send")
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to AI companion with streaming response
    
    Returns Server-Sent Events stream with chat response
    """
    try:
        # Get user's selected character
        character = await character_service.get_user_selected_character(current_user.id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "error",
                    "error": "No character selected. Please select a character first.",
                    "code": "CHARACTER_NOT_SELECTED"
                }
            )
        
        logger.info(f"Processing message from user {current_user.id}, character: {character.id} ({character.name})")
        
        if request.stream:
            # Return SSE stream
            return StreamingResponse(
                sse_generator(
                    user=current_user,
                    message_content=request.message,
                    stream=True
                ),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        else:
            # Return complete response
            response_parts = []
            async for chunk in chat_service.process_message(
                user=current_user,
                message_content=request.message,
                character_id=character.id,
                stream=False
            ):
                response_parts.append(chunk)
            
            return {"messages": response_parts}
            
    except Exception as e:
        logger.error(f"Error sending message for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.get("/history")
async def get_chat_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Get conversation history for user and selected character
    
    Args:
        limit: Number of messages to return (1-100)
        offset: Offset for pagination
    
    Returns:
        Conversation history with pagination metadata
    """
    try:
        # Get user's selected character
        character = await character_service.get_user_selected_character(current_user.id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "error",
                    "error": "No character selected. Please select a character first.",
                    "code": "CHARACTER_NOT_SELECTED"
                }
            )
        
        # Validate parameters
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset must be non-negative"
            )
        
        history = await chat_service.get_conversation_history(
            user_id=current_user.id,
            character_id=character.id,
            limit=limit,
            offset=offset
        )
        
        if "error" in history:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve conversation history"
            )
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.post("/switch-character")
async def switch_character(
    request: SwitchCharacterRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Switch user's selected character
    
    Args:
        request: Character switch request with new character ID
    
    Returns:
        Success status and character information
    """
    try:
        result = await chat_service.switch_character(
            user_id=current_user.id,
            character_id=request.character_id
        )
        
        if not result["success"]:
            if result.get("code") == "CHARACTER_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Character not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Failed to switch character")
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching character for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to switch character"
        )


@router.get("/provider")
async def get_provider_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current LLM provider status and information
    
    Returns:
        Provider status, available providers, and current model
    """
    try:
        status_info = await chat_service.get_service_status()
        
        # Add provider-specific headers for debugging
        provider_headers = {
            "X-LLM-Provider": status_info.get("current_provider", "unknown"),
            "X-LLM-Model": status_info.get("current_model", "unknown"),
            "X-Service-Status": status_info.get("status", "unknown")
        }
        
        return {
            "data": status_info,
            "headers": provider_headers
        }
        
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get provider status"
        )


# Admin Endpoints (for provider management)
@router.post("/admin/llm/switch")
async def admin_switch_provider(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint to manually switch LLM provider
    
    Args:
        provider: Provider name to switch to (groq/openai)
    
    Returns:
        Switch operation result
    """
    try:
        # TODO: Add admin role check
        # For now, allow any authenticated user (should be restricted in production)
        
        if provider not in ['groq', 'openai']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid provider. Must be 'groq' or 'openai'"
            )
        
        success = llm_service.switch_provider(provider)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{provider}' is not available or configured"
            )
        
        # Get updated status
        status_info = llm_service.get_provider_info()
        
        return {
            "success": True,
            "message": f"Switched to provider: {provider}",
            "provider_info": status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching provider to {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to switch provider"
        )


@router.get("/admin/llm/test")
async def admin_test_provider(
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint to test LLM provider connectivity
    
    Args:
        provider: Specific provider to test (optional)
    
    Returns:
        Connection test results
    """
    try:
        # TODO: Add admin role check
        
        if provider and provider not in ['groq', 'openai']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid provider. Must be 'groq' or 'openai'"
            )
        
        test_result = await llm_service.test_connection(provider)
        
        from datetime import datetime
        
        logger.info(f"Provider test result for {provider}: {test_result}")
        
        return {
            "provider": provider or llm_service._current_provider,
            "connected": test_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing provider {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test provider"
        )