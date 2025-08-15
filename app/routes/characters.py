"""
Character API endpoints for AI companion character management
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.database import get_db
from app.services.character import CharacterService
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.character import Character

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/characters", tags=["characters"])


# Response Models
class CharacterResponse(BaseModel):
    """Character response model"""
    id: int
    name: str
    personality_type: str
    avatar_url: Optional[str]
    is_premium: bool
    can_access: bool = Field(default=True, description="Whether current user can access this character")

    class Config:
        from_attributes = True


class CharacterSelectionResponse(BaseModel):
    """Character selection response model"""
    success: bool
    message: str
    character: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class CharacterListResponse(BaseModel):
    """Character list response model"""
    success: bool = True
    characters: List[CharacterResponse]
    total_count: int
    user_tier: str


class CurrentCharacterResponse(BaseModel):
    """Current character response model"""
    success: bool = True
    character: Optional[CharacterResponse] = None
    message: Optional[str] = None


# Request Models
class CharacterSelectionRequest(BaseModel):
    """Character selection request (empty body for POST requests)"""
    pass


@router.get("/", response_model=CharacterListResponse)
async def list_characters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of characters available to the current user
    
    Returns:
        CharacterListResponse: List of available characters
    """
    try:
        # Create character service
        character_service = CharacterService(db)
        
        # Determine if user is premium
        user_is_premium = current_user.subscription_tier == "pro"
        
        # Get available characters
        characters = await character_service.get_all_characters(user_is_premium)
        
        # Convert to response models
        character_responses = []
        for character in characters:
            can_access = character.can_be_used_by_user(user_is_premium)
            character_responses.append(
                CharacterResponse(
                    id=character.id,
                    name=character.name,
                    personality_type=character.personality_type,
                    avatar_url=character.avatar_url,
                    is_premium=character.is_premium,
                    can_access=can_access
                )
            )
        
        logger.info(f"User {current_user.id} requested character list, returned {len(character_responses)} characters")
        
        return CharacterListResponse(
            characters=character_responses,
            total_count=len(character_responses),
            user_tier=current_user.subscription_tier
        )
        
    except Exception as e:
        logger.error(f"Error listing characters for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve characters"
                }
            }
        )


@router.post("/{character_id}/select", response_model=CharacterSelectionResponse)
async def select_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Select a character for the current user
    
    Args:
        character_id: ID of the character to select
        
    Returns:
        CharacterSelectionResponse: Selection result
    """
    try:
        # Create character service
        character_service = CharacterService(db)
        
        # Determine if user is premium
        user_is_premium = current_user.subscription_tier == "pro"
        
        # Attempt to select character
        result = await character_service.select_character(
            user_id=current_user.id,
            character_id=character_id,
            user_is_premium=user_is_premium
        )
        
        if not result["success"]:
            # Map error codes to HTTP status codes
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            if result.get("error_code") == "CHARACTER_NOT_FOUND":
                status_code = status.HTTP_404_NOT_FOUND
            elif result.get("error_code") == "PREMIUM_REQUIRED":
                status_code = status.HTTP_403_FORBIDDEN
            
            logger.warning(f"Character selection failed for user {current_user.id}, character {character_id}: {result['message']}")
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "success": False,
                    "error": {
                        "code": result.get("error_code", "UNKNOWN_ERROR"),
                        "message": result["message"]
                    }
                }
            )
        
        logger.info(f"User {current_user.id} successfully selected character {character_id}")
        
        return CharacterSelectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting character {character_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to select character"
                }
            }
        )


@router.get("/current", response_model=CurrentCharacterResponse)
async def get_current_character(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's selected character
    
    Returns:
        CurrentCharacterResponse: Current character info
    """
    try:
        # Create character service
        character_service = CharacterService(db)
        
        # Get user's selected character
        character = await character_service.get_user_selected_character(current_user.id)
        
        if character:
            # Verify user can still access this character
            user_is_premium = current_user.subscription_tier == "pro"
            can_access = character.can_be_used_by_user(user_is_premium)
            
            character_response = CharacterResponse(
                id=character.id,
                name=character.name,
                personality_type=character.personality_type,
                avatar_url=character.avatar_url,
                is_premium=character.is_premium,
                can_access=can_access
            )
            
            logger.debug(f"User {current_user.id} has character {character.id} selected")
            
            return CurrentCharacterResponse(
                character=character_response,
                message=f"Current character: {character.name}"
            )
        else:
            logger.debug(f"User {current_user.id} has no character selected")
            
            return CurrentCharacterResponse(
                character=None,
                message="No character selected"
            )
        
    except Exception as e:
        logger.error(f"Error getting current character for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to get current character"
                }
            }
        )


@router.delete("/current", response_model=CharacterSelectionResponse)
async def clear_character_selection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear the current user's character selection
    
    Returns:
        CharacterSelectionResponse: Clearing result
    """
    try:
        # Create character service
        character_service = CharacterService(db)
        
        # Clear character selection
        success = await character_service.clear_user_character_selection(current_user.id)
        
        if success:
            logger.info(f"Cleared character selection for user {current_user.id}")
            
            return CharacterSelectionResponse(
                success=True,
                message="Character selection cleared successfully"
            )
        else:
            logger.warning(f"Failed to clear character selection for user {current_user.id}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "CACHE_ERROR",
                        "message": "Failed to clear character selection"
                    }
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing character selection for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to clear character selection"
                }
            }
        )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character_details(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific character
    
    Args:
        character_id: ID of the character to retrieve
        
    Returns:
        CharacterResponse: Character details
    """
    try:
        # Create character service
        character_service = CharacterService(db)
        
        # Get character by ID
        character = await character_service.get_character_by_id(character_id)
        
        if not character:
            logger.warning(f"Character {character_id} not found for user {current_user.id}")
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "CHARACTER_NOT_FOUND",
                        "message": "Character not found"
                    }
                }
            )
        
        # Check if user can access this character
        user_is_premium = current_user.subscription_tier == "pro"
        can_access = character.can_be_used_by_user(user_is_premium)
        
        character_response = CharacterResponse(
            id=character.id,
            name=character.name,
            personality_type=character.personality_type,
            avatar_url=character.avatar_url,
            is_premium=character.is_premium,
            can_access=can_access
        )
        
        logger.debug(f"User {current_user.id} requested details for character {character_id}")
        
        return character_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character {character_id} details for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to get character details"
                }
            }
        )