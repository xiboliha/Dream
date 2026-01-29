"""Integration tests for the conversation flow."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.conversation import Conversation, Message, MessageRole
from src.models.user import User


class TestConversationFlow:
    """Integration tests for conversation flow."""

    @pytest_asyncio.fixture
    async def mock_ai_service(self):
        """Create mock AI service."""
        service = AsyncMock()
        service.chat = AsyncMock(return_value=MagicMock(
            content="你好呀！今天过得怎么样？",
            total_tokens=50,
        ))
        service.simple_chat = AsyncMock(return_value='{"extracted_info": [], "emotional_state": {}}')
        service.close = AsyncMock()
        return service

    @pytest_asyncio.fixture
    async def conversation_engine(self, mock_ai_service):
        """Create conversation engine with mocked AI."""
        from src.services.memory import MemoryManager
        from src.core.conversation import ConversationEngine

        memory_manager = MemoryManager(
            ai_service=mock_ai_service,
            cache_service=None,
            short_term_limit=10,
            consolidation_threshold=0.7,
        )

        engine = ConversationEngine(
            ai_service=mock_ai_service,
            memory_manager=memory_manager,
            max_context_messages=10,
            response_timeout=30.0,
        )

        return engine

    @pytest.mark.asyncio
    async def test_create_conversation(self, db_session, conversation_engine):
        """Test creating a new conversation."""
        # Create test user first
        user = User(wechat_id="test_user_1", nickname="测试用户")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create conversation
        conversation = await conversation_engine.get_or_create_conversation(
            db_session, user.id
        )

        assert conversation is not None
        assert conversation.user_id == user.id
        assert conversation.session_id is not None

    @pytest.mark.asyncio
    async def test_add_message(self, db_session, conversation_engine):
        """Test adding messages to conversation."""
        # Create test user
        user = User(wechat_id="test_user_2", nickname="测试用户2")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create conversation
        conversation = await conversation_engine.get_or_create_conversation(
            db_session, user.id
        )

        # Add user message
        user_msg = await conversation_engine.add_message(
            db_session,
            conversation,
            role=MessageRole.USER.value,
            content="你好",
        )

        assert user_msg.id is not None
        assert user_msg.content == "你好"
        assert user_msg.role == MessageRole.USER.value

        # Add assistant message
        assistant_msg = await conversation_engine.add_message(
            db_session,
            conversation,
            role=MessageRole.ASSISTANT.value,
            content="你好呀！",
        )

        assert assistant_msg.id is not None
        assert assistant_msg.role == MessageRole.ASSISTANT.value

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, db_session, conversation_engine):
        """Test retrieving conversation history."""
        # Create test user
        user = User(wechat_id="test_user_3", nickname="测试用户3")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create conversation and add messages
        conversation = await conversation_engine.get_or_create_conversation(
            db_session, user.id
        )

        await conversation_engine.add_message(
            db_session, conversation, MessageRole.USER.value, "消息1"
        )
        await conversation_engine.add_message(
            db_session, conversation, MessageRole.ASSISTANT.value, "回复1"
        )
        await conversation_engine.add_message(
            db_session, conversation, MessageRole.USER.value, "消息2"
        )

        # Get history
        history = await conversation_engine.get_conversation_history(
            db_session, conversation, limit=10
        )

        assert len(history) == 3
        assert history[0].content == "消息1"
        assert history[1].content == "回复1"
        assert history[2].content == "消息2"

    @pytest.mark.asyncio
    async def test_process_message(self, db_session, conversation_engine):
        """Test full message processing flow."""
        # Create test user
        user = User(wechat_id="test_user_4", nickname="测试用户4")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Process message
        result = await conversation_engine.process_message(
            session=db_session,
            user_id=user.id,
            message_content="你好，我是小明",
            personality_config=None,
        )

        assert "response" in result
        assert result["response"] is not None
        assert "conversation_id" in result
        assert "session_id" in result


class TestEmotionIntegration:
    """Integration tests for emotion analysis."""

    def test_emotion_analysis_happy(self):
        """Test emotion analysis for happy messages."""
        from src.services.emotion import get_emotion_analyzer, EmotionType

        analyzer = get_emotion_analyzer()
        result = analyzer.analyze("今天太开心了！哈哈哈")

        assert result.primary_emotion == EmotionType.HAPPY
        assert result.intensity > 0.5

    def test_emotion_analysis_sad(self):
        """Test emotion analysis for sad messages."""
        from src.services.emotion import get_emotion_analyzer, EmotionType

        analyzer = get_emotion_analyzer()
        result = analyzer.analyze("好难过，想哭")

        assert result.primary_emotion == EmotionType.SAD
        assert result.intensity > 0.5

    def test_emotion_tracking(self):
        """Test emotion tracking over time."""
        from src.services.emotion import get_emotion_analyzer, get_emotion_tracker

        analyzer = get_emotion_analyzer()
        tracker = get_emotion_tracker()

        user_id = 999

        # Record multiple emotions
        messages = [
            "今天好开心",
            "有点累了",
            "还是很高兴",
            "哈哈哈太好笑了",
        ]

        for msg in messages:
            result = analyzer.analyze(msg)
            tracker.record(user_id, result)

        # Get trend
        trend = tracker.get_trend(user_id)
        assert trend["sample_size"] == 4
        assert trend["dominant_emotion"] is not None


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_content_filter_safe(self):
        """Test content filter with safe content."""
        from src.core.security import get_content_filter

        filter = get_content_filter()
        result = filter.filter_input("你好，今天天气真好")

        assert result.is_safe is True
        assert result.action == "allow"

    def test_content_filter_too_long(self):
        """Test content filter with too long content."""
        from src.core.security import get_content_filter

        filter = get_content_filter()
        long_content = "测试" * 2000
        result = filter.filter_input(long_content)

        assert result.is_safe is False
        assert result.action == "block"

    def test_rate_limiter(self):
        """Test rate limiter functionality."""
        from src.core.security import get_rate_limiter

        limiter = get_rate_limiter()
        user_id = 888

        # Reset user first
        limiter.reset_user(user_id)

        # First few requests should pass
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit(user_id)
            assert allowed is True


class TestRelationshipIntegration:
    """Integration tests for relationship system."""

    @pytest.mark.asyncio
    async def test_relationship_metrics(self, db_session):
        """Test relationship metrics tracking."""
        from src.core.relationship import get_relationship_builder, RelationshipStage
        from src.models.user import User

        # Create test user
        user = User(wechat_id="test_rel_user", nickname="关系测试用户")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        builder = get_relationship_builder()

        # Get initial metrics
        metrics = await builder.get_metrics(db_session, user.id)
        assert metrics.intimacy == 0.0
        assert metrics.get_stage() == RelationshipStage.STRANGER

        # Update metrics
        await builder.update_metrics(db_session, user.id, "message_received")
        await builder.update_metrics(db_session, user.id, "positive_emotion")

        # Check updated metrics
        metrics = await builder.get_metrics(db_session, user.id)
        assert metrics.intimacy > 0
        assert metrics.total_interactions == 2

    def test_stage_behaviors(self):
        """Test stage-specific behaviors."""
        from src.core.relationship import (
            get_relationship_builder,
            RelationshipMetrics,
            RelationshipStage,
        )

        builder = get_relationship_builder()

        # Test stranger stage
        stranger_metrics = RelationshipMetrics(intimacy=5)
        behaviors = builder.get_stage_behaviors(stranger_metrics)
        assert behaviors["formality"] == 0.7
        assert behaviors["pet_names"] is False

        # Test close friend stage
        close_metrics = RelationshipMetrics(intimacy=60)
        behaviors = builder.get_stage_behaviors(close_metrics)
        assert behaviors["formality"] == 0.2
        assert behaviors["pet_names"] is True


class TestPersonalityIntegration:
    """Integration tests for personality system."""

    def test_personality_loading(self):
        """Test personality configuration loading."""
        from src.core.personality import init_personality_system

        system = init_personality_system()
        personalities = system.list_personalities()

        # Should have loaded at least one personality
        assert len(personalities) > 0

    def test_personality_adaptation(self):
        """Test personality adaptation for users."""
        from src.core.personality import get_personality_system

        system = get_personality_system()
        user_id = 777

        # Get initial config
        config1 = system.get_personality_for_user(user_id)

        # Adapt personality
        system.adapt_to_user(user_id, "warmth", 0.1)
        system.adapt_to_user(user_id, "empathy", 0.1)

        # Get adapted config
        config2 = system.get_personality_for_user(user_id)

        # Traits should be slightly different
        if config1 and config2:
            assert config2["traits"]["warmth"] >= config1["traits"]["warmth"]
