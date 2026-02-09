"""Message buffer service for handling consecutive user messages."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class BufferedMessage:
    """A buffered message waiting to be processed."""
    content: str
    message_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserBuffer:
    """Buffer for a single user's messages."""
    messages: List[BufferedMessage] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    last_message_time: Optional[datetime] = None
    # Event to signal when processing is complete
    process_event: Optional[asyncio.Event] = None
    # Store the result after processing
    process_result: Optional[Dict[str, Any]] = None


class MessageBufferService:
    """Service for buffering consecutive user messages.

    When a user sends multiple messages quickly, this service buffers them
    and combines them into a single request after a short delay.
    """

    def __init__(
        self,
        buffer_timeout: float = 2.0,  # 等待时间（秒）
        max_buffer_size: int = 10,     # 最大缓冲消息数
        max_wait_time: float = 10.0,   # 最大等待时间（秒）
    ):
        """Initialize message buffer service.

        Args:
            buffer_timeout: Time to wait for more messages before processing (seconds)
            max_buffer_size: Maximum number of messages to buffer
            max_wait_time: Maximum time to wait before forcing processing
        """
        self.buffer_timeout = buffer_timeout
        self.max_buffer_size = max_buffer_size
        self.max_wait_time = max_wait_time

        # User buffers: user_id -> UserBuffer
        self._buffers: Dict[int, UserBuffer] = {}

        # Callback for processing messages
        self._process_callback: Optional[Callable] = None

        # Lock for thread safety
        self._locks: Dict[int, asyncio.Lock] = {}

    def _get_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create lock for user."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    def set_process_callback(self, callback: Callable) -> None:
        """Set callback for processing buffered messages.

        Args:
            callback: Async function(user_id, combined_message, message_type) -> response
        """
        self._process_callback = callback

    async def add_message(
        self,
        user_id: int,
        message: str,
        message_type: str = "text",
    ) -> Dict[str, Any]:
        """Add a message to the buffer.

        The first message will wait for the buffer timeout before processing.
        Subsequent messages within the timeout will be combined.

        Args:
            user_id: User ID
            message: Message content
            message_type: Type of message

        Returns:
            Dict with processing result
        """
        async with self._get_lock(user_id):
            # Get or create buffer for user
            if user_id not in self._buffers:
                self._buffers[user_id] = UserBuffer()

            buffer = self._buffers[user_id]
            now = datetime.utcnow()

            # Check if this is the first message (starting a new buffer session)
            is_first_message = len(buffer.messages) == 0

            # Add message to buffer
            buffer.messages.append(BufferedMessage(
                content=message,
                message_type=message_type,
                timestamp=now,
            ))
            buffer.last_message_time = now

            logger.debug(f"User {user_id}: Added message to buffer, count={len(buffer.messages)}")

            # Check if we should process immediately
            should_process_now = False

            # Force process if buffer is full
            if len(buffer.messages) >= self.max_buffer_size:
                should_process_now = True
                logger.debug(f"User {user_id}: Buffer full, processing immediately")

            # Force process if max wait time exceeded
            if len(buffer.messages) > 1:
                first_msg_time = buffer.messages[0].timestamp
                if (now - first_msg_time).total_seconds() >= self.max_wait_time:
                    should_process_now = True
                    logger.debug(f"User {user_id}: Max wait time exceeded, processing")

            if should_process_now:
                # Cancel existing timer
                if buffer.timer_task and not buffer.timer_task.done():
                    buffer.timer_task.cancel()

                # Process immediately
                return await self._process_buffer(user_id)

            if is_first_message:
                # First message: create event and start timer
                buffer.process_event = asyncio.Event()
                buffer.process_result = None

                # Start timer for processing
                buffer.timer_task = asyncio.create_task(
                    self._timer_callback(user_id)
                )

                logger.info(f"User {user_id}: First message, waiting {self.buffer_timeout}s for more...")

        # For first message: wait for processing to complete (outside lock)
        if is_first_message:
            # Wait for the timer to complete processing
            await buffer.process_event.wait()

            # Return the result
            result = buffer.process_result or {"status": "error", "message": "No result"}
            return result
        else:
            # Subsequent messages: just return buffered status
            # The first message's request will return the combined result
            async with self._get_lock(user_id):
                logger.info(f"User {user_id}: Buffered {len(buffer.messages)} messages")

                # Cancel and restart timer
                if buffer.timer_task and not buffer.timer_task.done():
                    buffer.timer_task.cancel()

                buffer.timer_task = asyncio.create_task(
                    self._timer_callback(user_id)
                )

            return {
                "status": "buffered",
                "message": f"已缓冲 {len(buffer.messages)} 条消息",
                "buffer_count": len(buffer.messages),
            }

    async def _timer_callback(self, user_id: int) -> None:
        """Timer callback to process buffer after timeout."""
        try:
            await asyncio.sleep(self.buffer_timeout)

            async with self._get_lock(user_id):
                if user_id in self._buffers and self._buffers[user_id].messages:
                    result = await self._process_buffer(user_id)

                    # Store result and signal completion
                    buffer = self._buffers[user_id]
                    buffer.process_result = result
                    if buffer.process_event:
                        buffer.process_event.set()

        except asyncio.CancelledError:
            # Timer was cancelled (new message arrived, timer restarted)
            pass
        except Exception as e:
            logger.error(f"Error in buffer timer for user {user_id}: {e}")
            # Signal error to waiting request
            if user_id in self._buffers:
                buffer = self._buffers[user_id]
                buffer.process_result = {"status": "error", "message": str(e)}
                if buffer.process_event:
                    buffer.process_event.set()

    async def _process_buffer(self, user_id: int) -> Dict[str, Any]:
        """Process all buffered messages for a user.

        Args:
            user_id: User ID

        Returns:
            Processing result
        """
        if user_id not in self._buffers:
            return {"status": "error", "message": "No buffer found"}

        buffer = self._buffers[user_id]

        if not buffer.messages:
            return {"status": "error", "message": "Buffer is empty"}

        # Combine messages
        messages = buffer.messages.copy()
        message_count = len(messages)

        # Clear buffer
        buffer.messages = []
        buffer.timer_task = None

        # Combine message contents
        if message_count == 1:
            combined_message = messages[0].content
        else:
            # Join multiple messages with newline
            combined_message = "\n".join(m.content for m in messages)
            logger.info(f"User {user_id}: Combined {message_count} messages into one")

        # Get message type (use first message's type)
        message_type = messages[0].message_type

        # Call process callback if set
        if self._process_callback:
            try:
                result = await self._process_callback(
                    user_id,
                    combined_message,
                    message_type,
                )
                result["buffered_count"] = message_count
                return result
            except Exception as e:
                logger.error(f"Error processing buffered messages: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "buffered_count": message_count,
                }

        return {
            "status": "processed",
            "combined_message": combined_message,
            "buffered_count": message_count,
        }

    async def flush_buffer(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Force process any buffered messages for a user.

        Args:
            user_id: User ID

        Returns:
            Processing result or None if no messages buffered
        """
        async with self._get_lock(user_id):
            if user_id not in self._buffers:
                return None

            buffer = self._buffers[user_id]

            # Cancel timer
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()

            if not buffer.messages:
                return None

            return await self._process_buffer(user_id)

    def get_buffer_status(self, user_id: int) -> Dict[str, Any]:
        """Get current buffer status for a user.

        Args:
            user_id: User ID

        Returns:
            Buffer status info
        """
        if user_id not in self._buffers:
            return {"buffered": False, "count": 0}

        buffer = self._buffers[user_id]
        return {
            "buffered": len(buffer.messages) > 0,
            "count": len(buffer.messages),
            "messages": [m.content for m in buffer.messages],
        }

    def clear_buffer(self, user_id: int) -> None:
        """Clear buffer for a user without processing.

        Args:
            user_id: User ID
        """
        if user_id in self._buffers:
            buffer = self._buffers[user_id]
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()
            buffer.messages = []
            buffer.timer_task = None
            if buffer.process_event:
                buffer.process_event.set()  # Unblock any waiting request


# Global instance
_message_buffer: Optional[MessageBufferService] = None


def get_message_buffer() -> MessageBufferService:
    """Get global message buffer service instance."""
    global _message_buffer
    if _message_buffer is None:
        _message_buffer = MessageBufferService()
    return _message_buffer


def init_message_buffer(
    buffer_timeout: float = 2.0,
    max_buffer_size: int = 10,
    max_wait_time: float = 10.0,
) -> MessageBufferService:
    """Initialize global message buffer service.

    Args:
        buffer_timeout: Time to wait for more messages
        max_buffer_size: Maximum messages to buffer
        max_wait_time: Maximum wait time before processing

    Returns:
        MessageBufferService instance
    """
    global _message_buffer
    _message_buffer = MessageBufferService(
        buffer_timeout=buffer_timeout,
        max_buffer_size=max_buffer_size,
        max_wait_time=max_wait_time,
    )
    return _message_buffer
