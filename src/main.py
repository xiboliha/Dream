"""Main application entry point for AI Girlfriend Agent."""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.utils.logger import setup_logger
from src.services.storage import init_database, init_cache, close_database, close_cache
from src.services.ai import create_ai_service
from src.services.memory import MemoryManager
from src.core.conversation import ConversationEngine
from src.core.personality import init_personality_system
from src.interfaces.wechat import WeChatClient, WeChatHandler


class AIGirlfriendApp:
    """Main application class for AI Girlfriend Agent."""

    def __init__(self):
        """Initialize the application."""
        self.wechat_client = None
        self.wechat_handler = None
        self.conversation_engine = None
        self.memory_manager = None
        self.ai_service = None
        self._running = False
        self._loop = None

    async def initialize(self) -> None:
        """Initialize all services and components."""
        logger.info("Initializing AI Girlfriend Agent...")

        # Setup logging
        setup_logger(
            log_level=settings.log_level,
            log_dir=settings.log_dir,
        )

        # Initialize database
        logger.info("Initializing database...")
        init_database(
            database_url=settings.database_url,
            echo=settings.database_echo,
        )

        # Initialize cache
        logger.info("Initializing cache...")
        await init_cache(
            redis_url=settings.redis_url,
            redis_password=settings.redis_password,
        )

        # Initialize AI service
        logger.info(f"Initializing AI service ({settings.ai_provider.value})...")
        self.ai_service = create_ai_service(
            provider=settings.ai_provider.value,
            api_key=settings.get_ai_api_key(),
            model=settings.get_ai_model(),
        )

        # Initialize personality system
        logger.info("Initializing personality system...")
        personality_system = init_personality_system()
        if personality_system.list_personalities():
            personality_system.set_current_personality(
                personality_system.list_personalities()[0]
            )

        # Initialize memory manager
        logger.info("Initializing memory manager...")
        from src.services.storage import get_cache_service
        self.memory_manager = MemoryManager(
            ai_service=self.ai_service,
            cache_service=get_cache_service(),
            short_term_limit=settings.short_term_memory_limit,
            consolidation_threshold=settings.long_term_memory_threshold,
        )

        # Initialize conversation engine
        logger.info("Initializing conversation engine...")
        self.conversation_engine = ConversationEngine(
            ai_service=self.ai_service,
            memory_manager=self.memory_manager,
            max_context_messages=settings.max_context_messages,
            response_timeout=settings.response_timeout,
        )

        # Initialize WeChat handler
        logger.info("Initializing WeChat handler...")
        self.wechat_handler = WeChatHandler(
            conversation_engine=self.conversation_engine,
        )

        # Initialize WeChat client
        logger.info("Initializing WeChat client...")
        self.wechat_client = WeChatClient(
            hot_reload=settings.wechat_hot_reload,
            qr_path=settings.wechat_qr_path,
            status_storage_dir=settings.wechat_status_storage_dir,
        )
        self.wechat_client.set_message_handler(self.wechat_handler)

        logger.info("All components initialized successfully!")

    async def start(self) -> None:
        """Start the application."""
        self._running = True
        self._loop = asyncio.get_event_loop()

        logger.info("Starting AI Girlfriend Agent...")

        # Login to WeChat
        logger.info("Logging in to WeChat...")
        if not self.wechat_client.login(self._loop):
            logger.error("Failed to login to WeChat")
            return

        # Run WeChat client in background
        wechat_thread = self.wechat_client.run_async()

        logger.info("AI Girlfriend Agent is now running!")
        logger.info("Press Ctrl+C to stop")

        # Keep running until stopped
        try:
            while self._running and wechat_thread.is_alive():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop the application."""
        logger.info("Stopping AI Girlfriend Agent...")
        self._running = False

        # Stop WeChat client
        if self.wechat_client:
            self.wechat_client.stop()

        # Close AI service
        if self.ai_service:
            await self.ai_service.close()

        # Close cache
        await close_cache()

        # Close database
        await close_database()

        logger.info("AI Girlfriend Agent stopped")

    def handle_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False


async def main() -> None:
    """Main entry point."""
    app = AIGirlfriendApp()

    # Setup signal handlers
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)

    try:
        await app.initialize()
        await app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
