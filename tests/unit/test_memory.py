"""Unit tests for memory system."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from src.models.memory import MemoryType, ShortTermMemory, LongTermMemory


class TestMemoryManager:
    """Tests for MemoryManager class."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service."""
        service = AsyncMock()
        service.simple_chat = AsyncMock(return_value='{"extracted_info": [], "emotional_state": {}}')
        return service

    @pytest.fixture
    def memory_manager(self, mock_ai_service):
        """Create MemoryManager instance."""
        from src.services.memory import MemoryManager
        return MemoryManager(
            ai_service=mock_ai_service,
            cache_service=None,
            short_term_limit=10,
            consolidation_threshold=0.7,
        )

    def test_extract_keywords(self, memory_manager):
        """Test keyword extraction."""
        content = "我喜欢吃火锅和烧烤"
        keywords = memory_manager._extract_keywords(content)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_map_info_type(self, memory_manager):
        """Test info type mapping."""
        assert memory_manager._map_info_type("用户基本信息") == MemoryType.FACT.value
        assert memory_manager._map_info_type("用户偏好") == MemoryType.PREFERENCE.value
        assert memory_manager._map_info_type("重要事件") == MemoryType.EVENT.value
        assert memory_manager._map_info_type("未知类型") == MemoryType.CONTEXT.value

    def test_generate_memory_key(self, memory_manager):
        """Test memory key generation."""
        memory = MagicMock()
        memory.extracted_info = {"type": "food", "content": "喜欢火锅"}
        memory.memory_type = MemoryType.PREFERENCE.value
        memory.id = 1

        key = memory_manager._generate_memory_key(memory)
        assert "food" in key

    def test_parse_extraction_response_valid(self, memory_manager):
        """Test parsing valid extraction response."""
        response = '{"extracted_info": [{"type": "test", "content": "value"}]}'
        result = memory_manager._parse_extraction_response(response)
        assert result is not None
        assert "extracted_info" in result

    def test_parse_extraction_response_invalid(self, memory_manager):
        """Test parsing invalid extraction response."""
        response = "这不是JSON格式"
        result = memory_manager._parse_extraction_response(response)
        assert result is None


class TestMemoryModels:
    """Tests for memory data models."""

    def test_short_term_memory_creation(self):
        """Test ShortTermMemory model creation."""
        memory = ShortTermMemory(
            user_id=1,
            conversation_id=1,
            content="测试内容",
            memory_type=MemoryType.CONTEXT.value,
        )
        assert memory.user_id == 1
        assert memory.content == "测试内容"
        assert memory.relevance_score == 1.0

    def test_long_term_memory_creation(self):
        """Test LongTermMemory model creation."""
        memory = LongTermMemory(
            user_id=1,
            memory_type=MemoryType.FACT.value,
            key="name",
            value="张三",
        )
        assert memory.user_id == 1
        assert memory.key == "name"
        assert memory.value == "张三"
        assert memory.importance == 0.5
