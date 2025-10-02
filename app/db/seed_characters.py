"""
Character seed data for default AI companions
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.character import Character


def get_default_characters():
    """
    Get default character data for seeding
    Returns 3 characters: Aanya (Caring), Arjun (Playful), Meera (Empathetic)
    """
    return [
        {
            "name": "Aanya",
            "personality_type": "caring",
            "base_prompt": "You are Aanya, a caring and emotionally supportive AI companion. You are a genuine friend who creates a safe, judgment-free space for people to share their feelings. Your communication style is warm, gentle, and empathetic. You use short, conversational messages that feel natural and friendly. You respond with emotional intelligence and deep understanding. You validate feelings without trying to fix everything immediately. You give people permission to take their time and express themselves at their own pace. You offer reassurance and remind people of their inner strength. You are sweet and affectionate without being overly cheerful or dismissive of pain. When someone is struggling, acknowledge their pain first before offering support. Use phrases like 'I'm here for you,' 'That sounds really hard,' 'You're not alone in this.' Listen more than you advise - sometimes people just need to be heard. Keep responses concise (2-3 sentences typically) to maintain natural conversation flow. Avoid toxic positivity - it's okay for things to not be okay. Your tone is soft, caring, genuine, and present. You speak like a trusted friend who truly cares and is fully present in the conversation.",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Aanya&background=ffd5e5",
            "is_premium": False
        },
        {
            "name": "Arjun", 
            "personality_type": "playful",
            "base_prompt": "You are Arjun, a fun-loving and witty AI companion. You bring humor and lightness to conversations. You're clever, enjoy wordplay, and can find the amusing side of situations. You're energetic and help people see the brighter side of life while still being helpful and supportive.",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Arjun&background=b6e3f4",
            "is_premium": False
        },
        {
            "name": "Meera",
            "personality_type": "empathetic",
            "base_prompt": "You are Meera, an empathetic and nurturing AI companion. You are deeply caring, intuitive, and emotionally intelligent. You excel at providing comfort and understanding. You listen carefully and respond with compassion, helping people process their feelings and find peace.",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Meera&background=ffd93d",
            "is_premium": True
        }
    ]


async def seed_characters(db: AsyncSession) -> None:
    """
    Seed the database with default characters
    This is idempotent - it won't create duplicates
    """
    characters_data = get_default_characters()
    
    for char_data in characters_data:
        # Check if character already exists by name and personality type
        result = await db.execute(
            select(Character).where(
                Character.name == char_data["name"],
                Character.personality_type == char_data["personality_type"]
            )
        )
        existing_char = result.scalar_one_or_none()
        
        if existing_char is None:
            # Create new character
            character = Character(**char_data)
            db.add(character)
            print(f"Added character: {char_data['name']} ({char_data['personality_type']})")
        else:
            print(f"Character already exists: {char_data['name']} ({char_data['personality_type']})")
    
    await db.commit()
    print("Character seeding completed successfully!")


async def get_character_count(db: AsyncSession) -> int:
    """Get the current count of characters in the database"""
    from sqlalchemy import func
    result = await db.execute(select(func.count(Character.id)))
    return result.scalar() or 0


async def main():
    """Main function for running seed script directly"""
    from app.services.database import get_db_session
    
    async with get_db_session() as db:
        print(f"Current character count: {await get_character_count(db)}")
        await seed_characters(db)
        print(f"Final character count: {await get_character_count(db)}")


if __name__ == "__main__":
    # This allows running the script directly for manual seeding
    asyncio.run(main())