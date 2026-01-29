"""WeChat message handler for processing incoming messages."""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from loguru import logger

from src.core.conversation import ConversationEngine
from src.core.personality import get_personality_system
from src.services.storage import get_database_service
from src.utils.helpers import calculate_typing_delay


class WeChatHandler:
    """Handler for WeChat messages."""

    def __init__(
        self,
        conversation_engine: ConversationEngine,
        on_response: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize WeChat handler.

        Args:
            conversation_engine: Conversation engine for generating responses
            on_response: Callback for sending responses
        """
        self.conversation_engine = conversation_engine
        self.on_response = on_response
        self._user_cache: Dict[str, int] = {}  # wechat_id -> user_id mapping
        self._processing: Dict[str, bool] = {}  # Track processing status

    async def handle_text_message(
        self,
        wechat_id: str,
        nickname: str,
        content: str,
        msg_id: str,
    ) -> Optional[str]:
        """Handle incoming text message.

        Args:
            wechat_id: WeChat user ID
            nickname: User's nickname
            content: Message content
            msg_id: Message ID

        Returns:
            Response text or None
        """
        # Prevent duplicate processing
        if self._processing.get(msg_id):
            logger.warning(f"Message {msg_id} already being processed")
            return None

        self._processing[msg_id] = True

        try:
            # Get or create user
            user_id = await self._get_or_create_user(wechat_id, nickname)

            # Get personality config
            personality_system = get_personality_system()
            personality_config = personality_system.get_personality_for_user(user_id)

            # Process message
            db = get_database_service()
            async with db.get_async_session() as session:
                result = await self.conversation_engine.process_message(
                    session=session,
                    user_id=user_id,
                    message_content=content,
                    personality_config=personality_config,
                )

            response = result["response"]
            typing_delay = result.get("typing_delay", 1.0)

            # Simulate typing delay
            await asyncio.sleep(min(typing_delay, 3.0))

            logger.info(f"Generated response for {nickname}: {response[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Error handling message from {nickname}: {e}")
            return "抱歉，我好像遇到了一点问题，稍后再聊好吗？"

        finally:
            self._processing.pop(msg_id, None)

    async def handle_image_message(
        self,
        wechat_id: str,
        nickname: str,
        image_path: str,
        msg_id: str,
    ) -> Optional[str]:
        """Handle incoming image message.

        Args:
            wechat_id: WeChat user ID
            nickname: User's nickname
            image_path: Path to downloaded image
            msg_id: Message ID

        Returns:
            Response text or None
        """
        # For now, just acknowledge the image
        responses = [
            "哇，这张图片好有意思！",
            "收到图片啦~",
            "让我看看这是什么~",
            "好看！",
        ]
        import random
        return random.choice(responses)

    async def handle_voice_message(
        self,
        wechat_id: str,
        nickname: str,
        voice_path: str,
        msg_id: str,
    ) -> Optional[str]:
        """Handle incoming voice message.

        Args:
            wechat_id: WeChat user ID
            nickname: User's nickname
            voice_path: Path to downloaded voice
            msg_id: Message ID

        Returns:
            Response text or None
        """
        return "收到语音啦，不过我现在还不太会听语音，能打字告诉我吗？"

    async def _get_or_create_user(
        self,
        wechat_id: str,
        nickname: str,
    ) -> int:
        """Get or create user in database.

        Args:
            wechat_id: WeChat user ID
            nickname: User's nickname

        Returns:
            User ID
        """
        # Check cache first
        if wechat_id in self._user_cache:
            return self._user_cache[wechat_id]

        from sqlalchemy import select
        from src.models.user import User

        db = get_database_service()
        async with db.get_async_session() as session:
            # Try to find existing user
            result = await session.execute(
                select(User).where(User.wechat_id == wechat_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                # Create new user
                user = User(
                    wechat_id=wechat_id,
                    nickname=nickname,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"Created new user: {nickname} ({wechat_id})")

            self._user_cache[wechat_id] = user.id
            return user.id

    async def send_greeting(
        self,
        wechat_id: str,
        nickname: str,
    ) -> Optional[str]:
        """Send a greeting message to user.

        Args:
            wechat_id: WeChat user ID
            nickname: User's nickname

        Returns:
            Greeting message
        """
        try:
            user_id = await self._get_or_create_user(wechat_id, nickname)

            db = get_database_service()
            async with db.get_async_session() as session:
                personality_system = get_personality_system()
                personality_config = personality_system.get_personality_for_user(user_id)

                greeting = await self.conversation_engine.get_greeting(
                    session=session,
                    user_id=user_id,
                    personality_config=personality_config,
                )

            return greeting

        except Exception as e:
            logger.error(f"Error generating greeting for {nickname}: {e}")
            return None
