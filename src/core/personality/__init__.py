"""Personality module for AI Girlfriend Agent."""

from src.core.personality.system import (
    PersonalitySystem,
    PersonalityConfig,
    PersonalityTraits,
    LanguageStyle,
    get_personality_system,
    init_personality_system,
)

__all__ = [
    "PersonalitySystem",
    "PersonalityConfig",
    "PersonalityTraits",
    "LanguageStyle",
    "get_personality_system",
    "init_personality_system",
]
