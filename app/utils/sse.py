"""
Server-Sent Events (SSE) utility for formatting and streaming responses
"""

import json
import asyncio
import logging
from typing import Any, Dict, Optional, AsyncGenerator

logger = logging.getLogger(__name__)


def format_sse(
    data: Any,
    event: Optional[str] = None,
    id: Optional[str] = None
) -> str:
    """
    Format data as Server-Sent Events (SSE) string.
    
    Args:
        data: Data to send (will be JSON serialized)
        event: Optional event type
        id: Optional event ID
        
    Returns:
        str: Properly formatted SSE string
    """
    lines = []
    
    # Add event type if provided
    if event:
        lines.append(f"event: {event}")
    
    # Add event ID if provided
    if id:
        lines.append(f"id: {id}")
    
    # Add data (JSON serialize if not string)
    if isinstance(data, str):
        lines.append(f"data: {data}")
    else:
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            lines.append(f"data: {json_data}")
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize SSE data: {e}")
            lines.append(f"data: {{'error': 'Serialization failed'}}")
    
    # SSE format requires double newline at end
    return "\n".join(lines) + "\n\n"


def format_heartbeat() -> str:
    """
    Create a heartbeat ping to keep SSE connection alive.
    
    Returns:
        str: SSE heartbeat string
    """
    return ":ping\n\n"


def format_error_sse(
    error_message: str,
    error_code: Optional[str] = None,
    event_id: Optional[str] = None
) -> str:
    """
    Format error as SSE event.
    
    Args:
        error_message: Error message
        error_code: Optional error code
        event_id: Optional event ID
        
    Returns:
        str: Formatted error SSE string
    """
    error_data = {
        "type": "error",
        "error": error_message
    }
    
    if error_code:
        error_data["code"] = error_code
    
    return format_sse(error_data, event="error", id=event_id)


async def sse_generator(
    message_stream: AsyncGenerator[Dict[str, Any], None],
    heartbeat_interval: int = 15
) -> AsyncGenerator[str, None]:
    """
    Generate SSE formatted events from message stream with heartbeat.
    
    Args:
        message_stream: Async generator of message dictionaries
        heartbeat_interval: Seconds between heartbeat pings (default: 15)
        
    Yields:
        str: SSE formatted strings
    """
    last_heartbeat = asyncio.get_event_loop().time()
    
    try:
        async for message in message_stream:
            current_time = asyncio.get_event_loop().time()
            
            # Send heartbeat if needed
            if current_time - last_heartbeat >= heartbeat_interval:
                yield format_heartbeat()
                last_heartbeat = current_time
            
            # Determine event type
            event_type = message.get("type", "message")
            event_id = message.get("id")
            
            # Format and yield the message
            sse_message = format_sse(message, event=event_type, id=event_id)
            yield sse_message
            
            # Check if this is an error or completion event
            if event_type in ["error", "complete"]:
                break
                
    except Exception as e:
        logger.error(f"Error in SSE generator: {e}")
        # Send error event
        error_sse = format_error_sse(
            "Stream processing error occurred",
            "STREAM_ERROR"
        )
        yield error_sse


async def sse_chat_generator(
    message_stream: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[str, None]:
    """
    Specialized SSE generator for chat messages with appropriate event types.
    
    Args:
        message_stream: Async generator of chat message dictionaries
        
    Yields:
        str: SSE formatted chat messages
    """
    try:
        async for chunk in message_stream:
            chunk_type = chunk.get("type", "unknown")
            
            # Map chunk types to SSE event names
            event_name = None
            if chunk_type == "metadata":
                event_name = "chat-start"
            elif chunk_type == "content":
                event_name = "chat-content"
            elif chunk_type == "complete":
                event_name = "chat-complete"
            elif chunk_type == "error":
                event_name = "chat-error"
            
            # Format and yield SSE message
            sse_message = format_sse(chunk, event=event_name)
            yield sse_message
            
            # Add small delay for better streaming UX
            await asyncio.sleep(0.01)
            
            # Break on completion or error
            if chunk_type in ["complete", "error"]:
                break
                
    except Exception as e:
        logger.error(f"Error in chat SSE generator: {e}")
        error_sse = format_error_sse(
            "Chat stream error occurred",
            "CHAT_STREAM_ERROR"
        )
        yield error_sse


def create_sse_headers() -> Dict[str, str]:
    """
    Create appropriate headers for SSE response.
    
    Returns:
        Dict[str, str]: Headers dictionary for SSE
    """
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }


async def test_sse_format() -> None:
    """Test function to verify SSE formatting works correctly"""
    # Test basic SSE formatting
    basic_sse = format_sse({"message": "Hello, World!"})
    print("Basic SSE:", repr(basic_sse))
    
    # Test SSE with event and ID
    event_sse = format_sse(
        {"type": "test", "data": "Test data"},
        event="test-event",
        id="123"
    )
    print("Event SSE:", repr(event_sse))
    
    # Test heartbeat
    heartbeat = format_heartbeat()
    print("Heartbeat:", repr(heartbeat))
    
    # Test error format
    error_sse = format_error_sse("Test error", "TEST_ERROR", "error-123")
    print("Error SSE:", repr(error_sse))


if __name__ == "__main__":
    # Run test when script is executed directly
    asyncio.run(test_sse_format())