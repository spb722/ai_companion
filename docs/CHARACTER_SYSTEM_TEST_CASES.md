# Character System Test Cases

## Overview
This document provides comprehensive test cases for the AI Companion Character System. These tests are designed for the implementation team to validate that all character management features are working correctly.

## Prerequisites

### 1. Environment Setup
```bash
# 1. Ensure Docker services are running
docker-compose up -d

# 2. Run database migrations
alembic upgrade head

# 3. Seed character data
python scripts/seed_db.py

# 4. Start the application
python main.py
```

### 2. Test Data
After seeding, you should have these characters:
- **Priya** (ID: 1, Friendly, Free tier)
- **Arjun** (ID: 2, Playful, Free tier)  
- **Meera** (ID: 3, Caring, Premium tier)

### 3. Authentication
Create test users through the auth endpoints:
```bash
# Free user
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testfree@example.com",
    "password": "password123",
    "username": "testfree"
  }'

# Premium user (you'll need to update subscription_tier in database)
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testpro@example.com", 
    "password": "password123",
    "username": "testpro"
  }'
```

## Test Cases

### TC001: Database and Seeding

**Objective**: Verify character data is properly seeded in the database.

**Steps**:
1. Run the seed script: `python scripts/seed_db.py`
2. Check the output for successful seeding messages
3. Run the automated test: `python test_character_system.py`

**Expected Results**:
```
🌱 Starting database seeding...
📊 Current character count: 0
🎭 Seeding characters...
Added character: Priya (friendly)
Added character: Arjun (playful)
Added character: Meera (caring)
📊 Final character count: 3
✅ Database seeding completed successfully!
```

**Validation**:
- [ ] Seed script runs without errors
- [ ] 3 characters are created (Priya, Arjun, Meera)
- [ ] Re-running script shows "Character already exists" messages
- [ ] Test script passes all checks

---

### TC002: Character Listing API

**Objective**: Test the character listing endpoint for different user tiers.

#### TC002a: Free User Character Access

**API Endpoint**: `GET /api/v1/characters`

**Test Steps**:
1. Login as free user and get access token
2. Make API request with Bearer token

**Example Request**:
```bash
# Login first
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "testfree@example.com", "password": "password123"}')

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

# Get characters
curl -X GET "http://localhost:8001/api/v1/characters" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "characters": [
    {
      "id": 1,
      "name": "Priya",
      "personality_type": "friendly",
      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Priya&background=c0aede",
      "is_premium": false,
      "can_access": true
    },
    {
      "id": 2,
      "name": "Arjun", 
      "personality_type": "playful",
      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Arjun&background=b6e3f4",
      "is_premium": false,
      "can_access": true
    }
  ],
  "total_count": 2,
  "user_tier": "free"
}
```

**Validation**:
- [ ] Response contains only 2 characters (free tier only)
- [ ] Both characters have `can_access: true`
- [ ] `user_tier` shows "free"
- [ ] Premium character (Meera) is not included

#### TC002b: Premium User Character Access

**Test Steps**: Same as TC002a but use premium user credentials

**Expected Response**:
```json
{
  "success": true,
  "characters": [
    {
      "id": 1,
      "name": "Priya",
      "personality_type": "friendly",
      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Priya&background=c0aede",
      "is_premium": false,
      "can_access": true
    },
    {
      "id": 2,
      "name": "Arjun",
      "personality_type": "playful", 
      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Arjun&background=b6e3f4",
      "is_premium": false,
      "can_access": true
    },
    {
      "id": 3,
      "name": "Meera",
      "personality_type": "caring",
      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Meera&background=ffd93d", 
      "is_premium": true,
      "can_access": true
    }
  ],
  "total_count": 3,
  "user_tier": "pro"
}
```

**Validation**:
- [ ] Response contains all 3 characters
- [ ] All characters have `can_access: true`
- [ ] `user_tier` shows "pro"
- [ ] Premium character (Meera) is included

---

### TC003: Character Selection

**Objective**: Test character selection functionality and Redis caching.

#### TC003a: Successful Character Selection (Free User)

**API Endpoint**: `POST /api/v1/characters/{id}/select`

**Example Request**:
```bash
# Select Priya (ID: 1) - free character
curl -X POST "http://localhost:8001/api/v1/characters/1/select" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Successfully selected Priya",
  "character": {
    "id": 1,
    "name": "Priya",
    "personality_type": "friendly"
  }
}
```

**Validation**:
- [ ] Response indicates success
- [ ] Character information is returned
- [ ] Selection is cached in Redis (verify with TC004)

#### TC003b: Premium Character Access Denied (Free User)

**Example Request**:
```bash
# Try to select Meera (ID: 3) - premium character with free user
curl -X POST "http://localhost:8001/api/v1/characters/3/select" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": false,
  "error": {
    "code": "PREMIUM_REQUIRED",
    "message": "This character requires a premium subscription"
  }
}
```

**Validation**:
- [ ] HTTP status code: 403 Forbidden
- [ ] Error code is "PREMIUM_REQUIRED"
- [ ] Clear error message explaining premium requirement

#### TC003c: Invalid Character Selection

**Example Request**:
```bash
# Try to select non-existent character (ID: 999)
curl -X POST "http://localhost:8001/api/v1/characters/999/select" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": false,
  "error": {
    "code": "CHARACTER_NOT_FOUND", 
    "message": "Character not found"
  }
}
```

**Validation**:
- [ ] HTTP status code: 404 Not Found
- [ ] Error code is "CHARACTER_NOT_FOUND"

---

### TC004: Current Character Retrieval

**Objective**: Test getting user's currently selected character.

#### TC004a: Get Current Character (After Selection)

**API Endpoint**: `GET /api/v1/characters/current`

**Pre-condition**: Complete TC003a (select a character first)

**Example Request**:
```bash
curl -X GET "http://localhost:8001/api/v1/characters/current" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "character": {
    "id": 1,
    "name": "Priya",
    "personality_type": "friendly",
    "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Priya&background=c0aede",
    "is_premium": false,
    "can_access": true
  },
  "message": "Current character: Priya"
}
```

**Validation**:
- [ ] Returns the previously selected character
- [ ] Character details are complete and accurate

#### TC004b: No Character Selected

**Pre-condition**: Clear character selection (use TC005 or fresh user)

**Expected Response**:
```json
{
  "success": true,
  "character": null,
  "message": "No character selected"
}
```

**Validation**:
- [ ] `character` field is null
- [ ] Message indicates no selection

---

### TC005: Character Selection Clearing

**Objective**: Test clearing character selection.

**API Endpoint**: `DELETE /api/v1/characters/current`

**Pre-condition**: Have a character selected (complete TC003a)

**Example Request**:
```bash
curl -X DELETE "http://localhost:8001/api/v1/characters/current" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Character selection cleared successfully"
}
```

**Validation**:
- [ ] HTTP status code: 200 OK
- [ ] Success message returned
- [ ] Subsequent call to `/current` returns null character (TC004b)

---

### TC006: Character Details

**Objective**: Test retrieving specific character details.

**API Endpoint**: `GET /api/v1/characters/{id}`

**Example Request**:
```bash
# Get details for Priya (ID: 1)
curl -X GET "http://localhost:8001/api/v1/characters/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "id": 1,
  "name": "Priya",
  "personality_type": "friendly",
  "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Priya&background=c0aede",
  "is_premium": false,
  "can_access": true
}
```

**Validation**:
- [ ] Character details are complete and accurate
- [ ] `can_access` reflects user's subscription tier

---

### TC007: Redis Caching Verification

**Objective**: Verify character selections are properly cached in Redis.

**Tools Needed**: Redis CLI or Redis GUI

**Steps**:
1. Select a character using TC003a
2. Check Redis for the cache key

**Redis Commands**:
```bash
# Connect to Redis
redis-cli

# Check if user's character selection exists (replace {user_id} with actual user ID)
GET user:{user_id}:character

# Check TTL (should be ~24 hours = 86400 seconds)
TTL user:{user_id}:character

# List all user character keys
KEYS user:*:character
```

**Expected Results**:
- [ ] Key `user:{user_id}:character` exists
- [ ] Value matches selected character ID
- [ ] TTL is approximately 86400 seconds (24 hours)

---

### TC008: Prompt System Testing

**Objective**: Test multilingual prompt generation.

**Test Method**: Use the test script or direct function calls

**Example Test Script**:
```python
from app.prompts.character_prompts import (
    get_character_prompt_by_character_id,
    validate_prompt_coverage,
    get_available_languages,
    get_available_personalities
)

# Test 1: Get English prompt for Priya (friendly)
prompt_en = get_character_prompt_by_character_id(1, "friendly", "en")
print("English Prompt Length:", len(prompt_en))
print("English Prompt Preview:", prompt_en[:200] + "...")

# Test 2: Get Hindi prompt for Arjun (playful)  
prompt_hi = get_character_prompt_by_character_id(2, "playful", "hi")
print("Hindi Prompt Length:", len(prompt_hi))
print("Hindi Prompt Preview:", prompt_hi[:200] + "...")

# Test 3: Get Tamil prompt for Meera (caring)
prompt_ta = get_character_prompt_by_character_id(3, "caring", "ta")
print("Tamil Prompt Length:", len(prompt_ta))
print("Tamil Prompt Preview:", prompt_ta[:200] + "...")

# Test 4: Test fallback for invalid language
prompt_fallback = get_character_prompt_by_character_id(1, "friendly", "invalid")
print("Fallback works:", prompt_fallback == prompt_en)

# Test 5: Validate coverage
coverage = validate_prompt_coverage()
print("Coverage:", coverage)
```

**Expected Results**:
- [ ] All prompts return non-empty strings
- [ ] Prompts are substantial (>100 characters)
- [ ] Hindi prompts contain Devanagari script
- [ ] Tamil prompts contain Tamil script
- [ ] Invalid language falls back to English
- [ ] Coverage is 100% (9/9 combinations)

---

### TC009: Authentication Integration

**Objective**: Test character system integration with authentication.

#### TC009a: Unauthenticated Access

**Example Request**:
```bash
# Try to access characters without token
curl -X GET "http://localhost:8001/api/v1/characters" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": false,
  "error": {
    "code": "MISSING_TOKEN",
    "message": "Authorization token is required"
  }
}
```

**Validation**:
- [ ] HTTP status code: 401 Unauthorized
- [ ] Error code is "MISSING_TOKEN"

#### TC009b: Invalid Token

**Example Request**:
```bash
# Try with invalid token
curl -X GET "http://localhost:8001/api/v1/characters" \
  -H "Authorization: Bearer invalid_token_here" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": false,
  "error": {
    "code": "TOKEN_INVALID",
    "message": "Invalid or expired token"
  }
}
```

**Validation**:
- [ ] HTTP status code: 401 Unauthorized
- [ ] Error code is "TOKEN_INVALID"

---

### TC010: Error Handling

**Objective**: Test system behavior under error conditions.

#### TC010a: Database Connection Error

**Steps**:
1. Stop the MySQL container: `docker-compose stop mysql`
2. Try to access any character endpoint
3. Restart MySQL: `docker-compose start mysql`

**Expected Behavior**:
- [ ] Graceful error responses (not crashes)
- [ ] HTTP 500 status codes
- [ ] Error messages indicate internal server error

#### TC010b: Redis Connection Error

**Steps**:
1. Stop the Redis container: `docker-compose stop redis`
2. Try to select a character
3. Restart Redis: `docker-compose start redis`

**Expected Behavior**:
- [ ] Character selection fails gracefully
- [ ] Error message indicates cache error
- [ ] System continues to function (degraded mode)

---

## Automated Testing

### Running the Complete Test Suite

**Command**:
```bash
python test_character_system.py
```

**Expected Output**:
```
🧪 Testing Character System
==================================================

1️⃣ Testing database seeding...
   Initial character count: 3
   Final character count: 3
   ✅ Database seeding successful!

2️⃣ Testing character service...
   Free user characters: 2
   Premium user characters: 3
   ✅ Character service working!

3️⃣ Testing Redis caching...
   ✅ Redis caching working!

4️⃣ Testing prompt system...
   Prompt coverage: 100.0%
   Total combinations: 9
   Covered combinations: 9
   ✅ Prompt system working!

5️⃣ Testing available options...
   Available languages: ['en', 'hi', 'ta']
   Available personalities: ['friendly', 'playful', 'caring']
   ✅ Available options correct!

🎉 All tests passed! Character system is working correctly.
```

### Manual API Testing Script

Create a file `test_api_manually.sh`:

```bash
#!/bin/bash

echo "🧪 Manual API Testing Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8001"

# Function to test API endpoint
test_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    
    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo "Request: $method $endpoint"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status_code)"
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status_code)"
    fi
    
    echo "Response: $body" | jq . 2>/dev/null || echo "Response: $body"
}

# Setup: Login and get token
echo "Setting up authentication..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "testfree@example.com", "password": "password123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get authentication token${NC}"
    echo "Please ensure test user exists and credentials are correct"
    exit 1
fi

echo -e "${GREEN}✅ Authentication successful${NC}"

# Run tests
test_api "GET" "/api/v1/characters" "" "200" "List characters"
test_api "POST" "/api/v1/characters/1/select" "" "200" "Select character 1"
test_api "GET" "/api/v1/characters/current" "" "200" "Get current character"
test_api "GET" "/api/v1/characters/1" "" "200" "Get character details"
test_api "POST" "/api/v1/characters/3/select" "" "403" "Try premium character (should fail)"
test_api "POST" "/api/v1/characters/999/select" "" "404" "Try invalid character"
test_api "DELETE" "/api/v1/characters/current" "" "200" "Clear character selection"

echo -e "\n${GREEN}🎉 Manual testing complete!${NC}"
```

**Usage**:
```bash
chmod +x test_api_manually.sh
./test_api_manually.sh
```

---

## Test Results Checklist

After running all tests, verify:

### Core Functionality
- [ ] Database seeding works correctly
- [ ] Character listing respects user tiers
- [ ] Character selection works for valid cases
- [ ] Premium access control is enforced
- [ ] Redis caching functions properly
- [ ] Character clearing works

### API Endpoints
- [ ] All endpoints return proper HTTP status codes
- [ ] Error responses follow consistent format
- [ ] Authentication is properly enforced
- [ ] Response schemas match documentation

### Prompt System
- [ ] All 9 language/personality combinations work
- [ ] Prompts contain appropriate cultural context
- [ ] Fallback to English works for invalid languages
- [ ] Token counts are reasonable (<200 tokens)

### Error Handling
- [ ] Graceful degradation when services are unavailable
- [ ] Clear error messages for user-facing issues
- [ ] No system crashes under error conditions

### Performance
- [ ] Character listing is fast (<500ms)
- [ ] Character selection is immediate (<100ms)
- [ ] Redis caching reduces database calls
- [ ] No memory leaks in extended testing

---

## Troubleshooting

### Common Issues

**Issue**: "Character already exists" during seeding
- **Solution**: This is normal for re-runs. Check that count increases appropriately.

**Issue**: Redis connection refused
- **Solution**: Ensure Redis container is running: `docker-compose up redis -d`

**Issue**: 401 Unauthorized errors
- **Solution**: Check token expiration, re-login if necessary

**Issue**: Premium character not accessible
- **Solution**: Verify user's subscription_tier is set to "pro" in database

**Issue**: Prompts return null
- **Solution**: Check personality_type matches enum values exactly

### Debug Commands

```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs app

# Check Redis keys
redis-cli KEYS "*"

# Check database characters
mysql -u root -p ai_companion -e "SELECT * FROM characters;"
```

---

This comprehensive test suite ensures your character system is working correctly across all components. Run these tests after any changes to verify functionality remains intact.