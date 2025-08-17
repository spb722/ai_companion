#!/usr/bin/env python3
"""
Quick test to verify quota functionality is working
"""

import asyncio
import aiohttp
import json

async def test_quota():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Quota Fix")
    print("=" * 50)
    
    # Test data
    test_user = {
        "email": f"quota_test_{int(__import__('time').time())}@example.com",
        "password": "testpass123",
        "preferred_language": "en"
    }
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Register user
        print("1️⃣ Registering test user...")
        async with session.post(f"{base_url}/auth/register", json=test_user) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data["access_token"]
                print(f"   ✅ User registered: {test_user['email']}")
            else:
                print(f"   ❌ Registration failed: {resp.status}")
                return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get characters
        print("2️⃣ Getting characters...")
        async with session.get(f"{base_url}/characters", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data["characters"]:
                    character_id = data["characters"][0]["id"]
                    print(f"   ✅ Selected character: {data['characters'][0]['name']} (ID: {character_id})")
                else:
                    print("   ❌ No characters available")
                    return
            else:
                print(f"   ❌ Failed to get characters: {resp.status}")
                return
        
        # 3. Select character
        print("3️⃣ Selecting character...")
        async with session.post(
            f"{base_url}/api/v1/chat/switch-character", 
            headers=headers,
            json={"character_id": character_id}
        ) as resp:
            if resp.status == 200:
                print("   ✅ Character selected")
            else:
                print(f"   ❌ Character selection failed: {resp.status}")
                return
        
        # 4. Check initial usage
        print("4️⃣ Checking initial quota...")
        async with session.get(f"{base_url}/api/v1/users/usage", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                initial_used = data["quota"]["used"]
                print(f"   📊 Initial usage: {initial_used}/{data['quota']['limit']} (Remaining: {data['quota']['remaining']})")
            else:
                print(f"   ❌ Failed to get usage: {resp.status}")
                return
        
        # 5. Send a test message
        print("5️⃣ Sending test message...")
        message_data = {
            "message": "Hello! This is a quota test message. Please respond briefly.",
            "stream": False
        }
        async with session.post(
            f"{base_url}/api/v1/chat/send", 
            headers=headers,
            json=message_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("   ✅ Message sent successfully")
                
                # Check if quota info is in response
                messages = data.get("messages", [])
                quota_found = False
                for msg in messages:
                    if msg.get("type") == "complete" and "quota" in msg:
                        quota = msg["quota"]
                        print(f"   📊 Updated quota: {quota['limit'] - quota['remaining']}/{quota['limit']} (Remaining: {quota['remaining']})")
                        quota_found = True
                        break
                
                if not quota_found:
                    print("   ⚠️  No quota info found in response")
            else:
                error_data = await resp.text()
                print(f"   ❌ Message failed: {resp.status}")
                print(f"   Error: {error_data}")
                return
        
        # 6. Check updated usage
        print("6️⃣ Checking updated quota...")
        async with session.get(f"{base_url}/api/v1/users/usage", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                final_used = data["quota"]["used"]
                print(f"   📊 Final usage: {final_used}/{data['quota']['limit']} (Remaining: {data['quota']['remaining']})")
                
                if final_used > initial_used:
                    print("   ✅ SUCCESS: Quota incremented correctly!")
                    print(f"   📈 Usage increased from {initial_used} to {final_used}")
                else:
                    print("   ❌ FAILED: Quota did not increment")
                    print(f"   📉 Usage stayed at {final_used}")
            else:
                print(f"   ❌ Failed to get final usage: {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_quota())