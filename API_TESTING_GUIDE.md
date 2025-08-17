# AI Companion Chat API Testing Guide

## Overview

This guide provides comprehensive documentation for testing the AI Companion Chat Engine APIs. The system includes authentication, character management, real-time chat with Server-Sent Events (SSE), conversation management, and Redis caching.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Environment Setup](#environment-setup)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Testing Scenarios](#testing-scenarios)
6. [SSE Testing](#sse-testing)
7. [Error Handling](#error-handling)
8. [Performance Testing](#performance-testing)
9. [Troubleshooting](#troubleshooting)

## System Requirements

### Dependencies
- Python 3.11+
- FastAPI
- MySQL database
- Redis server
- Supabase account (for authentication)
- LLM provider (Groq/OpenAI) API keys

### Environment Variables
```bash
# Database
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/ai_companion

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase Authentication
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# LLM Providers (at least one required)
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Environment Setup

### 1. Start Required Services

```bash
# Start MySQL (Docker example)
docker run -d --name mysql-ai-companion \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=ai_companion \
  -e MYSQL_USER=aiuser \
  -e MYSQL_PASSWORD=aipassword \
  -p 3306:3306 mysql:8.0

# Start Redis
docker run -d --name redis-ai-companion -p 6379:6379 redis:7-alpine

# Or use local installations
# MySQL: brew install mysql && brew services start mysql
# Redis: brew install redis && brew services start redis
```

### 2. Run Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m app.db.init_db

# Seed character data
python -m app.db.seed_characters

# Start the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Verify Services

```bash
# Check application health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm_provider": "available"
  },
  "timestamp": "2024-01-XX..."
}
```

## Authentication

### User Registration

**Endpoint:** `POST /auth/register`

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123",
    "preferred_language": "en"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "preferred_language": "en"
  }
}
```

### User Login

**Endpoint:** `POST /auth/login`

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

### Using Authentication Token

For all protected endpoints, include the Bearer token:

```bash
# Set token as environment variable for easier testing
export AUTH_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Use in requests
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/protected-endpoint"
```

## API Endpoints

### Character Management

#### Get Available Characters

**Endpoint:** `GET /characters`

```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/characters"
```

**Expected Response:**
```json
{
  "characters": [
    {
      "id": 1,
      "name": "Luna",
      "personality_type": "friendly",
      "description": "A warm and supportive companion...",
      "languages": ["en", "es", "zh"]
    },
    {
      "id": 2,
      "name": "Alex",
      "personality_type": "professional",
      "description": "A knowledgeable business advisor...",
      "languages": ["en", "es", "zh"]
    }
  ]
}
```

#### Select Character

**Endpoint:** `POST /chat/switch-character`

```bash
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 1}'
```

### Chat Endpoints

#### Get Current Conversation Info

**Endpoint:** `GET /api/v1/chat/conversation`

```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/conversation"
```

**Expected Response:**
```json
{
  "id": 123,
  "user_id": 1,
  "character_id": 1,
  "message_count": 5,
  "started_at": "2024-01-15T10:30:00Z",
  "last_message_at": "2024-01-15T10:35:00Z",
  "character": {
    "id": 1,
    "name": "Luna",
    "personality_type": "friendly",
    "description": "A warm and supportive companion..."
  }
}
```

#### Send Chat Message (Non-Streaming)

**Endpoint:** `POST /api/v1/chat/send`

```bash
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! How are you today?",
    "stream": false
  }'
```

**Expected Response:**
```json
{
  "messages": [
    {
      "type": "metadata",
      "conversation_id": 123,
      "character": {
        "id": 1,
        "name": "Luna",
        "personality_type": "friendly"
      },
      "provider": "groq"
    },
    {
      "type": "content",
      "content": "Hello! I'm doing wonderfully, thank you for asking...",
      "provider": "groq"
    },
    {
      "type": "complete",
      "conversation_id": 123,
      "provider_used": "groq",
      "duration_seconds": 1.2
    }
  ]
}
```

#### Send Chat Message (Streaming SSE)

**Endpoint:** `POST /api/v1/chat/send` (with stream: true)

```bash
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Tell me a short story",
    "stream": true
  }' \
  --no-buffer
```

**Expected SSE Response:**
```
event: chat-start
data: {"type":"metadata","conversation_id":123,"character":{"id":1,"name":"Luna"}}

event: chat-content
data: {"type":"content","content":"Once upon","provider":"groq"}

event: chat-content
data: {"type":"content","content":" a time","provider":"groq"}

event: chat-content
data: {"type":"content","content":" in a","provider":"groq"}

event: chat-complete
data: {"type":"complete","conversation_id":123,"duration_seconds":2.1}
```

#### Get Chat History

**Endpoint:** `GET /api/v1/chat/history`

```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/history?limit=10&offset=0"
```

**Expected Response:**
```json
{
  "conversation_id": 123,
  "messages": [
    {
      "id": 1,
      "conversation_id": 123,
      "sender_type": "user",
      "content": "Hello! How are you today?",
      "created_at": "2024-01-15T10:30:00Z",
      "is_from_user": true,
      "is_from_assistant": false
    },
    {
      "id": 2,
      "conversation_id": 123,
      "sender_type": "assistant",
      "content": "Hello! I'm doing wonderfully...",
      "created_at": "2024-01-15T10:30:02Z",
      "is_from_user": false,
      "is_from_assistant": true
    }
  ],
  "total": 4,
  "character_id": 1,
  "user_id": 1
}
```

### Provider Management

#### Get Provider Status

**Endpoint:** `GET /api/v1/chat/provider`

```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/provider"
```

#### Switch Provider (Admin)

**Endpoint:** `POST /api/v1/chat/admin/llm/switch`

```bash
curl -X POST "http://localhost:8000/api/v1/chat/admin/llm/switch?provider=openai" \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

## Testing Scenarios

### Basic Functionality Tests

#### 1. User Authentication Flow
```bash
# Test registration
./test_scripts/test_auth_flow.sh

# Expected: Successful registration and login
```

#### 2. Character Selection
```bash
# Test character listing and selection
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/characters"

# Select character
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 1}'

# Verify selection
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/conversation"
```

#### 3. Basic Chat Flow
```bash
# Send first message
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "stream": false}'

# Get history
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/history?limit=5"

# Send follow-up
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more", "stream": false}'
```

#### 4. Conversation Persistence
```bash
# Send multiple messages
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/v1/chat/send" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Message $i\", \"stream\": false}"
  sleep 1
done

# Verify all messages saved
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/history?limit=20"
```

### Edge Case Testing

#### 1. No Character Selected
```bash
# Try to chat without selecting character
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "stream": false}'

# Expected: 400 error with CHARACTER_NOT_SELECTED code
```

#### 2. Invalid Character Selection
```bash
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 999}'

# Expected: 404 error
```

#### 3. Long Messages
```bash
# Test with very long message (2000+ characters)
LONG_MESSAGE=$(python -c "print('A' * 2001)")
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$LONG_MESSAGE\", \"stream\": false}"

# Expected: 422 validation error
```

#### 4. Invalid Authentication
```bash
# Test with invalid token
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "stream": false}'

# Expected: 401 Unauthorized
```

## SSE Testing

### Testing with curl

```bash
# Test SSE streaming
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Tell me a story about space", "stream": true}' \
  --no-buffer -v
```

### Testing with JavaScript

```javascript
// Browser testing
const eventSource = new EventSource('/api/v1/chat/send', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

eventSource.addEventListener('chat-start', (event) => {
  const data = JSON.parse(event.data);
  console.log('Chat started:', data);
});

eventSource.addEventListener('chat-content', (event) => {
  const data = JSON.parse(event.data);
  console.log('Content chunk:', data.content);
});

eventSource.addEventListener('chat-complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('Chat completed:', data);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  console.error('SSE Error:', event);
});
```

### Testing with Python

```python
import requests
import json

def test_sse_stream():
    url = "http://localhost:8000/api/v1/chat/send"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    data = {
        "message": "Tell me about AI",
        "stream": True
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                print(f"Received: {data}")
```

## Performance Testing

### Concurrent Users Test

```bash
# Test with multiple concurrent users
for i in {1..10}; do
  (
    TOKEN=$(get_auth_token "user$i@example.com")
    curl -X POST "http://localhost:8000/api/v1/chat/send" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"message": "Hello from user '$i'", "stream": false}' &
  )
done
wait
```

### Cache Performance Test

```bash
# Test Redis caching effectiveness
echo "First request (cache miss):"
time curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/history?limit=20"

echo "Second request (cache hit):"
time curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/history?limit=20"
```

### Load Testing with ab

```bash
# Install Apache Bench
# brew install httpie

# Test endpoint load
ab -n 100 -c 10 -H "Authorization: Bearer $AUTH_TOKEN" \
  "http://localhost:8000/api/v1/chat/conversation"
```

## Error Handling

### Expected Error Responses

#### Authentication Errors
```json
{
  "detail": "Could not validate credentials",
  "status_code": 401
}
```

#### Character Not Selected
```json
{
  "detail": {
    "type": "error",
    "error": "No character selected. Please select a character first.",
    "code": "CHARACTER_NOT_SELECTED"
  },
  "status_code": 400
}
```

#### Service Unavailable
```json
{
  "type": "error",
  "error": "AI service is currently unavailable. Please try again later.",
  "code": "SERVICE_UNAVAILABLE"
}
```

#### Rate Limiting (Future)
```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "status_code": 429
}
```

## Validation Checklist

### ✅ Core Functionality
- [ ] User registration and login work
- [ ] Character selection and switching work
- [ ] Non-streaming chat messages work
- [ ] SSE streaming chat works
- [ ] Message history retrieval works
- [ ] Conversation persistence works

### ✅ Authentication & Security
- [ ] Protected endpoints require valid JWT
- [ ] Invalid tokens are rejected
- [ ] User isolation (can't access other users' data)

### ✅ Data Integrity
- [ ] Messages are saved to database
- [ ] Conversation metadata updates correctly
- [ ] Message order is preserved
- [ ] Character associations are correct

### ✅ Performance & Caching
- [ ] Redis caching improves response times
- [ ] Cache invalidation works on new messages
- [ ] System degrades gracefully if Redis is down

### ✅ Error Handling
- [ ] Appropriate error codes returned
- [ ] Error messages are user-friendly
- [ ] System handles LLM provider failures
- [ ] SSE streams handle errors gracefully

### ✅ SSE Streaming
- [ ] SSE headers are correct
- [ ] Events are properly formatted
- [ ] Streaming works in browsers
- [ ] Connection timeouts are handled
- [ ] Heartbeats prevent disconnections

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check MySQL status
docker ps | grep mysql

# Check logs
docker logs mysql-ai-companion

# Verify connection
mysql -h localhost -u aiuser -p ai_companion
```

#### 2. Redis Connection Errors
```bash
# Check Redis status
docker ps | grep redis

# Test connection
redis-cli ping

# Check logs
docker logs redis-ai-companion
```

#### 3. Authentication Issues
```bash
# Verify Supabase configuration
curl -H "apikey: $SUPABASE_KEY" \
  "$SUPABASE_URL/rest/v1/"

# Check JWT token validity
echo $AUTH_TOKEN | base64 -d
```

#### 4. LLM Provider Issues
```bash
# Test provider endpoint
curl "http://localhost:8000/api/v1/chat/admin/llm/test"

# Check API keys
echo $GROQ_API_KEY | wc -c
echo $OPENAI_API_KEY | wc -c
```

#### 5. SSE Not Working
- Check browser developer tools for SSE connection
- Verify `Accept: text/event-stream` header
- Check for proxy/nginx buffering issues
- Test with `curl --no-buffer`

### Logs and Monitoring

```bash
# Application logs
tail -f logs/app.log

# Database query logs
tail -f logs/db.log

# Redis logs
docker logs -f redis-ai-companion

# Check system resources
htop
```

### Health Checks

```bash
# Overall system health
curl http://localhost:8000/health

# Specific service health
curl http://localhost:8000/health/database
curl http://localhost:8000/health/redis
curl http://localhost:8000/health/llm
```

## Test Scripts

The repository includes automated test scripts in `/test_scripts/`:

```bash
# Run all tests
./test_scripts/run_all_tests.sh

# Individual test suites
./test_scripts/test_auth.sh
./test_scripts/test_chat.sh
./test_scripts/test_sse.sh
./test_scripts/test_performance.sh
```

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review application logs
3. Verify all environment variables are set
4. Test individual components in isolation
5. Contact the development team with detailed error messages

---

**Last Updated:** January 2024  
**API Version:** v1  
**Documentation Version:** 1.0