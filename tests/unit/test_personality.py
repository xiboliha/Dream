"""Unit tests for personality system."""

import pytest
from pathlib import Path

from src.core.personality import (
    PersonalitySystem,
    PersonalityConfig,
    PersonalityTraits,
    LanguageStyle,
)


class TestPersonalityTraits:
    """Tests for PersonalityTraits model."""

    def test_default_traits(self):
        """Test default trait values."""
        traits = PersonalityTraits()
        assert 0 <= traits.warmth <= 1
        assert 0 <= traits.empathy <= 1
        assert 0 <= traits.playfulness <= 1

    def test_custom_traits(self):
        """Test custom trait values."""
        traits = PersonalityTraits(
            warmth=0.9,
            empathy=0.8,
            playfulness=0.3,
        )
        assert traits.warmth == 0.9
        assert traits.empathy == 0.8
        assert traits.playfulness == 0.3

    def test_trait_bounds(self):
        """Test trait value bounds."""
        with pytest.raises(ValueError):
            PersonalityTraits(warmth=1.5)
        with pytest.raises(ValueError):
            PersonalityTraits(empathy=-0.1)


class TestLanguageStyle:
    """Tests for LanguageStyle model."""

    def test_default_style(self):
        """Test default language style."""
        style = LanguageStyle()
        assert 0 <= style.formality <= 1
        assert 0 <= style.emoji_usage <= 1
        assert isinstance(style.pet_names, bool)

    def test_custom_style(self):
        """Test custom language style."""
        style = LanguageStyle(
            formality=0.8,
            emoji_usage=0.2,
            pet_names=False,
        )
        assert style.formality == 0.8
        assert style.emoji_usage == 0.2
        assert style.pet_names is False


class TestPersonalitySystem:
    """Tests for PersonalitySystem class."""

    @pytest.fixture
    def personality_system(self, tmp_path):
        """Create PersonalitySystem with temp config dir."""
        # Create a test personality config
        config_dir = tmp_path / "personalities"
        config_dir.mkdir()

        test_config = """
name: test_personality
display_name: 测试人格
description: 用于测试的人格配置

traits:
  warmth: 0.8
  empathy: 0.7
  playfulness: 0.6

language_style:
  formality: 0.4
  emoji_usage: 0.5
  pet_names: true

expressions:
  greetings:
    - "你好呀~"
    - "嗨~"
"""
        (config_dir / "test.yaml").write_text(test_config, encoding="utf-8")

        return PersonalitySystem(str(config_dir))

    def test_load_personalities(self, personality_system):
        """Test personality loading."""
        personalities = personality_system.list_personalities()
        assert "test_personality" in personalities

    def test_get_personality(self, personality_system):
        """Test getting personality by name."""
        personality = personality_system.get_personality("test_personality")
        assert personality is not None
        assert personality.name == "test_personality"
        assert personality.display_name == "测试人格"

    def test_get_nonexistent_personality(self, personality_system):
        """Test getting non-existent personality."""
        personality = personality_system.get_personality("nonexistent")
        assert personality is None

    def test_set_current_personality(self, personality_system):
        """Test setting current personality."""
        result = personality_system.set_current_personality("test_personality")
        assert result is True

        current = personality_system.get_current_personality()
        assert current.name == "test_personality"

    def test_get_expression(self, personality_system):
        """Test getting random expression."""
        personality_system.set_current_personality("test_personality")
        expression = personality_system.get_expression("greetings")
        assert expression in ["你好呀~", "嗨~"]

    def test_adapt_to_user(self, personality_system):
        """Test user adaptation."""
        user_id = 123
        personality_system.adapt_to_user(user_id, "warmth", 0.1)

        # Get adapted personality
        config = personality_system.get_personality_for_user(
            user_id, "test_personality"
        )
        # Adaptation should slightly increase warmth
        assert config["traits"]["warmth"] >= 0.8

    def test_should_use_emoji(self, personality_system):
        """Test emoji usage decision."""
        personality_system.set_current_personality("test_personality")
        # With 0.5 emoji_usage, should sometimes return True
        results = [personality_system.should_use_emoji() for _ in range(100)]
        assert True in results
        assert False in results
