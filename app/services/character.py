"""
Character service for managing AI companion characters
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.character import Character
from app.models.user import User
from app.services.redis import redis_service

logger = logging.getLogger(__name__)


class CharacterService:
    """Service for character-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = redis_service
    
    async def get_all_characters(self, user_is_premium: bool = False) -> List[Character]:
        """
        Get all characters available to the user based on their subscription tier
        
        Args:
            user_is_premium: Whether the user has a premium subscription
            
        Returns:
            List[Character]: List of available characters
        """
        try:
            if user_is_premium:
                # Premium users get all characters
                result = await self.db.execute(
                    select(Character).order_by(Character.id)
                )
            else:
                # Free users only get non-premium characters
                result = await self.db.execute(
                    select(Character)
                    .where(Character.is_premium == False)
                    .order_by(Character.id)
                )
            
            characters = result.scalars().all()
            logger.debug(f"Retrieved {len(characters)} characters for {'premium' if user_is_premium else 'free'} user")
            return list(characters)
            
        except Exception as e:
            logger.error(f"Failed to get characters: {e}")
            return []
    
    async def get_character_by_id(self, character_id: int) -> Optional[Character]:
        """
        Get a character by ID
        
        Args:
            character_id: Character ID
            
        Returns:
            Optional[Character]: Character if found, None otherwise
        """
        try:
            result = await self.db.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()
            
            if character:
                logger.debug(f"Found character: {character.name} (ID: {character_id})")
            else:
                logger.warning(f"Character not found: ID {character_id}")
            
            return character
            
        except Exception as e:
            logger.error(f"Failed to get character {character_id}: {e}")
            return None
    
    async def can_user_access_character(
        self, 
        character_id: int, 
        user_is_premium: bool
    ) -> bool:
        """
        Check if a user can access a specific character
        
        Args:
            character_id: Character ID
            user_is_premium: Whether the user has a premium subscription
            
        Returns:
            bool: True if user can access the character, False otherwise
        """
        character = await self.get_character_by_id(character_id)
        if not character:
            return False
        
        return character.can_be_used_by_user(user_is_premium)
    
    async def select_character(
        self, 
        user_id: int, 
        character_id: int, 
        user_is_premium: bool = False
    ) -> Dict[str, Any]:
        """
        Select a character for a user
        
        Args:
            user_id: User ID
            character_id: Character ID to select
            user_is_premium: Whether the user has a premium subscription
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Check if character exists and user can access it
            if not await self.can_user_access_character(character_id, user_is_premium):
                character = await self.get_character_by_id(character_id)
                if not character:
                    return {
                        "success": False,
                        "message": "Character not found",
                        "error_code": "CHARACTER_NOT_FOUND"
                    }
                else:
                    return {
                        "success": False,
                        "message": "This character requires a premium subscription",
                        "error_code": "PREMIUM_REQUIRED"
                    }
            
            # Store selection in Redis
            success = await self.redis.set_user_character(user_id, character_id)
            
            if success:
                character = await self.get_character_by_id(character_id)
                logger.info(f"User {user_id} selected character {character_id} ({character.name})")
                return {
                    "success": True,
                    "message": f"Successfully selected {character.name}",
                    "character": {
                        "id": character.id,
                        "name": character.name,
                        "personality_type": character.personality_type
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to save character selection",
                    "error_code": "CACHE_ERROR"
                }
                
        except Exception as e:
            logger.error(f"Failed to select character for user {user_id}: {e}")
            return {
                "success": False,
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
    
    async def get_user_selected_character(self, user_id: int) -> Optional[Character]:
        """
        Get the user's currently selected character
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[Character]: Selected character if found, None otherwise
        """
        try:
            # First try to get from Redis cache
            character_id = await self.redis.get_user_character(user_id)
            
            if character_id:
                character = await self.get_character_by_id(character_id)
                if character:
                    logger.debug(f"User {user_id} has character {character_id} selected from cache")
                    return character
                else:
                    # Character not found in DB, clear cache
                    await self.redis.clear_user_character(user_id)
                    logger.warning(f"Cleared invalid character selection for user {user_id}")
            
            # No character selected or cached selection is invalid
            logger.debug(f"No character selected for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get selected character for user {user_id}: {e}")
            return None
    
    async def clear_user_character_selection(self, user_id: int) -> bool:
        """
        Clear a user's character selection
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = await self.redis.clear_user_character(user_id)
            logger.info(f"Cleared character selection for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to clear character selection for user {user_id}: {e}")
            return False
    
    async def get_default_character_for_user(self, user_is_premium: bool = False) -> Optional[Character]:
        """
        Get the default character for a new user
        
        Args:
            user_is_premium: Whether the user has a premium subscription
            
        Returns:
            Optional[Character]: Default character (first available free character)
        """
        try:
            # Get the first available character for the user
            result = await self.db.execute(
                select(Character)
                .where(Character.is_premium == False)  # Always start with free character
                .order_by(Character.id)
                .limit(1)
            )
            
            character = result.scalar_one_or_none()
            if character:
                logger.debug(f"Default character for new user: {character.name}")
            else:
                logger.error("No default character available")
            
            return character
            
        except Exception as e:
            logger.error(f"Failed to get default character: {e}")
            return None
    
    async def ensure_user_has_character(
        self, 
        user_id: int, 
        user_is_premium: bool = False
    ) -> Optional[Character]:
        """
        Ensure user has a character selected, assign default if not
        
        Args:
            user_id: User ID
            user_is_premium: Whether the user has a premium subscription
            
        Returns:
            Optional[Character]: User's character (selected or default)
        """
        try:
            # Check if user already has a character selected
            character = await self.get_user_selected_character(user_id)
            
            if character:
                # Verify user can still access this character (in case subscription changed)
                if character.can_be_used_by_user(user_is_premium):
                    return character
                else:
                    # User can no longer access this character, clear and assign default
                    await self.clear_user_character_selection(user_id)
                    logger.info(f"Cleared inaccessible character for user {user_id}")
            
            # No character or inaccessible character, assign default
            default_character = await self.get_default_character_for_user(user_is_premium)
            if default_character:
                result = await self.select_character(user_id, default_character.id, user_is_premium)
                if result["success"]:
                    logger.info(f"Assigned default character {default_character.name} to user {user_id}")
                    return default_character
            
            logger.error(f"Failed to ensure character for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to ensure character for user {user_id}: {e}")
            return None