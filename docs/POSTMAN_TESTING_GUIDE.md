# AI Companion - Postman Testing Guide
## Rate Limiting & Message Quota Features

### 📋 Prerequisites

1. **Application Running**: Make sure your app is running on `http://localhost:8000`
2. **Services Active**: Redis and MySQL containers should be running
3. **Postman Installed**: Download from [postman.com](https://www.postman.com/downloads/)

### 📥 Import the Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose: `docs/AI_Companion_Rate_Limiting_Testing.postman_collection.json`
5. Click **Import**

### 🌍 Environment Setup

The collection uses the environment variable `{{base_url}}` which is set to `http://localhost:8000` by default.

**Optional**: Create a Postman Environment for better organization:
1. Click **Environments** (left sidebar)
2. Click **Create Environment**
3. Name it: `AI Companion Local`
4. Add variables:
   - `base_url`: `http://localhost:8000`
   - `access_token`: (will be auto-populated)
   - `character_id`: (will be auto-populated)
   - `user_id`: (will be auto-populated)

---

## 🧪 Testing Steps - Execute in Order

### **Phase 1: Setup & Authentication** 🔐

#### 1.1 Health Check
- **Purpose**: Verify the application is running
- **Expected**: `200 OK` with health status
- **Action**: Click **Send**

#### 1.2 Register Test User
- **Purpose**: Create a new user account
- **Auto-Features**: 
  - Uses timestamp in email to avoid conflicts
  - Automatically saves `access_token` to environment
- **Expected**: `200 OK` with user details and JWT token
- **Verify**: Check **Console** tab for "Access token saved"

#### 1.3 Get Characters
- **Purpose**: Retrieve available AI characters
- **Auto-Features**: Automatically saves first character ID
- **Expected**: `200 OK` with character list
- **Verify**: Check **Console** for "Character ID saved"

#### 1.4 Select Character
- **Purpose**: Choose character for chat conversations
- **Expected**: `200 OK` confirming character selection
- **Verify**: Response shows selected character details

---

### **Phase 2: Rate Limiting Tests** ⏱️

> **Important**: Execute these requests quickly (within 1 minute) to test rate limiting

#### 2.1 Rate Limit Test 1-5
- **Purpose**: First batch of requests (should succeed)
- **Action**: Send this request **5 times rapidly**
- **Expected**: All should return `200 OK`
- **Observe**: `X-RateLimit-Remaining` header decreasing

#### 2.2 Rate Limit Test 6-10
- **Purpose**: Second batch of requests (should succeed)
- **Action**: Send this request **5 times rapidly**
- **Expected**: All should return `200 OK`
- **Observe**: `X-RateLimit-Remaining` header approaching 0

#### 2.3 Rate Limit Test 11 (Should Fail)
- **Purpose**: Trigger rate limiting
- **Action**: Send immediately after previous tests
- **Expected**: `429 Too Many Requests`
- **Verify**: 
  ```json
  {
    "detail": {
      "code": "RATE_LIMIT_EXCEEDED",
      "error": "Rate limit exceeded. Please try again later.",
      "retry_after": 45
    }
  }
  ```

#### 2.4 Check Rate Limit Headers
- **Purpose**: Verify rate limit headers are present
- **Expected**: `200 OK` with headers:
  - `X-RateLimit-Limit: 10`
  - `X-RateLimit-Remaining: 0`
  - `X-RateLimit-Reset: [timestamp]`
- **Verify**: Check **Headers** tab in response

**⏰ Wait 1 minute before proceeding to reset rate limits**

---

### **Phase 3: Message Quota Tests** 💬

#### 3.1 Check Initial Usage
- **Purpose**: View starting quota status
- **Expected**: `200 OK` showing:
  ```json
  {
    "tier": "free",
    "quota": {
      "limit": 20,
      "used": 0,
      "remaining": 20
    }
  }
  ```

#### 3.2 Send Message 1-5 (Batch)
- **Purpose**: Send several messages to consume quota
- **Action**: Send this request **5-15 times**
- **Expected**: `200 OK` with decreasing `quota.remaining`
- **Observe**: Console shows remaining message count

#### 3.3 Check Usage After Messages
- **Purpose**: Verify quota consumption
- **Expected**: `quota.used` > 0, `quota.remaining` < 20
- **Verify**: Console shows updated usage

#### 3.4 Send Messages Until Quota Exceeded
- **Purpose**: Hit the free tier limit (20 messages)
- **Action**: Keep sending until you get quota exceeded
- **Method**: 
  1. Send this request repeatedly
  2. Watch console for remaining count
  3. Continue until you see quota exceeded error

- **Expected Final Response**: `400 Bad Request`
  ```json
  {
    "success": false,
    "error": "Daily message limit reached",
    "code": "QUOTA_EXCEEDED",
    "quota": {
      "tier": "free",
      "limit": 20,
      "used": 20,
      "remaining": 0
    }
  }
  ```

---

### **Phase 4: Tier Management Tests** ⬆️

#### 4.1 Get User Profile
- **Purpose**: View current user details
- **Expected**: User profile with quota information
- **Verify**: `subscription_tier: "free"`

#### 4.2 Upgrade to Pro Tier
- **Purpose**: Test tier upgrade functionality
- **Expected**: `200 OK` with:
  ```json
  {
    "success": true,
    "message": "Tier updated from 'free' to 'pro'",
    "user": {
      "subscription_tier": "pro"
    },
    "quota": {
      "limit": 500,
      "remaining": 500
    }
  }
  ```
- **Key Feature**: Quota resets to 500 messages!

#### 4.3 Verify Pro Tier Usage
- **Purpose**: Confirm pro tier activation
- **Expected**: `tier: "pro"`, `limit: 500`
- **Verify**: Console shows pro tier verification

#### 4.4 Test Pro Tier Message
- **Purpose**: Send message with pro tier
- **Expected**: `200 OK` with `quota.remaining` close to 500
- **Verify**: Message sends successfully with pro quota

#### 4.5 Downgrade to Free Tier
- **Purpose**: Test tier downgrade
- **Expected**: `200 OK` with tier changed back to "free"
- **Note**: Quota limit returns to 20

---

### **Phase 5: Advanced Tests** 🚀

#### 5.1 Test SSE Streaming
- **Purpose**: Verify streaming works with quota tracking
- **Special Setup**: Uses `Accept: text/event-stream` header
- **Expected**: Streaming response with SSE events
- **Note**: This will count toward your quota

#### 5.2 Test Invalid Tier Upgrade
- **Purpose**: Verify input validation
- **Expected**: `422 Validation Error`
- **Verify**: Rejects invalid tier "premium"

#### 5.3 Test Unauthorized Access
- **Purpose**: Verify authentication requirement
- **Expected**: `401 Unauthorized`
- **Verify**: Request without token fails

---

## 📊 Expected Test Results Summary

| Test Phase | Success Criteria |
|------------|------------------|
| **Setup** | ✅ User created, token saved, character selected |
| **Rate Limiting** | ✅ 10 requests succeed, 11th fails with 429 |
| **Quota (Free)** | ✅ 20 messages allowed, 21st fails with QUOTA_EXCEEDED |
| **Tier Upgrade** | ✅ Pro tier gives 500 message limit |
| **Advanced** | ✅ Streaming works, validation works, auth required |

## 🐛 Troubleshooting

### Common Issues:

1. **Rate Limit Not Working**
   - Wait 60 seconds between rate limit test batches
   - Check Redis is running: `docker ps | grep redis`

2. **Quota Not Resetting on Upgrade**
   - Check database user tier update
   - Verify Redis quota key reset

3. **Authentication Errors**
   - Re-run "Register Test User" to get fresh token
   - Check token is saved in environment variables

4. **Application Not Responding**
   - Verify app is running: `curl http://localhost:8000/health`
   - Check application logs for errors

### Debug Information:

- **View Environment Variables**: Click gear icon → select your environment
- **Check Console Logs**: Look at **Console** tab in Postman (bottom panel)
- **Inspect Headers**: Check **Headers** tab in response
- **View Raw Response**: Check **Body** tab → **Raw** for full response

### Redis Debugging:
```bash
# Connect to Redis container
docker exec -it redis-ai-companion redis-cli

# Check rate limit keys
KEYS rate:*

# Check quota keys  
KEYS quota:*

# View specific key with TTL
TTL rate:127.0.0.1:1705276800
GET quota:1:2024-01-15
```

## 🎯 Testing Tips

1. **Execute in Order**: Follow the phase sequence for best results
2. **Watch Console**: Postman console shows helpful debug info
3. **Check Headers**: Rate limit info is in response headers
4. **Time Sensitive**: Rate limit tests must be done within 1 minute
5. **Fresh Start**: Create new user for each test session to avoid quota conflicts

Happy Testing! 🚀