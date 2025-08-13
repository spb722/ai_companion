#!/bin/bash

# AI Companion Authentication Test Script
API_BASE="http://localhost:8001/api/v1"
EMAIL="test$(date +%s)@example.com"  # Unique email
PASSWORD="TestPass123"

echo "🧪 Testing AI Companion Authentication System"
echo "============================================="

# Test 1: Health Check
echo "1. Testing Health Check..."
curl -s -X GET "$API_BASE/health" | jq '.'

# Test 2: User Registration
echo -e "\n2. Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"username\": \"testuser\"
  }")

echo "$REGISTER_RESPONSE" | jq '.'

# Extract access token
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.data.session.access_token')

# Test 3: Get Profile
echo -e "\n3. Testing Get Profile..."
curl -s -X GET "$API_BASE/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'

# Test 4: Update Profile
echo -e "\n4. Testing Profile Update..."
curl -s -X PATCH "$API_BASE/auth/profile" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "updated_user",
    "preferred_language": "hi"
  }' | jq '.'

echo -e "\n✅ Authentication tests completed!"
echo "Check the responses above for success/failure status."