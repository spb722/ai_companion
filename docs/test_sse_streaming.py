#!/usr/bin/env python3
"""
SSE (Server-Sent Events) Testing Utility for AI Companion Chat API

This script tests the streaming chat functionality comprehensively.
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestConfig:
    base_url: str = "http://localhost:8000"
    test_email: str = f"test_sse_{int(time.time())}@example.com"
    test_password: str = "TestPassword123!"
    character_id: Optional[int] = None
    access_token: Optional[str] = None


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def log_info(message: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def log_success(message: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def log_warning(message: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def log_error(message: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


class SSETestClient:
    def __init__(self, config: TestConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def register_user(self) -> bool:
        """Register a test user and get access token"""
        try:
            async with self.session.post(
                f"{self.config.base_url}/auth/register",
                json={
                    "email": self.config.test_email,
                    "password": self.config.test_password,
                    "preferred_language": "en"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.config.access_token = data["access_token"]
                    log_success(f"User registered: {self.config.test_email}")
                    return True
                else:
                    log_error(f"Registration failed: {response.status}")
                    return False
        except Exception as e:
            log_error(f"Registration error: {e}")
            return False

    async def get_characters(self) -> bool:
        """Get available characters and select the first one"""
        try:
            headers = {"Authorization": f"Bearer {self.config.access_token}"}
            async with self.session.get(
                f"{self.config.base_url}/characters",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["characters"]:
                        self.config.character_id = data["characters"][0]["id"]
                        character_name = data["characters"][0]["name"]
                        log_success(f"Selected character: {character_name} (ID: {self.config.character_id})")
                        return True
                    else:
                        log_error("No characters available")
                        return False
                else:
                    log_error(f"Failed to get characters: {response.status}")
                    return False
        except Exception as e:
            log_error(f"Character fetch error: {e}")
            return False

    async def select_character(self) -> bool:
        """Select the character for chat"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": "application/json"
            }
            async with self.session.post(
                f"{self.config.base_url}/api/v1/chat/switch-character",
                headers=headers,
                json={"character_id": self.config.character_id}
            ) as response:
                if response.status == 200:
                    log_success("Character selected successfully")
                    return True
                else:
                    log_error(f"Character selection failed: {response.status}")
                    return False
        except Exception as e:
            log_error(f"Character selection error: {e}")
            return False

    async def test_sse_stream(self, message: str, test_name: str) -> Dict[str, Any]:
        """Test SSE streaming with a specific message"""
        log_info(f"Testing SSE stream: {test_name}")
        
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        payload = {
            "message": message,
            "stream": True
        }

        events = []
        content_chunks = []
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.config.base_url}/api/v1/chat/send",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    log_error(f"HTTP Error: {response.status}")
                    error_text = await response.text()
                    log_error(f"Error response: {error_text}")
                    return {"success": False, "error": f"HTTP {response.status}"}

                log_success(f"SSE connection established (HTTP {response.status})")
                
                # Verify SSE headers
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' not in content_type:
                    log_warning(f"Unexpected content-type: {content_type}")
                else:
                    log_success("Correct SSE content-type header")

                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if not line_str:
                        continue
                    
                    if line_str.startswith('event: '):
                        current_event = line_str[7:]
                    elif line_str.startswith('data: '):
                        data_str = line_str[6:]
                        try:
                            data = json.loads(data_str)
                            events.append(data)
                            
                            event_type = data.get('type', 'unknown')
                            print(f"  📡 {event_type}: ", end="")
                            
                            if event_type == 'metadata':
                                print(f"Conversation {data.get('conversation_id')}, Provider: {data.get('provider')}")
                            elif event_type == 'content':
                                content = data.get('content', '')
                                content_chunks.append(content)
                                print(f"'{content}'")
                            elif event_type == 'complete':
                                duration = data.get('duration_seconds', 0)
                                print(f"Duration: {duration}s")
                            elif event_type == 'error':
                                print(f"ERROR: {data.get('error', 'Unknown error')}")
                                
                        except json.JSONDecodeError as e:
                            log_warning(f"Invalid JSON in SSE data: {data_str[:100]}...")
                    elif line_str.startswith(':'):
                        # Heartbeat or comment
                        print(f"  💓 Heartbeat: {line_str}")

                end_time = time.time()
                total_duration = end_time - start_time
                
                # Analyze results
                full_content = ''.join(content_chunks)
                
                result = {
                    "success": True,
                    "test_name": test_name,
                    "message": message,
                    "total_events": len(events),
                    "content_chunks": len(content_chunks),
                    "full_content": full_content,
                    "total_duration": total_duration,
                    "events": events
                }
                
                log_success(f"SSE test completed: {len(events)} events, {len(content_chunks)} content chunks")
                log_info(f"Full response: {full_content[:100]}...")
                log_info(f"Total duration: {total_duration:.2f}s")
                
                return result

        except Exception as e:
            log_error(f"SSE stream error: {e}")
            return {"success": False, "error": str(e)}

    async def test_concurrent_streams(self, num_streams: int = 3) -> bool:
        """Test multiple concurrent SSE streams"""
        log_info(f"Testing {num_streams} concurrent SSE streams")
        
        messages = [
            "Tell me a very short joke",
            "What's 2+2?",
            "Say hello in French"
        ]
        
        tasks = []
        for i in range(min(num_streams, len(messages))):
            task = self.test_sse_stream(
                messages[i],
                f"Concurrent Test {i+1}"
            )
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            log_info(f"Concurrent streams: {successful}/{len(results)} successful")
            
            return successful == len(results)
            
        except Exception as e:
            log_error(f"Concurrent stream test error: {e}")
            return False

    async def test_sse_error_handling(self) -> bool:
        """Test SSE error scenarios"""
        log_info("Testing SSE error handling")
        
        # Test without character selection (should fail gracefully)
        # First, clear character selection by selecting invalid character
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        payload = {
            "message": "This should fail gracefully",
            "stream": True
        }

        try:
            # Use invalid character first
            await self.session.post(
                f"{self.config.base_url}/api/v1/chat/switch-character",
                headers={"Authorization": f"Bearer {self.config.access_token}", "Content-Type": "application/json"},
                json={"character_id": 999}
            )
            
            # Now try to chat - should fail gracefully
            async with self.session.post(
                f"{self.config.base_url}/api/v1/chat/send",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status == 400:
                    log_success("Error handling: Correctly rejected invalid character")
                    return True
                else:
                    log_warning(f"Unexpected response for error case: {response.status}")
                    return False
                    
        except Exception as e:
            log_error(f"Error handling test failed: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run comprehensive SSE test suite"""
        log_info("Starting SSE Testing Suite")
        log_info(f"Base URL: {self.config.base_url}")
        
        # Setup
        if not await self.register_user():
            return False
            
        if not await self.get_characters():
            return False
            
        if not await self.select_character():
            return False

        # Test cases
        test_cases = [
            ("Hello! Please respond briefly.", "Basic SSE Test"),
            ("Tell me a very short story about a cat.", "Short Story Test"),
            ("What is 1+1? Answer in one word.", "Simple Math Test"),
            ("Translate 'hello' to Spanish.", "Translation Test")
        ]

        success_count = 0
        total_tests = len(test_cases) + 2  # +2 for concurrent and error tests

        # Individual SSE tests
        for message, test_name in test_cases:
            result = await self.test_sse_stream(message, test_name)
            if result.get("success"):
                success_count += 1
            await asyncio.sleep(1)  # Brief pause between tests

        # Concurrent streams test
        if await self.test_concurrent_streams():
            success_count += 1

        # Error handling test
        if await self.test_sse_error_handling():
            success_count += 1

        log_info(f"SSE Test Results: {success_count}/{total_tests} tests passed")
        
        if success_count == total_tests:
            log_success("All SSE tests passed!")
            return True
        else:
            log_warning(f"Some tests failed: {total_tests - success_count} failures")
            return False


async def main():
    """Main test execution"""
    config = TestConfig()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        config.base_url = sys.argv[1]
    
    log_info(f"SSE Testing Utility - AI Companion Chat API")
    log_info(f"Target: {config.base_url}")
    
    async with SSETestClient(config) as client:
        success = await client.run_all_tests()
        
        if success:
            log_success("🎉 All SSE tests completed successfully!")
            sys.exit(0)
        else:
            log_error("❌ Some SSE tests failed!")
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)