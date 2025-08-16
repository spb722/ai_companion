#!/bin/bash

echo "🧪 Manual API Testing Script for Character System"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}Request: $method $endpoint${NC}"
    
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
    
    # Pretty print JSON if possible
    echo "$body" | jq . 2>/dev/null || echo "Response: $body"
}

# Function to create test user if not exists
create_test_user() {
    echo -e "\n${BLUE}Creating test user...${NC}"
    register_response=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"email": "testfree@example.com", "password": "password123", "username": "testfree"}')
    
    echo "Registration response: $register_response"
}

# Check if server is running
echo -e "${BLUE}Checking if server is running...${NC}"
health_check=$(curl -s "$BASE_URL/" || echo "FAILED")
if [[ "$health_check" == *"AI Companion API"* ]]; then
    echo -e "${GREEN}✅ Server is running${NC}"
else
    echo -e "${RED}❌ Server is not running. Please start it with: python main.py${NC}"
    exit 1
fi

# Create test user (ignore if already exists)
create_test_user

# Setup: Login and get token
echo -e "\n${BLUE}Setting up authentication...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "testfree@example.com", "password": "password123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token' 2>/dev/null)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Failed to get authentication token${NC}"
    echo "Login response: $LOGIN_RESPONSE"
    echo -e "${YELLOW}Please ensure:${NC}"
    echo "1. Database is running and migrated"
    echo "2. Test user exists or registration worked"
    echo "3. Credentials are correct"
    exit 1
fi

echo -e "${GREEN}✅ Authentication successful${NC}"
echo "Token: ${TOKEN:0:20}..."

# Run character system tests
echo -e "\n${BLUE}=== CHARACTER SYSTEM TESTS ===${NC}"

test_api "GET" "/api/v1/characters" "" "200" "TC002a: List characters (free user)"

test_api "POST" "/api/v1/characters/1/select" "" "200" "TC003a: Select character 1 (Priya - free)"

test_api "GET" "/api/v1/characters/current" "" "200" "TC004a: Get current character (should be Priya)"

test_api "GET" "/api/v1/characters/1" "" "200" "TC006: Get character 1 details"

test_api "POST" "/api/v1/characters/3/select" "" "403" "TC003b: Try premium character (should fail)"

test_api "POST" "/api/v1/characters/999/select" "" "404" "TC003c: Try invalid character (should fail)"

test_api "DELETE" "/api/v1/characters/current" "" "200" "TC005: Clear character selection"

test_api "GET" "/api/v1/characters/current" "" "200" "TC004b: Get current character (should be null)"

test_api "POST" "/api/v1/characters/2/select" "" "200" "TC003a: Select character 2 (Arjun - free)"

# Test unauthenticated access
echo -e "\n${BLUE}=== AUTHENTICATION TESTS ===${NC}"

echo -e "\n${YELLOW}Testing: TC009a: Unauthenticated access${NC}"
echo -e "${BLUE}Request: GET /api/v1/characters (no token)${NC}"
unauth_response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/characters" \
    -H "Content-Type: application/json")
unauth_status=$(echo "$unauth_response" | tail -n1)
unauth_body=$(echo "$unauth_response" | head -n -1)

if [ "$unauth_status" = "401" ]; then
    echo -e "${GREEN}✅ PASS${NC} (Status: $unauth_status)"
else
    echo -e "${RED}❌ FAIL${NC} (Expected: 401, Got: $unauth_status)"
fi
echo "$unauth_body" | jq . 2>/dev/null || echo "Response: $unauth_body"

echo -e "\n${YELLOW}Testing: TC009b: Invalid token${NC}"
echo -e "${BLUE}Request: GET /api/v1/characters (invalid token)${NC}"
invalid_response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/characters" \
    -H "Authorization: Bearer invalid_token_here" \
    -H "Content-Type: application/json")
invalid_status=$(echo "$invalid_response" | tail -n1)
invalid_body=$(echo "$invalid_response" | head -n -1)

if [ "$invalid_status" = "401" ]; then
    echo -e "${GREEN}✅ PASS${NC} (Status: $invalid_status)"
else
    echo -e "${RED}❌ FAIL${NC} (Expected: 401, Got: $invalid_status)"
fi
echo "$invalid_body" | jq . 2>/dev/null || echo "Response: $invalid_body"

# Final summary
echo -e "\n${BLUE}=== TEST SUMMARY ===${NC}"
echo -e "${GREEN}🎉 Manual API testing complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Review any failed tests above"
echo "2. Run the automated test suite: python test_character_system.py"
echo "3. Check Redis caching manually with: redis-cli"
echo "4. Test premium user functionality by updating subscription_tier in database"
echo "5. Review the full test documentation in docs/CHARACTER_SYSTEM_TEST_CASES.md"

echo -e "\n${BLUE}=== DEBUGGING COMMANDS ===${NC}"
echo "Check containers: docker-compose ps"
echo "View logs: docker-compose logs app"
echo "Check Redis: redis-cli KEYS '*'"
echo "Check DB: docker-compose exec mysql mysql -u root -p ai_companion -e 'SELECT * FROM characters;'"