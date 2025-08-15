#!/usr/bin/env python3
"""
Test script for the character system implementation
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.database import get_db_session
from app.db.seed_characters import seed_characters, get_character_count
from app.services.character import CharacterService
from app.services.redis import redis_service
from app.prompts.character_prompts import (
    get_character_prompt_by_character_id,
    validate_prompt_coverage,
    get_available_languages,
    get_available_personalities
)


async def test_character_system():
    """Test the complete character system"""
    print("🧪 Testing Character System")
    print("=" * 50)
    
    try:
        # Test 1: Database seeding
        print("\n1️⃣ Testing database seeding...")
        async with get_db_session() as db:
            initial_count = await get_character_count(db)
            print(f"   Initial character count: {initial_count}")
            
            await seed_characters(db)
            final_count = await get_character_count(db)
            print(f"   Final character count: {final_count}")
            
            assert final_count >= 3, "Should have at least 3 characters"
            print("   ✅ Database seeding successful!")
        
        # Test 2: Character Service
        print("\n2️⃣ Testing character service...")
        async with get_db_session() as db:
            service = CharacterService(db)
            
            # Test getting all characters for free user
            free_chars = await service.get_all_characters(user_is_premium=False)
            print(f"   Free user characters: {len(free_chars)}")
            
            # Test getting all characters for premium user
            premium_chars = await service.get_all_characters(user_is_premium=True)
            print(f"   Premium user characters: {len(premium_chars)}")
            
            assert len(premium_chars) >= len(free_chars), "Premium should have at least as many characters"
            print("   ✅ Character service working!")
        
        # Test 3: Redis caching
        print("\n3️⃣ Testing Redis caching...")
        test_user_id = 12345
        test_character_id = 1
        
        # Test setting character selection
        success = await redis_service.set_user_character(test_user_id, test_character_id)
        assert success, "Should be able to set character selection"
        
        # Test getting character selection
        cached_id = await redis_service.get_user_character(test_user_id)
        assert cached_id == test_character_id, "Should retrieve the same character ID"
        
        # Test clearing selection
        cleared = await redis_service.clear_user_character(test_user_id)
        assert cleared, "Should be able to clear selection"
        
        # Verify it's cleared
        cached_id_after = await redis_service.get_user_character(test_user_id)
        assert cached_id_after is None, "Character selection should be cleared"
        
        print("   ✅ Redis caching working!")
        
        # Test 4: Prompt system
        print("\n4️⃣ Testing prompt system...")
        
        # Test prompt coverage
        coverage = validate_prompt_coverage()
        print(f"   Prompt coverage: {coverage['coverage_percentage']:.1f}%")
        print(f"   Total combinations: {coverage['total_combinations']}")
        print(f"   Covered combinations: {coverage['covered_combinations']}")
        
        assert coverage['coverage_percentage'] == 100.0, "Should have 100% prompt coverage"
        
        # Test getting specific prompt
        prompt = get_character_prompt_by_character_id(1, "friendly", "en")
        assert prompt is not None, "Should get prompt for valid character"
        assert len(prompt) > 100, "Prompt should be substantial"
        
        # Test language fallback
        fallback_prompt = get_character_prompt_by_character_id(1, "friendly", "invalid")
        assert fallback_prompt is not None, "Should fallback to English for invalid language"
        
        print("   ✅ Prompt system working!")
        
        # Test 5: Available options
        print("\n5️⃣ Testing available options...")
        languages = get_available_languages()
        personalities = get_available_personalities()
        
        print(f"   Available languages: {languages}")
        print(f"   Available personalities: {personalities}")
        
        assert len(languages) == 3, "Should have 3 languages"
        assert len(personalities) == 3, "Should have 3 personalities"
        
        print("   ✅ Available options correct!")
        
        print("\n🎉 All tests passed! Character system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def cleanup_test_data():
    """Clean up any test data"""
    try:
        # Clear any test Redis data
        await redis_service.clear_user_character(12345)
        await redis_service.close()
    except:
        pass


async def main():
    """Main test function"""
    success = await test_character_system()
    await cleanup_test_data()
    
    if success:
        print("\n✅ Character system test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Character system test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())