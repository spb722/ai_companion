#!/bin/bash

# AI Companion Chat API Test Suite
# This script tests all the chat API endpoints comprehensively

set -e  # Exit on any error

# Configuration
BASE_URL="http://localhost:8000"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

test_endpoint() {
    local name="$1"
    local expected_code="$2"
    shift 2
    local curl_args=("$@")
    
    log_info "Testing: $name"
    
    response=$(curl -s -w "\n%{http_code}" "${curl_args[@]}")
    response_body=$(echo "$response" | head -n -1)
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "$expected_code" ]; then
        log_success "$name - HTTP $http_code"
        echo "$response_body" | jq . 2>/dev/null || echo "$response_body"
    else
        log_error "$name - Expected HTTP $expected_code, got $http_code"
        echo "$response_body"
        return 1
    fi
    echo ""
}

# Main test execution
main() {
    log_info "Starting AI Companion Chat API Test Suite"
    log_info "Base URL: $BASE_URL"
    log_info "Test Email: $TEST_EMAIL"
    echo ""

    # Step 1: Check health
    log_info "=== HEALTH CHECK ==="
    test_endpoint "Health Check" "200" \
        -X GET "$BASE_URL/health"

    # Step 2: Register user
    log_info "=== USER REGISTRATION ==="
    REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\",
            \"preferred_language\": \"en\"
        }")
    
    if echo "$REGISTER_RESPONSE" | jq -e '.access_token' > /dev/null; then
        ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
        log_success "User registered successfully"
        echo "$REGISTER_RESPONSE" | jq .
    else
        log_error "Registration failed"
        echo "$REGISTER_RESPONSE"
        exit 1
    fi
    echo ""

    # Step 3: Test authentication
    log_info "=== AUTHENTICATION TEST ==="
    test_endpoint "Get User Profile" "200" \
        -X GET "$BASE_URL/auth/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    # Step 4: Get characters
    log_info "=== CHARACTER MANAGEMENT ==="
    CHARACTERS_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
        "$BASE_URL/characters")
    
    if echo "$CHARACTERS_RESPONSE" | jq -e '.characters[0].id' > /dev/null; then
        CHARACTER_ID=$(echo "$CHARACTERS_RESPONSE" | jq -r '.characters[0].id')
        CHARACTER_NAME=$(echo "$CHARACTERS_RESPONSE" | jq -r '.characters[0].name')
        log_success "Got characters - Selected: $CHARACTER_NAME (ID: $CHARACTER_ID)"
        echo "$CHARACTERS_RESPONSE" | jq .
    else
        log_error "Failed to get characters"
        echo "$CHARACTERS_RESPONSE"
        exit 1
    fi
    echo ""

    # Step 5: Select character
    log_info "=== CHARACTER SELECTION ==="
    test_endpoint "Switch Character" "200" \
        -X POST "$BASE_URL/api/v1/chat/switch-character" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"character_id\": $CHARACTER_ID}"

    # Step 6: Get conversation info
    log_info "=== CONVERSATION MANAGEMENT ==="
    test_endpoint "Get Conversation Info" "200" \
        -X GET "$BASE_URL/api/v1/chat/conversation" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    # Step 7: Test chat (non-streaming)
    log_info "=== CHAT FUNCTIONALITY (NON-STREAMING) ==="
    test_endpoint "Send Chat Message (Non-streaming)" "200" \
        -X POST "$BASE_URL/api/v1/chat/send" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Hello! This is a test message. Please respond briefly.",
            "stream": false
        }'

    # Step 8: Test chat history
    log_info "=== CHAT HISTORY ==="
    test_endpoint "Get Chat History" "200" \
        -X GET "$BASE_URL/api/v1/chat/history?limit=10" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    # Step 9: Send multiple messages for conversation flow
    log_info "=== CONVERSATION FLOW TEST ==="
    for i in {1..3}; do
        test_endpoint "Chat Message $i" "200" \
            -X POST "$BASE_URL/api/v1/chat/send" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"message\": \"This is test message number $i. Please acknowledge.\",
                \"stream\": false
            }"
        sleep 1
    done

    # Step 10: Test provider status
    log_info "=== PROVIDER STATUS ==="
    test_endpoint "Get Provider Status" "200" \
        -X GET "$BASE_URL/api/v1/chat/provider" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    # Step 11: Test error cases
    log_info "=== ERROR HANDLING TESTS ==="
    
    # Test without authentication
    test_endpoint "Unauthorized Access" "401" \
        -X GET "$BASE_URL/api/v1/chat/conversation"
    
    # Test invalid character selection
    test_endpoint "Invalid Character Selection" "404" \
        -X POST "$BASE_URL/api/v1/chat/switch-character" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"character_id": 999}'
    
    # Test empty message
    test_endpoint "Empty Message Validation" "422" \
        -X POST "$BASE_URL/api/v1/chat/send" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"message": "", "stream": false}'

    # Step 12: Final conversation state
    log_info "=== FINAL STATE CHECK ==="
    test_endpoint "Final Chat History" "200" \
        -X GET "$BASE_URL/api/v1/chat/history?limit=20" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    test_endpoint "Final Conversation Info" "200" \
        -X GET "$BASE_URL/api/v1/chat/conversation" \
        -H "Authorization: Bearer $ACCESS_TOKEN"

    log_success "All tests completed successfully!"
    log_info "Test user: $TEST_EMAIL"
    log_info "Access token: $ACCESS_TOKEN"
}

# Check dependencies
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found - JSON output won't be formatted"
    fi
}

# Cleanup function
cleanup() {
    log_info "Test completed"
}

trap cleanup EXIT

# Run tests
check_dependencies
main