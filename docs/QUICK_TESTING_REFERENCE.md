# Quick Testing Reference - AI Companion API

## Testing Checklist

### ✅ Prerequisites
- [ ] Application running on `http://localhost:8000`
- [ ] MySQL database connected
- [ ] Redis cache connected
- [ ] At least one LLM provider configured (Groq/OpenAI)

### ✅ Basic Flow Test
```bash
# 1. Check health
curl http://localhost:8000/health

# 2. Register
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123", "preferred_language": "en"}'
# → Save access_token

# 3. Get characters
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/characters
# → Note character ID

# 4. Select character
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 1}'

# 5. Send message
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "stream": false}'

# 6. Check history
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/chat/history"
```

## Key Endpoints Summary

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| POST | `/auth/register` | Register user | No |
| POST | `/auth/login` | Login user | No |
| GET | `/auth/me` | Get user profile | Yes |
| GET | `/characters` | List characters | Yes |
| POST | `/api/v1/chat/switch-character` | Select character | Yes |
| POST | `/api/v1/chat/send` | Send message | Yes |
| GET | `/api/v1/chat/history` | Get history | Yes |
| GET | `/api/v1/chat/conversation` | Get conversation info | Yes |
| GET | `/api/v1/chat/provider` | Check LLM status | Yes |

## Expected Response Codes

| Endpoint | Success | Error Cases |
|----------|---------|-------------|
| Register/Login | 200 | 422 (validation), 400 (user exists) |
| Characters | 200 | 401 (unauthorized) |
| Switch Character | 200 | 401, 404 (character not found) |
| Send Message | 200 | 401, 400 (no character), 422 (validation) |
| Chat History | 200 | 401, 400 (no character) |

## SSE Streaming Test

```bash
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Tell me a story", "stream": true}' \
  --no-buffer
```

**Expected SSE Events:**
1. `chat-start` - Metadata about conversation
2. `chat-content` - Multiple content chunks
3. `chat-complete` - Completion metadata

## Error Testing

```bash
# No auth
curl http://localhost:8000/api/v1/chat/conversation
# → 401 Unauthorized

# No character selected
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "stream": false}'
# → 400 CHARACTER_NOT_SELECTED

# Invalid character
curl -X POST "http://localhost:8000/api/v1/chat/switch-character" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id": 999}'
# → 404 Character not found
```

## Performance Validation

### Response Time Expectations
- Health check: < 100ms
- Authentication: < 500ms
- Character selection: < 200ms
- Chat message (cached): < 1s
- Chat message (LLM): 1-5s
- Chat history: < 300ms

### Caching Verification
```bash
# First request (cache miss)
time curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/chat/history"

# Second request (cache hit - should be faster)
time curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/chat/history"
```

## Troubleshooting Quick Fixes

### Service Issues
```bash
# Check containers
docker ps | grep -E "(mysql|redis)"

# Restart if needed
docker restart mysql-ai-companion redis-ai-companion

# Check logs
docker logs mysql-ai-companion
docker logs redis-ai-companion
```

### Application Issues
```bash
# Check health
curl http://localhost:8000/health

# Check specific service health
curl http://localhost:8000/health | jq '.services'
```

### Common Error Solutions

| Error | Solution |
|-------|----------|
| Connection refused | Check if app is running on port 8000 |
| Database error | Verify MySQL container and credentials |
| Redis error | Check Redis container |
| LLM unavailable | Verify API keys in environment |
| 401 Unauthorized | Check token format and expiration |
| CHARACTER_NOT_SELECTED | Select character first |

## Data Validation

### User Registration
- Email: Valid format required
- Password: Minimum 8 characters
- Language: "en", "es", or "zh"

### Chat Messages
- Content: 1-2000 characters
- Stream: Boolean (true/false)

### Pagination
- Limit: 1-100 (default: 20)
- Offset: >= 0 (default: 0)

## Sample Valid Requests

### Registration
```json
{
  "email": "user@domain.com",
  "password": "securepass123",
  "preferred_language": "en"
}
```

### Character Selection
```json
{
  "character_id": 1
}
```

### Chat Message
```json
{
  "message": "Hello, how are you today?",
  "stream": false
}
```

### Streaming Chat
```json
{
  "message": "Tell me about artificial intelligence",
  "stream": true
}
```