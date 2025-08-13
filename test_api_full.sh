#!/bin/bash

# Complete API Testing Script
API_BASE="http://localhost:8001/api/v1"
TIMESTAMP=$(date +%s)
EMAIL="test.user.$TIMESTAMP@gmail.com" 
PASSWORD="TestPassword123"
USERNAME="testuser$TIMESTAMP"

echo "🧪 Complete AI Companion API Test"
echo "================================="
echo "Email: $EMAIL"
echo "Username: $USERNAME"

# Test 1: Health Check
echo -e "\n1️⃣ Testing Health Check..."
curl -s -X GET "$API_BASE/health" | jq '.'

# Test 2: User Registration
echo -e "\n2️⃣ Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"username\": \"$USERNAME\"
  }")

echo "$REGISTER_RESPONSE" | jq '.'

# Check if registration was successful
if echo "$REGISTER_RESPONSE" | jq -e '.success' > /dev/null; then
    echo "✅ Registration successful!"
    
    # Check if email confirmation is required
    EMAIL_CONFIRMATION=$(echo "$REGISTER_RESPONSE" | jq -r '.data.email_confirmation_required // false')
    
    if [ "$EMAIL_CONFIRMATION" = "true" ]; then
        echo "📧 Email confirmation required - cannot test login until confirmed"
        echo "   Check your Supabase project settings to disable email confirmation for testing"
    else
        # Extract access token if available
        ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.data.session.access_token // null')
        
        if [ "$ACCESS_TOKEN" != "null" ]; then
            echo -e "\n3️⃣ Testing Get Profile with Token..."
            curl -s -X GET "$API_BASE/auth/me" \
              -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
        fi
    fi
else
    echo "❌ Registration failed"
fi

echo -e "\n✅ API tests completed!"
echo "Note: Full authentication flow requires email confirmation to be disabled in Supabase"