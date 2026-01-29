"""Unit tests for utility functions."""

import pytest
from datetime import datetime

from src.utils.helpers import (
    generate_session_id,
    get_time_greeting,
    truncate_text,
    clean_message,
    calculate_typing_delay,
    mask_sensitive_info,
    format_duration,
)


class TestHelpers:
    """Tests for helper functions."""

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID format

        # Should generate unique IDs
        another_id = generate_session_id()
        assert session_id != another_id

    def test_get_time_greeting(self):
        """Test time-based greeting."""
        greeting = get_time_greeting()
        assert isinstance(greeting, str)
        assert greeting in ["早上好", "上午好", "中午好", "下午好", "晚上好", "夜深了"]

    def test_truncate_text_short(self):
        """Test truncating short text."""
        text = "短文本"
        result = truncate_text(text, max_length=100)
        assert result == text

    def test_truncate_text_long(self):
        """Test truncating long text."""
        text = "这是一段很长的文本" * 10
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_clean_message(self):
        """Test message cleaning."""
        text = "  多余   空格   的文本  "
        result = clean_message(text)
        assert result == "多余 空格 的文本"

    def test_calculate_typing_delay(self):
        """Test typing delay calculation."""
        short_text = "短"
        long_text = "这是一段很长的文本" * 20

        short_delay = calculate_typing_delay(short_text)
        long_delay = calculate_typing_delay(long_text)

        assert short_delay >= 0.5  # min delay
        assert long_delay <= 3.0  # max delay
        assert short_delay <= long_delay

    def test_mask_sensitive_info_phone(self):
        """Test phone number masking."""
        text = "我的电话是13812345678"
        result = mask_sensitive_info(text)
        assert "13812345678" not in result
        assert "1**********" in result

    def test_mask_sensitive_info_email(self):
        """Test email masking."""
        text = "邮箱是test@example.com"
        result = mask_sensitive_info(text)
        assert "test@example.com" not in result
        assert "***@***.***" in result

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        assert format_duration(30) == "30秒"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        assert format_duration(120) == "2分钟"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        assert format_duration(7200) == "2小时"

    def test_format_duration_days(self):
        """Test duration formatting for days."""
        assert format_duration(172800) == "2天"


class TestExceptions:
    """Tests for custom exceptions."""

    def test_aigf_exception(self):
        """Test base exception."""
        from src.utils.exceptions import AIGFException
        with pytest.raises(AIGFException):
            raise AIGFException("Test error")

    def test_ai_service_error(self):
        """Test AI service error."""
        from src.utils.exceptions import AIServiceError
        with pytest.raises(AIServiceError):
            raise AIServiceError("AI error")

    def test_memory_error(self):
        """Test memory error."""
        from src.utils.exceptions import MemoryError
        with pytest.raises(MemoryError):
            raise MemoryError("Memory error")

    def test_wechat_error(self):
        """Test WeChat error."""
        from src.utils.exceptions import WeChatError
        with pytest.raises(WeChatError):
            raise WeChatError("WeChat error")
