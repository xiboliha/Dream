"""WeChat client using itchat."""

import asyncio
import os
import threading
from typing import Any, Callable, Dict, Optional

from loguru import logger

try:
    import itchat
    from itchat.content import TEXT, PICTURE, RECORDING, VIDEO, ATTACHMENT
    ITCHAT_AVAILABLE = True
except ImportError:
    ITCHAT_AVAILABLE = False
    logger.warning("itchat not installed, WeChat functionality unavailable")


class WeChatClient:
    """WeChat client wrapper using itchat."""

    def __init__(
        self,
        hot_reload: bool = True,
        qr_path: str = "./data/cache/qr.png",
        status_storage_dir: str = "./data/cache/wechat",
    ):
        """Initialize WeChat client.

        Args:
            hot_reload: Enable hot reload for persistent login
            qr_path: Path to save QR code image
            status_storage_dir: Directory for status storage
        """
        if not ITCHAT_AVAILABLE:
            raise ImportError("itchat is required. Install with: pip install itchat-uos")

        self.hot_reload = hot_reload
        self.qr_path = qr_path
        self.status_storage_dir = status_storage_dir
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._message_handler: Optional[Callable] = None
        self._login_callback: Optional[Callable] = None
        self._logout_callback: Optional[Callable] = None

        # Ensure directories exist
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        os.makedirs(status_storage_dir, exist_ok=True)

    def set_message_handler(self, handler: Callable) -> None:
        """Set the message handler callback.

        Args:
            handler: Async function to handle messages
        """
        self._message_handler = handler

    def set_login_callback(self, callback: Callable) -> None:
        """Set login success callback."""
        self._login_callback = callback

    def set_logout_callback(self, callback: Callable) -> None:
        """Set logout callback."""
        self._logout_callback = callback

    def _register_handlers(self) -> None:
        """Register itchat message handlers."""

        @itchat.msg_register(TEXT)
        def handle_text(msg):
            """Handle text messages."""
            if self._message_handler and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_text_message(msg),
                    self._loop
                )

        @itchat.msg_register(PICTURE)
        def handle_picture(msg):
            """Handle picture messages."""
            if self._message_handler and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_image_message(msg),
                    self._loop
                )

        @itchat.msg_register(RECORDING)
        def handle_recording(msg):
            """Handle voice messages."""
            if self._message_handler and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_voice_message(msg),
                    self._loop
                )

    async def _process_text_message(self, msg: Dict[str, Any]) -> None:
        """Process incoming text message.

        Args:
            msg: itchat message dict
        """
        try:
            from_user = msg.get("User", {})
            wechat_id = from_user.get("UserName", "")
            nickname = from_user.get("NickName", "Unknown")
            content = msg.get("Text", "")
            msg_id = msg.get("MsgId", "")

            logger.info(f"Received text from {nickname}: {content[:50]}...")

            if self._message_handler:
                response = await self._message_handler.handle_text_message(
                    wechat_id=wechat_id,
                    nickname=nickname,
                    content=content,
                    msg_id=msg_id,
                )

                if response:
                    self.send_message(wechat_id, response)

        except Exception as e:
            logger.error(f"Error processing text message: {e}")

    async def _process_image_message(self, msg: Dict[str, Any]) -> None:
        """Process incoming image message.

        Args:
            msg: itchat message dict
        """
        try:
            from_user = msg.get("User", {})
            wechat_id = from_user.get("UserName", "")
            nickname = from_user.get("NickName", "Unknown")
            msg_id = msg.get("MsgId", "")

            # Download image
            image_path = os.path.join(self.status_storage_dir, f"{msg_id}.png")
            msg.download(image_path)

            logger.info(f"Received image from {nickname}")

            if self._message_handler:
                response = await self._message_handler.handle_image_message(
                    wechat_id=wechat_id,
                    nickname=nickname,
                    image_path=image_path,
                    msg_id=msg_id,
                )

                if response:
                    self.send_message(wechat_id, response)

        except Exception as e:
            logger.error(f"Error processing image message: {e}")

    async def _process_voice_message(self, msg: Dict[str, Any]) -> None:
        """Process incoming voice message.

        Args:
            msg: itchat message dict
        """
        try:
            from_user = msg.get("User", {})
            wechat_id = from_user.get("UserName", "")
            nickname = from_user.get("NickName", "Unknown")
            msg_id = msg.get("MsgId", "")

            # Download voice
            voice_path = os.path.join(self.status_storage_dir, f"{msg_id}.mp3")
            msg.download(voice_path)

            logger.info(f"Received voice from {nickname}")

            if self._message_handler:
                response = await self._message_handler.handle_voice_message(
                    wechat_id=wechat_id,
                    nickname=nickname,
                    voice_path=voice_path,
                    msg_id=msg_id,
                )

                if response:
                    self.send_message(wechat_id, response)

        except Exception as e:
            logger.error(f"Error processing voice message: {e}")

    def send_message(self, to_user: str, content: str) -> bool:
        """Send text message to user.

        Args:
            to_user: User's WeChat ID
            content: Message content

        Returns:
            True if sent successfully
        """
        try:
            itchat.send(content, toUserName=to_user)
            logger.info(f"Sent message to {to_user}: {content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_image(self, to_user: str, image_path: str) -> bool:
        """Send image to user.

        Args:
            to_user: User's WeChat ID
            image_path: Path to image file

        Returns:
            True if sent successfully
        """
        try:
            itchat.send_image(image_path, toUserName=to_user)
            logger.info(f"Sent image to {to_user}")
            return True
        except Exception as e:
            logger.error(f"Failed to send image: {e}")
            return False

    def get_friends(self) -> list:
        """Get list of friends."""
        return itchat.get_friends(update=True)

    def get_user_info(self, wechat_id: str) -> Optional[Dict[str, Any]]:
        """Get user information.

        Args:
            wechat_id: User's WeChat ID

        Returns:
            User info dict or None
        """
        try:
            return itchat.search_friends(userName=wechat_id)
        except Exception:
            return None

    def login(self, event_loop: asyncio.AbstractEventLoop) -> bool:
        """Login to WeChat.

        Args:
            event_loop: Asyncio event loop for callbacks

        Returns:
            True if login successful
        """
        self._loop = event_loop
        self._register_handlers()

        try:
            # Login with QR code
            itchat.auto_login(
                hotReload=self.hot_reload,
                statusStorageDir=self.status_storage_dir,
                qrCallback=self._qr_callback,
                loginCallback=self._on_login,
                exitCallback=self._on_logout,
            )

            logger.info("WeChat login successful")
            return True

        except Exception as e:
            logger.error(f"WeChat login failed: {e}")
            return False

    def _qr_callback(self, uuid: str, status: str, qrcode: bytes) -> None:
        """Handle QR code generation.

        Args:
            uuid: QR code UUID
            status: Login status
            qrcode: QR code image bytes
        """
        if status == "0":
            # Save QR code image
            with open(self.qr_path, "wb") as f:
                f.write(qrcode)
            logger.info(f"QR code saved to {self.qr_path}")
            print(f"\n请扫描二维码登录微信: {self.qr_path}\n")

    def _on_login(self) -> None:
        """Handle successful login."""
        logger.info("WeChat logged in successfully")
        if self._login_callback:
            self._login_callback()

    def _on_logout(self) -> None:
        """Handle logout."""
        logger.warning("WeChat logged out")
        self._running = False
        if self._logout_callback:
            self._logout_callback()

    def run(self) -> None:
        """Run the WeChat client (blocking)."""
        self._running = True
        logger.info("Starting WeChat client...")
        itchat.run(blockThread=True)

    def run_async(self) -> threading.Thread:
        """Run the WeChat client in a separate thread.

        Returns:
            Thread running the client
        """
        self._running = True
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("WeChat client started in background thread")
        return thread

    def stop(self) -> None:
        """Stop the WeChat client."""
        self._running = False
        try:
            itchat.logout()
            logger.info("WeChat client stopped")
        except Exception as e:
            logger.error(f"Error stopping WeChat client: {e}")

    @property
    def is_running(self) -> bool:
        """Check if client is running."""
        return self._running
