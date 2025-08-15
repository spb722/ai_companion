#!/usr/bin/env python3
"""
Database seeding script for AI Companion
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.services.database import get_db_session
from app.db.seed_characters import seed_characters, get_character_count


async def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...")
    
    try:
        async with get_db_session() as db:
            print(f"📊 Current character count: {await get_character_count(db)}")
            
            # Seed characters
            print("🎭 Seeding characters...")
            await seed_characters(db)
            
            print(f"📊 Final character count: {await get_character_count(db)}")
            print("✅ Database seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())