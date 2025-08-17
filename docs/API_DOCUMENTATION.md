# AI Companion Chat API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication

### Register User
**POST** `/auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "preferred_language": "en"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "preferred_language": "en"
  }
}
```

### Login User
**POST** `/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "preferred_language": "en"
  }
}
```

### Get User Profile
**GET** `/auth/me`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "preferred_language": "en",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Character Management

### Get Available Characters
**GET** `/characters`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "characters": [
    {
      "id": 1,
      "name": "Luna",
      "personality_type": "friendly",
      "description": "A warm and supportive companion who loves to help and chat about daily life.",
      "languages": ["en", "es", "zh"]
    },
    {
      "id": 2,
      "name": "Alex",
      "personality_type": "professional",
      "description": "A knowledgeable business advisor focused on productivity and professional growth.",
      "languages": ["en", "es", "zh"]
    },
    {
      "id": 3,
      "name": "Maya",
      "personality_type": "creative",
      "description": "An artistic and imaginative companion who loves creative projects and storytelling.",
      "languages": ["en", "es", "zh"]
    }
  ]
}
```

### Switch Character
**POST** `/api/v1/chat/switch-character`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "character_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "character": {
    "id": 1,
    "name": "Luna",
    "personality_type": "friendly",
    "description": "A warm and supportive companion who loves to help and chat about daily life."
  }
}
```

---

## Chat API

### Send Chat Message (Non-Streaming)
**POST** `/api/v1/chat/send`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Hello! How are you today?",
  "stream": false
}
```

**Response:**
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
      "provider": "groq",
      "estimated_tokens": 45
    },
    {
      "type": "content",
      "content": "Hello! I'm doing wonderfully, thank you for asking! It's always a pleasure to chat with you. How has your day been going so far?",
      "provider": "groq"
    },
    {
      "type": "complete",
      "conversation_id": 123,
      "provider_used": "groq",
      "duration_seconds": 1.2,
      "message_length": 87,
      "timestamp": "2024-01-15T10:35:00Z"
    }
  ]
}
```

### Send Chat Message (Streaming SSE)
**POST** `/api/v1/chat/send`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: text/event-stream
```

**Request:**
```json
{
  "message": "Tell me a short story",
  "stream": true
}
```

**Response (Server-Sent Events):**
```
event: chat-start
data: {"type":"metadata","conversation_id":123,"character":{"id":1,"name":"Luna","personality_type":"friendly"},"provider":"groq","estimated_tokens":52}

event: chat-content
data: {"type":"content","content":"Once upon a time","provider":"groq"}

event: chat-content
data: {"type":"content","content":" in a small village","provider":"groq"}

event: chat-content
data: {"type":"content","content":", there lived a kind baker","provider":"groq"}

event: chat-content
data: {"type":"content","content":" who made magical bread that could heal any sadness.","provider":"groq"}

event: chat-complete
data: {"type":"complete","conversation_id":123,"provider_used":"groq","duration_seconds":2.1,"message_length":98,"timestamp":"2024-01-15T10:37:00Z"}
```

### Get Chat History
**GET** `/api/v1/chat/history`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of messages to return (1-100, default: 20)
- `offset` (optional): Offset for pagination (default: 0)

**Example:**
```
GET /api/v1/chat/history?limit=10&offset=0
```

**Response:**
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
      "content": "Hello! I'm doing wonderfully, thank you for asking! It's always a pleasure to chat with you.",
      "created_at": "2024-01-15T10:30:02Z",
      "is_from_user": false,
      "is_from_assistant": true
    },
    {
      "id": 3,
      "conversation_id": 123,
      "sender_type": "user",
      "content": "Tell me a short story",
      "created_at": "2024-01-15T10:35:00Z",
      "is_from_user": true,
      "is_from_assistant": false
    },
    {
      "id": 4,
      "conversation_id": 123,
      "sender_type": "assistant",
      "content": "Once upon a time in a small village, there lived a kind baker who made magical bread that could heal any sadness.",
      "created_at": "2024-01-15T10:35:02Z",
      "is_from_user": false,
      "is_from_assistant": true
    }
  ],
  "total": 4,
  "character_id": 1,
  "user_id": 1,
  "started_at": "2024-01-15T10:30:00Z",
  "last_message_at": "2024-01-15T10:35:02Z"
}
```

### Get Conversation Info
**GET** `/api/v1/chat/conversation`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 123,
  "user_id": 1,
  "character_id": 1,
  "message_count": 4,
  "started_at": "2024-01-15T10:30:00Z",
  "last_message_at": "2024-01-15T10:35:02Z",
  "character": {
    "id": 1,
    "name": "Luna",
    "personality_type": "friendly",
    "description": "A warm and supportive companion who loves to help and chat about daily life."
  }
}
```

---

## Provider Management

### Get Provider Status
**GET** `/api/v1/chat/provider`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "data": {
    "status": "healthy",
    "current_provider": "groq",
    "fallback_provider": "openai",
    "available_providers": ["groq", "openai"],
    "available_provider": "groq",
    "current_model": "llama-3.1-70b-versatile"
  },
  "headers": {
    "X-LLM-Provider": "groq",
    "X-LLM-Model": "llama-3.1-70b-versatile",
    "X-Service-Status": "healthy"
  }
}
```

### Switch Provider (Admin)
**POST** `/api/v1/chat/admin/llm/switch?provider=openai`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to provider: openai",
  "provider_info": {
    "current_provider": "openai",
    "fallback_provider": "groq",
    "available_providers": ["groq", "openai"],
    "current_model": "gpt-4o-mini"
  }
}
```

### Test Provider Connection (Admin)
**GET** `/api/v1/chat/admin/llm/test?provider=groq`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "provider": "groq",
  "connected": true,
  "timestamp": "2024-01-15T10:40:00Z"
}
```

---

## Health Check

### Application Health
**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm_provider": "available"
  },
  "timestamp": "2024-01-15T10:45:00Z",
  "version": "1.0.0"
}
```

---

## Error Responses

### Authentication Errors

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### Validation Errors

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 400 Bad Request - No Character Selected
```json
{
  "detail": {
    "type": "error",
    "error": "No character selected. Please select a character first.",
    "code": "CHARACTER_NOT_SELECTED"
  }
}
```

#### 400 Bad Request - Message Too Long
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "ensure this value has at most 2000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### Chat Service Errors

#### Service Unavailable
```json
{
  "type": "error",
  "error": "AI service is currently unavailable. Please try again later.",
  "code": "SERVICE_UNAVAILABLE"
}
```

#### Processing Error
```json
{
  "type": "error",
  "error": "An unexpected error occurred while processing your message.",
  "code": "PROCESSING_ERROR",
  "conversation_id": 123
}
```

#### LLM Generation Error
```json
{
  "type": "error",
  "error": "Failed to generate AI response",
  "code": "LLM_ERROR",
  "conversation_id": 123
}
```

### Character Errors

#### 404 Character Not Found
```json
{
  "detail": "Character not found"
}
```

### Server Errors

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Testing with curl

### Complete Testing Flow

```bash
# 1. Register user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "preferred_language": "en"
  }'

# 2. Save the access_token from response, then get characters
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  "http://localhost:8000/characters"

# 3. Select a character (use character ID from previous response)
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 1}'

# 4. Send a chat message (non-streaming)
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! How are you?",
    "stream": false
  }'

# 5. Send a chat message (streaming)
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Tell me a joke",
    "stream": true
  }' \
  --no-buffer

# 6. Get chat history
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  "http://localhost:8000/api/v1/chat/history?limit=10"

# 7. Get conversation info
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  "http://localhost:8000/api/v1/chat/conversation"
```

---

## Rate Limits (Future Implementation)

The following rate limits will be implemented:

- **Authentication endpoints**: 5 requests per minute per IP
- **Chat endpoints**: 10 requests per minute per user
- **Daily message limits**: 
  - Free tier: 20 messages per day
  - Pro tier: 500 messages per day

When rate limits are exceeded:

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

---

## Notes

1. All timestamps are in ISO 8601 format (UTC)
2. Message content is limited to 2000 characters
3. SSE connections include heartbeat pings to prevent timeouts
4. Authentication tokens expire after 24 hours
5. Conversation context is cached in Redis for 1 hour
6. The system supports failover between LLM providers (Groq/OpenAI)