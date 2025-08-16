# LLM Integration Test Cases

## Overview
This document provides comprehensive test cases for the AI Companion LLM Integration System (Task 5). These tests validate the configurable LLM integration with Groq/OpenAI providers, streaming responses, conversation context management, and provider failover functionality.

## Prerequisites

### 1. Environment Setup
```bash
# 1. Ensure Docker services are running
docker-compose up -d

# 2. Run database migrations
alembic upgrade head

# 3. Seed character and user data
python scripts/seed_db.py

# 4. Configure LLM providers in .env file
echo "GROQ_API_KEY=your_groq_api_key_here" >> .env
echo "OPENAI_API_KEY=your_openai_api_key_here" >> .env
echo "LLM_PRIMARY_PROVIDER=groq" >> .env
echo "LLM_FALLBACK_PROVIDER=openai" >> .env

# 5. Start the application
python main.py
```

### 2. Required API Keys
You need at least one of the following API keys:
- **Groq API Key** (Primary): Get from https://console.groq.com/
- **OpenAI API Key** (Fallback): Get from https://platform.openai.com/

### 3. Test Users and Characters
Ensure you have:
- **Test User**: `testuser@example.com` with password `password123`
- **Characters**: Priya (ID: 1, friendly), Arjun (ID: 2, playful), Meera (ID: 3, caring)
- **Character Selection**: User has selected a character via `/api/v1/characters/{id}/select`

### 4. Authentication Token
```bash
# Get authentication token for testing
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "password": "password123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"
```

## Test Cases

### TC001: Provider Configuration Validation

**Objective**: Verify LLM provider configuration is properly loaded and validated.

**Test Method**: Direct service testing

**Example Test Script**:
```python
from app.config import settings
from app.services.llm_service import llm_service

# Test 1: Configuration loading
print("=== LLM Configuration ===")
llm_config = settings.llm
print(f"Primary Provider: {llm_config.primary_provider}")
print(f"Fallback Provider: {llm_config.fallback_provider}")
print(f"Available Providers: {list(llm_config.providers.keys())}")

# Test 2: Provider client initialization
print("\n=== Provider Service ===")
provider_info = llm_service.get_provider_info()
print(f"Current Provider: {provider_info['current_provider']}")
print(f"Available Providers: {provider_info['available_providers']}")
print(f"Current Model: {provider_info['current_model']}")
```

**Expected Results**:
- [ ] Configuration loads without errors
- [ ] At least one provider has valid API key
- [ ] Primary provider is 'groq', fallback is 'openai'
- [ ] Provider models are correctly mapped (mixtral-8x7b-32768 for Groq, gpt-3.5-turbo for OpenAI)

**Validation**:
- [ ] No configuration validation errors
- [ ] Provider info shows expected provider names
- [ ] Models match provider specifications

---

### TC002: Provider Connectivity Testing

**Objective**: Test connectivity to configured LLM providers.

#### TC002a: Provider Status Check

**API Endpoint**: `GET /api/v1/chat/provider`

**Example Request**:
```bash
curl -X GET "http://localhost:8001/api/v1/chat/provider" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "data": {
    "status": "healthy",
    "current_provider": "groq",
    "fallback_provider": "openai",
    "available_providers": ["groq", "openai"],
    "available_provider": "groq",
    "current_model": "mixtral-8x7b-32768"
  },
  "headers": {
    "X-LLM-Provider": "groq",
    "X-LLM-Model": "mixtral-8x7b-32768",
    "X-Service-Status": "healthy"
  }
}
```

**Validation**:
- [ ] Status is "healthy" when providers are available
- [ ] Current provider matches configuration
- [ ] Headers contain debugging information
- [ ] Available providers list is accurate

#### TC002b: Provider Connection Test (Admin)

**API Endpoint**: `GET /api/v1/chat/admin/llm/test?provider=groq`

**Example Request**:
```bash
# Test Groq connectivity
curl -X GET "http://localhost:8001/api/v1/chat/admin/llm/test?provider=groq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "provider": "groq",
  "connected": true,
  "timestamp": "2025-08-16T09:45:00.000Z"
}
```

**Validation**:
- [ ] Connection test returns true for configured providers
- [ ] Timestamp is current
- [ ] Test works for both groq and openai

---

### TC003: Chat Message Processing

**Objective**: Test the core chat functionality with streaming responses.

#### TC003a: Successful Chat Message (Streaming)

**API Endpoint**: `POST /api/v1/chat/send`

**Example Request**:
```bash
# Send a chat message with streaming (character auto-selected from Redis)
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! How are you today?",
    "stream": true
  }'
```

**Expected SSE Stream Response**:
```
data: {"type": "metadata", "conversation_id": 1, "character": {"id": 1, "name": "Priya", "personality_type": "friendly"}, "provider": "groq", "estimated_tokens": 150}

data: {"type": "content", "content": "Hello", "provider": "groq"}

data: {"type": "content", "content": "! I'm", "provider": "groq"}

data: {"type": "content", "content": " doing", "provider": "groq"}

data: {"type": "content", "content": " wonderfully", "provider": "groq"}

data: {"type": "content", "content": " today", "provider": "groq"}

data: {"type": "content", "content": ", thank", "provider": "groq"}

data: {"type": "content", "content": " you", "provider": "groq"}

data: {"type": "content", "content": " for", "provider": "groq"}

data: {"type": "content", "content": " asking", "provider": "groq"}

data: {"type": "content", "content": "!", "provider": "groq"}

data: {"type": "complete", "conversation_id": 1, "provider_used": "groq", "duration_seconds": 2.1, "message_length": 45, "timestamp": "2025-08-16T09:45:02.000Z"}

data: {"type": "end"}
```

**Validation**:
- [ ] Response starts with metadata chunk
- [ ] Content chunks stream progressively
- [ ] Response reflects character's personality (Priya - friendly)
- [ ] Complete chunk includes timing and metadata
- [ ] Stream ends with "end" marker
- [ ] Response headers include proper SSE headers

#### TC003b: Non-Streaming Chat Message

**Example Request**:
```bash
# Send a chat message without streaming (character auto-selected from Redis)
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about yourself",
    "stream": false
  }'
```

**Expected Response**:
```json
{
  "messages": [
    {
      "type": "metadata",
      "conversation_id": 1,
      "character": {
        "id": 2,
        "name": "Arjun",
        "personality_type": "playful"
      },
      "provider": "groq",
      "estimated_tokens": 180
    },
    {
      "type": "content",
      "content": "Hey there! I'm Arjun, your fun-loving AI companion! I love bringing humor and lightness to our conversations. I'm always ready with a joke or a playful comment to brighten your day. What would you like to chat about?",
      "provider": "groq"
    },
    {
      "type": "complete",
      "conversation_id": 1,
      "provider_used": "groq",
      "duration_seconds": 1.8,
      "message_length": 187,
      "timestamp": "2025-08-16T09:45:04.000Z"
    }
  ]
}
```

**Validation**:
- [ ] All response chunks returned in array
- [ ] Response reflects character personality (Arjun - playful)
- [ ] Complete timing and metadata included

---

### TC004: Multilingual Character Responses

**Objective**: Test character responses in different languages.

#### TC004a: Hindi Language Response

**Example Request**:
```bash
# First select caring character (Meera), then test Hindi response
curl -X POST "http://localhost:8001/api/v1/characters/3/select" \
  -H "Authorization: Bearer $TOKEN"

# Test Hindi response with selected character
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "मैं आज थोड़ा परेशान हूं",
    "stream": false
  }'
```

**Expected Behavior**:
- [ ] Response is in Hindi (Devanagari script)
- [ ] Response reflects caring personality (Meera)
- [ ] Appropriate cultural context and empathy
- [ ] Response addresses the user's emotional state

#### TC004b: Tamil Language Response

**Example Request**:
```bash
# First select playful character (Arjun), then test Tamil response
curl -X POST "http://localhost:8001/api/v1/characters/2/select" \
  -H "Authorization: Bearer $TOKEN"

# Test Tamil response with selected character
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "எனக்கு இன்று மிகவும் மகிழ்ச்சியாக இருக்கிறது",
    "stream": false
  }'
```

**Expected Behavior**:
- [ ] Response is in Tamil (Tamil script)
- [ ] Response matches playful personality
- [ ] Appropriate cultural expressions
- [ ] Engages with user's positive mood

**Validation**:
- [ ] Language detection works correctly
- [ ] Character prompts use appropriate language
- [ ] Cultural context is maintained
- [ ] Personality traits are evident in language choice

---

### TC005: Provider Failover Testing

**Objective**: Test automatic failover between LLM providers.

#### TC005a: Manual Provider Switching

**API Endpoint**: `POST /api/v1/chat/admin/llm/switch`

**Example Request**:
```bash
# Switch to OpenAI provider
curl -X POST "http://localhost:8001/api/v1/chat/admin/llm/switch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai"}'
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Switched to provider: openai",
  "provider_info": {
    "current_provider": "openai",
    "fallback_provider": "openai",
    "available_providers": ["groq", "openai"],
    "current_model": "gpt-3.5-turbo"
  }
}
```

**Validation**:
- [ ] Provider switches successfully
- [ ] Model changes to OpenAI model (gpt-3.5-turbo)
- [ ] Subsequent chat requests use OpenAI

#### TC005b: Automatic Failover Simulation

**Test Method**: Simulate provider failure

**Steps**:
1. Temporarily disable Groq by using invalid API key
2. Send chat message
3. Observe automatic failover to OpenAI
4. Restore Groq API key

**Expected Behavior**:
- [ ] System detects Groq failure
- [ ] Automatically switches to OpenAI
- [ ] Chat continues without user interruption
- [ ] Error is logged but not exposed to user
- [ ] Response includes correct provider in metadata

**Validation Commands**:
```bash
# Step 1: Backup and invalidate Groq key
cp .env .env.backup
sed -i 's/GROQ_API_KEY=.*/GROQ_API_KEY=invalid_key/' .env

# Step 2: Restart app and test
python main.py &
APP_PID=$!

# Step 3: Send message (should use OpenAI)
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test failover", "stream": false}'

# Step 4: Restore configuration
kill $APP_PID
mv .env.backup .env
```

---

### TC006: Conversation Context Management

**Objective**: Test conversation persistence and context handling.

#### TC006a: Conversation History

**API Endpoint**: `GET /api/v1/chat/history?limit=10`

**Example Request**:
```bash
# Get history for selected character (auto-determined from Redis)
curl -X GET "http://localhost:8001/api/v1/chat/history?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "conversation_id": 1,
  "messages": [
    {
      "role": "user",
      "content": "Hello! How are you today?"
    },
    {
      "role": "assistant", 
      "content": "Hello! I'm doing wonderfully today, thank you for asking!"
    },
    {
      "role": "user",
      "content": "What's your name?"
    },
    {
      "role": "assistant",
      "content": "I'm Priya, your friendly AI companion! How can I help you today?"
    }
  ],
  "total": 4,
  "character_id": 1,
  "user_id": 1,
  "started_at": "2025-08-16T09:40:00.000Z",
  "last_message_at": "2025-08-16T09:45:00.000Z"
}
```

**Validation**:
- [ ] Messages are in chronological order (oldest first)
- [ ] Both user and assistant messages included
- [ ] Conversation metadata is accurate
- [ ] Pagination works with limit/offset

#### TC006b: Context Continuity

**Test Steps**:
1. Send initial message: "My name is John"
2. Send follow-up: "What did I just tell you?"
3. Verify AI remembers the name

**Example Test**:
```bash
# Message 1
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is John and I love reading books", "stream": false}'

# Message 2 (should reference previous context)
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you remember about me?", "stream": false}'
```

**Expected Behavior**:
- [ ] AI references the user's name (John)
- [ ] AI mentions the user's interest in books
- [ ] Context from previous messages is maintained
- [ ] Conversation flows naturally

---

### TC007: Character Switching During Conversation

**Objective**: Test switching characters mid-conversation.

**API Endpoint**: `POST /api/v1/chat/switch-character`

**Example Request**:
```bash
# Switch from Priya (friendly) to Arjun (playful)
curl -X POST "http://localhost:8001/api/v1/chat/switch-character" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 2}'
```

**Expected Response**:
```json
{
  "success": true,
  "character": {
    "id": 2,
    "name": "Arjun",
    "personality_type": "playful",
    "description": "Fun-loving and witty AI companion who brings humor and lightness to conversations."
  }
}
```

**Test Conversation**:
```bash
# Send message after switching
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke", "stream": false}'
```

**Validation**:
- [ ] Character switch is successful
- [ ] Cached character selection is updated
- [ ] Subsequent messages use new character's personality
- [ ] Conversation context is maintained across switch

---

### TC008: Error Handling and Edge Cases

**Objective**: Test system behavior under various error conditions.

#### TC008a: No Character Selected

**Example Request**:
```bash
# Clear character selection first
curl -X DELETE "http://localhost:8001/api/v1/characters/current" \
  -H "Authorization: Bearer $TOKEN"

# Try to send message without character
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "stream": false}'
```

**Expected Response**:
```json
{
  "type": "error",
  "error": "No character selected. Please select a character first.",
  "code": "CHARACTER_NOT_SELECTED"
}
```

**Validation**:
- [ ] Error is returned immediately
- [ ] Clear error message explaining issue
- [ ] Appropriate error code provided

#### TC008b: Invalid Character ID

**Example Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "stream": false}'
```

**Expected Response**:
```json
{
  "type": "error",
  "error": "No character selected. Please select a character first.",
  "code": "CHARACTER_NOT_SELECTED"
}
```

#### TC008c: Empty Message

**Example Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "", "stream": false}'
```

**Expected Response**:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character"
    }
  ]
}
```

**Validation**:
- [ ] HTTP 422 status code
- [ ] Pydantic validation error
- [ ] Clear field-level error message

#### TC008d: All Providers Down

**Test Method**: Disable all providers temporarily

**Steps**:
1. Set invalid API keys for both providers
2. Restart application
3. Try to send message

**Expected Behavior**:
- [ ] Error response indicating service unavailable
- [ ] HTTP 503 status code
- [ ] Graceful error message (no crash)

---

### TC009: Performance and Load Testing

**Objective**: Test system performance under load.

#### TC009a: Response Time Testing

**Test Script**: `test_response_times.sh`
```bash
#!/bin/bash

echo "Testing chat response times..."

# Get auth token
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "password": "password123"}')
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

# Test 10 messages and measure response times
for i in {1..10}; do
  echo "Test $i:"
  start_time=$(date +%s.%N)
  
  curl -s -X POST "http://localhost:8001/api/v1/chat/send" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Test message $i\", \"stream\": false}" \
    > /dev/null
  
  end_time=$(date +%s.%N)
  duration=$(echo "$end_time - $start_time" | bc)
  echo "Response time: ${duration}s"
  
  sleep 1
done
```

**Expected Results**:
- [ ] Average response time < 3 seconds
- [ ] No timeouts or connection errors
- [ ] Consistent performance across tests

#### TC009b: Concurrent User Testing

**Test Method**: Simulate multiple users chatting simultaneously

**Expected Behavior**:
- [ ] System handles multiple concurrent requests
- [ ] No mixing of conversations between users
- [ ] Response times remain reasonable
- [ ] No memory leaks or resource exhaustion

**Validation**:
- [ ] Each user gets their own conversation
- [ ] Character selections are user-specific
- [ ] No cross-contamination of messages

---

### TC010: Redis Caching Verification

**Objective**: Verify conversation context caching works properly.

#### TC010a: Cache Population

**Test Steps**:
1. Send a few messages to create conversation context
2. Check Redis for cached context

**Redis Commands**:
```bash
# Connect to Redis
redis-cli

# Check conversation context cache (replace {conversation_id})
GET conv:{conversation_id}:ctx:5

# Check character selection cache (replace {user_id})  
GET user:{user_id}:character

# List all conversation keys
KEYS conv:*:ctx:*

# Check TTL
TTL conv:{conversation_id}:ctx:5
```

**Expected Results**:
- [ ] Conversation context is cached with 1-hour TTL
- [ ] Character selection is cached with 24-hour TTL
- [ ] Cache keys follow expected naming pattern
- [ ] Cached data matches conversation content

#### TC010b: Cache Invalidation

**Test Steps**:
1. Send message (cache gets populated)
2. Send another message (cache should be cleared and repopulated)
3. Verify cache contains latest context

**Validation**:
- [ ] Cache is updated after new messages
- [ ] Old context is replaced with current context
- [ ] Cache TTL is reset after updates

---

### TC011: Token Limit and Context Management

**Objective**: Test handling of long conversations and token limits.

#### TC011a: Long Conversation Test

**Test Script**: Send multiple long messages to approach token limits

```bash
#!/bin/bash

# Send progressively longer messages
for i in {1..5}; do
  long_message=$(printf "This is a very long message that repeats itself multiple times. %.0s" {1..100})
  
  curl -X POST "http://localhost:8001/api/v1/chat/send" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$long_message\", \"stream\": false}"
    
  echo "Sent message $i"
  sleep 2
done
```

**Expected Behavior**:
- [ ] System handles long messages gracefully
- [ ] Context is truncated when approaching limits
- [ ] Warning logged about context reduction
- [ ] Conversation continues normally

#### TC011b: Token Estimation Accuracy

**Test Method**: Verify token estimation is reasonable

**Expected Results**:
- [ ] Token estimates are within 20% of actual usage
- [ ] Context reduction occurs before hitting limits
- [ ] System maintains last 2-3 message pairs minimum

---

## Automated Testing Script

### Complete LLM Integration Test

Create `test_llm_integration.py`:

```python
#!/usr/bin/env python3
"""
Comprehensive LLM Integration Test Suite
"""

import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8001"

class LLMIntegrationTester:
    def __init__(self):
        self.token = None
        self.conversation_id = None
        self.passed = 0
        self.failed = 0
    
    def authenticate(self) -> bool:
        """Get authentication token"""
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
                "email": "testuser@example.com",
                "password": "password123"
            })
            
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_provider_status(self):
        """Test provider status endpoint"""
        print("\n🧪 Testing Provider Status...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/chat/provider",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                if data["status"] in ["healthy", "degraded"]:
                    print(f"✅ Provider status: {data['status']}")
                    print(f"   Current provider: {data['current_provider']}")
                    print(f"   Available providers: {data['available_providers']}")
                    self.passed += 1
                else:
                    print(f"❌ Invalid provider status: {data['status']}")
                    self.failed += 1
            else:
                print(f"❌ Provider status failed: {response.status_code}")
                self.failed += 1
                
        except Exception as e:
            print(f"❌ Provider status error: {e}")
            self.failed += 1
    
    def test_chat_message(self, message: str) -> bool:
        """Test sending a chat message"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/send",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "message": message,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                messages = response.json()["messages"]
                
                # Find content and complete messages
                content_msg = next((m for m in messages if m["type"] == "content"), None)
                complete_msg = next((m for m in messages if m["type"] == "complete"), None)
                
                if content_msg and complete_msg:
                    self.conversation_id = complete_msg["conversation_id"]
                    print(f"✅ Chat response: {content_msg['content'][:50]}...")
                    print(f"   Provider: {content_msg['provider']}")
                    print(f"   Duration: {complete_msg['duration_seconds']:.2f}s")
                    return True
                else:
                    print("❌ Invalid response format")
                    return False
            else:
                print(f"❌ Chat failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return False
    
    def test_conversation_history(self):
        """Test conversation history retrieval"""
        print("\n🧪 Testing Conversation History...")
        
        if not self.conversation_id:
            print("❌ No conversation ID available")
            self.failed += 1
            return
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/chat/history",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"limit": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "messages" in data and len(data["messages"]) > 0:
                    print(f"✅ History retrieved: {len(data['messages'])} messages")
                    print(f"   Conversation ID: {data['conversation_id']}")
                    self.passed += 1
                else:
                    print("❌ No messages in history")
                    self.failed += 1
            else:
                print(f"❌ History failed: {response.status_code}")
                self.failed += 1
                
        except Exception as e:
            print(f"❌ History error: {e}")
            self.failed += 1
    
    def test_character_switching(self):
        """Test character switching"""
        print("\n🧪 Testing Character Switching...")
        
        try:
            # Switch to character 2 (Arjun - playful)
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/switch-character",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"character_id": 2}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["success"] and data["character"]["name"] == "Arjun":
                    print("✅ Character switched to Arjun")
                    
                    # Test message with new character
                    if self.test_chat_message("Tell me a joke"):
                        print("✅ Message sent with new character")
                        self.passed += 2
                    else:
                        print("❌ Failed to send message with new character")
                        self.failed += 1
                else:
                    print("❌ Character switch failed")
                    self.failed += 1
            else:
                print(f"❌ Character switch failed: {response.status_code}")
                self.failed += 1
                
        except Exception as e:
            print(f"❌ Character switching error: {e}")
            self.failed += 1
    
    def test_error_handling(self):
        """Test error handling"""
        print("\n🧪 Testing Error Handling...")
        
        # Test empty message
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/send",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"message": "", "stream": False}
            )
            
            if response.status_code == 422:
                print("✅ Empty message validation works")
                self.passed += 1
            else:
                print(f"❌ Empty message should return 422, got {response.status_code}")
                self.failed += 1
                
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            self.failed += 1
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting LLM Integration Test Suite")
        print("=" * 50)
        
        if not self.authenticate():
            print("❌ Cannot proceed without authentication")
            sys.exit(1)
        
        # Core functionality tests
        self.test_provider_status()
        
        print("\n🧪 Testing Basic Chat...")
        if self.test_chat_message("Hello! How are you today?"):
            print("✅ Basic chat works")
            self.passed += 1
        else:
            print("❌ Basic chat failed")
            self.failed += 1
        
        # Context and history tests
        self.test_conversation_history()
        
        # Character switching
        self.test_character_switching()
        
        # Error handling
        self.test_error_handling()
        
        # Multi-language test  
        print("\n🧪 Testing Multi-language Support...")
        if self.test_chat_message("नमस्ते! आप कैसे हैं?"):  # Hindi
            print("✅ Multi-language support works")
            self.passed += 1
        else:
            print("❌ Multi-language support failed")
            self.failed += 1
        
        # Results
        print("\n" + "=" * 50)
        print(f"🏁 Test Results: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("🎉 All tests passed! LLM Integration is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the issues above.")
            return False

if __name__ == "__main__":
    tester = LLMIntegrationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
```

### Usage

```bash
# Make executable and run
chmod +x test_llm_integration.py
python test_llm_integration.py
```

## Manual Testing Checklist

After running automated tests, verify these aspects manually:

### Core Functionality
- [ ] Chat messages generate appropriate responses
- [ ] Streaming works in browser/frontend
- [ ] Character personalities are evident in responses
- [ ] Multi-language responses work correctly
- [ ] Conversation context is maintained

### Provider Management  
- [ ] Provider status shows correct information
- [ ] Manual provider switching works
- [ ] Automatic failover activates when needed
- [ ] Performance is acceptable with both providers

### Error Handling
- [ ] Clear error messages for user issues
- [ ] Graceful degradation when services unavailable
- [ ] No system crashes under error conditions
- [ ] Appropriate HTTP status codes

### Performance
- [ ] Response times are reasonable (< 3s)
- [ ] System handles concurrent users
- [ ] Memory usage remains stable
- [ ] Long conversations don't cause issues

### Integration
- [ ] Works with existing authentication
- [ ] Character selection integrates properly
- [ ] Database operations are correct
- [ ] Redis caching functions properly

---

## Troubleshooting

### Common Issues

**Issue**: "No LLM providers are configured"
- **Solution**: Check .env file has valid API keys, restart application

**Issue**: SSE streaming not working
- **Solution**: Check CORS headers, verify frontend SSE implementation

**Issue**: Provider test fails
- **Solution**: Verify API keys are valid, check network connectivity

**Issue**: Character responses not matching personality
- **Solution**: Check character selection, verify prompt templates

**Issue**: Context not maintained across messages
- **Solution**: Check Redis connectivity, verify conversation ID continuity

### Debug Commands

```bash
# Check provider configuration
curl -X GET "http://localhost:8001/api/v1/chat/provider" \
  -H "Authorization: Bearer $TOKEN"

# Test provider connectivity
curl -X GET "http://localhost:8001/api/v1/chat/admin/llm/test" \
  -H "Authorization: Bearer $TOKEN"

# Check conversation in Redis
redis-cli KEYS "conv:*"

# View application logs
docker-compose logs app

# Check environment variables
grep -E "(GROQ|OPENAI|LLM)" .env
```

---

This comprehensive test suite ensures your LLM integration system is working correctly across all components including provider management, streaming responses, conversation context, character personalities, and error handling. Run these tests after any changes to verify functionality remains intact.