"""CLI interface for testing the AI Girlfriend Agent without WeChat."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from config.settings import settings
from src.utils.logger import setup_logger
from src.services.storage import init_database, init_cache, close_database, close_cache
from src.services.ai import create_ai_service
from src.services.memory import MemoryManager
from src.core.conversation import ConversationEngine
from src.core.personality import init_personality_system
from src.core.coordinator import init_coordinator, MessageContext


class CLIChat:
    """Command-line interface for chatting with the AI girlfriend."""

    def __init__(self):
        self.conversation_engine = None
        self.coordinator = None
        self.user_id = 1  # Default test user
        self._running = False

    async def initialize(self) -> None:
        """Initialize all components."""
        print("正在初始化 AI 女友系统...")

        # Setup logging (minimal for CLI)
        setup_logger(log_level="WARNING")

        # Initialize database
        print("  - 初始化数据库...")
        init_database(
            database_url=settings.database_url,
            echo=False,
        )

        # Initialize cache
        print("  - 初始化缓存...")
        await init_cache(
            redis_url=settings.redis_url,
            redis_password=settings.redis_password,
        )

        # Initialize AI service
        print(f"  - 初始化 AI 服务 ({settings.ai_provider.value})...")
        ai_service = create_ai_service(
            provider=settings.ai_provider.value,
            api_key=settings.get_ai_api_key(),
            model=settings.get_ai_model(),
        )

        # Initialize personality system
        print("  - 初始化人格系统...")
        personality_system = init_personality_system()
        if personality_system.list_personalities():
            personality_system.set_current_personality(
                personality_system.list_personalities()[0]
            )

        # Initialize memory manager
        print("  - 初始化记忆系统...")
        from src.services.storage import get_cache_service
        memory_manager = MemoryManager(
            ai_service=ai_service,
            cache_service=get_cache_service(),
            short_term_limit=settings.short_term_memory_limit,
            consolidation_threshold=settings.long_term_memory_threshold,
        )

        # Initialize conversation engine
        print("  - 初始化对话引擎...")
        self.conversation_engine = ConversationEngine(
            ai_service=ai_service,
            memory_manager=memory_manager,
            max_context_messages=settings.max_context_messages,
            response_timeout=settings.response_timeout,
        )

        # Initialize coordinator
        print("  - 初始化协调器...")
        self.coordinator = init_coordinator(self.conversation_engine)

        # Create test user if needed
        await self._ensure_test_user()

        print("\n初始化完成！")

    async def _ensure_test_user(self) -> None:
        """Ensure test user exists in database."""
        from sqlalchemy import select
        from src.models.user import User
        from src.services.storage import get_database_service

        db = get_database_service()
        async with db.get_async_session() as session:
            result = await session.execute(
                select(User).where(User.id == self.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    wechat_id="cli_test_user",
                    nickname="测试用户",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                self.user_id = user.id

    async def chat(self, message: str) -> str:
        """Send a message and get response.

        Args:
            message: User message

        Returns:
            AI response
        """
        from src.services.storage import get_database_service
        from src.core.personality import get_personality_system

        db = get_database_service()
        async with db.get_async_session() as session:
            # Get personality config
            personality_system = get_personality_system()
            personality_config = personality_system.get_personality_for_user(self.user_id)

            # Process message
            result = await self.conversation_engine.process_message(
                session=session,
                user_id=self.user_id,
                message_content=message,
                personality_config=personality_config,
            )

            return result["response"]

    async def run_interactive(self) -> None:
        """Run interactive chat session."""
        self._running = True

        print("\n" + "=" * 50)
        print("AI 女友聊天系统 - CLI 测试模式")
        print("=" * 50)
        print("输入消息开始聊天，输入 'quit' 或 'exit' 退出")
        print("输入 'clear' 清除对话历史")
        print("输入 'status' 查看系统状态")
        print("=" * 50 + "\n")

        # Send initial greeting
        from src.services.storage import get_database_service
        db = get_database_service()
        async with db.get_async_session() as session:
            greeting = await self.conversation_engine.get_greeting(
                session=session,
                user_id=self.user_id,
            )
            print(f"小爱: {greeting}\n")

        while self._running:
            try:
                # Get user input
                user_input = input("你: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["quit", "exit", "退出"]:
                    print("\n再见，下次再聊哦~ 💕")
                    break

                if user_input.lower() == "clear":
                    print("对话历史已清除\n")
                    continue

                if user_input.lower() == "status":
                    await self._show_status()
                    continue

                # Get AI response
                print("小爱: ", end="", flush=True)
                response = await self.chat(user_input)
                print(f"{response}\n")

            except KeyboardInterrupt:
                print("\n\n收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"\n发生错误: {e}\n")

        self._running = False

    async def _show_status(self) -> None:
        """Show system status."""
        from src.services.storage import get_database_service
        from src.core.relationship import get_relationship_builder
        from src.services.emotion import get_emotion_tracker

        db = get_database_service()
        relationship_builder = get_relationship_builder()
        emotion_tracker = get_emotion_tracker()

        async with db.get_async_session() as session:
            metrics = await relationship_builder.get_metrics(session, self.user_id)
            emotion_trend = emotion_tracker.get_trend(self.user_id)

        print("\n" + "-" * 30)
        print("系统状态")
        print("-" * 30)
        print(f"用户ID: {self.user_id}")
        print(f"亲密度: {metrics.intimacy:.1f}/100")
        print(f"信任度: {metrics.trust:.1f}/100")
        print(f"关系阶段: {metrics.get_stage().value}")
        print(f"互动次数: {metrics.total_interactions}")
        print(f"连续天数: {metrics.consecutive_days}")
        if emotion_trend.get("dominant_emotion"):
            print(f"主要情绪: {emotion_trend['dominant_emotion']}")
        print("-" * 30 + "\n")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await close_cache()
        await close_database()


async def main():
    """Main entry point for CLI."""
    cli = CLIChat()

    try:
        await cli.initialize()
        await cli.run_interactive()
    except Exception as e:
        print(f"错误: {e}")
        raise
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
