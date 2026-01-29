"""Personality system for managing AI character traits."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger
from pydantic import BaseModel, Field


class PersonalityTraits(BaseModel):
    """Personality trait configuration."""
    warmth: float = Field(default=0.7, ge=0, le=1)
    empathy: float = Field(default=0.7, ge=0, le=1)
    patience: float = Field(default=0.7, ge=0, le=1)
    playfulness: float = Field(default=0.5, ge=0, le=1)
    intellectuality: float = Field(default=0.5, ge=0, le=1)
    assertiveness: float = Field(default=0.5, ge=0, le=1)
    sensitivity: float = Field(default=0.7, ge=0, le=1)
    humor: float = Field(default=0.5, ge=0, le=1)


class LanguageStyle(BaseModel):
    """Language style configuration."""
    formality: float = Field(default=0.4, ge=0, le=1)
    verbosity: float = Field(default=0.6, ge=0, le=1)
    emoji_usage: float = Field(default=0.6, ge=0, le=1)
    pet_names: bool = True


class EmotionalResponse(BaseModel):
    """Emotional response configuration."""
    intensity_multiplier: float = 1.0
    response_style: str = "default"


class PersonalityConfig(BaseModel):
    """Complete personality configuration."""
    name: str
    display_name: str
    description: str = ""
    traits: PersonalityTraits = Field(default_factory=PersonalityTraits)
    language_style: LanguageStyle = Field(default_factory=LanguageStyle)
    expressions: Dict[str, List[str]] = Field(default_factory=dict)
    emotional_responses: Dict[str, EmotionalResponse] = Field(default_factory=dict)
    topic_preferences: Dict[str, List[str]] = Field(default_factory=dict)
    behavior_patterns: Dict[str, bool] = Field(default_factory=dict)


class PersonalitySystem:
    """System for managing and evolving AI personality."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize personality system.

        Args:
            config_dir: Directory containing personality configs
        """
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "config", "personalities"
            )
        self.config_dir = Path(config_dir)
        self._personalities: Dict[str, PersonalityConfig] = {}
        self._current_personality: Optional[str] = None
        self._user_adaptations: Dict[int, Dict[str, float]] = {}

        self._load_personalities()

    def _load_personalities(self) -> None:
        """Load all personality configurations from files."""
        if not self.config_dir.exists():
            logger.warning(f"Personality config directory not found: {self.config_dir}")
            return

        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data:
                    # Parse traits
                    if "traits" in data:
                        data["traits"] = PersonalityTraits(**data["traits"])

                    # Parse language style
                    if "language_style" in data:
                        data["language_style"] = LanguageStyle(**data["language_style"])

                    # Parse emotional responses
                    if "emotional_responses" in data:
                        data["emotional_responses"] = {
                            k: EmotionalResponse(**v) if isinstance(v, dict) else EmotionalResponse()
                            for k, v in data["emotional_responses"].items()
                        }

                    config = PersonalityConfig(**data)
                    self._personalities[config.name] = config
                    logger.info(f"Loaded personality: {config.name} ({config.display_name})")

            except Exception as e:
                logger.error(f"Failed to load personality from {config_file}: {e}")

    def get_personality(self, name: str) -> Optional[PersonalityConfig]:
        """Get personality configuration by name.

        Args:
            name: Personality name

        Returns:
            PersonalityConfig or None
        """
        return self._personalities.get(name)

    def list_personalities(self) -> List[str]:
        """List available personality names."""
        return list(self._personalities.keys())

    def set_current_personality(self, name: str) -> bool:
        """Set the current active personality.

        Args:
            name: Personality name

        Returns:
            True if successful
        """
        if name in self._personalities:
            self._current_personality = name
            logger.info(f"Set current personality to: {name}")
            return True
        logger.warning(f"Personality not found: {name}")
        return False

    def get_current_personality(self) -> Optional[PersonalityConfig]:
        """Get the current active personality."""
        if self._current_personality:
            return self._personalities.get(self._current_personality)
        # Return first available personality as default
        if self._personalities:
            return next(iter(self._personalities.values()))
        return None

    def get_personality_for_user(
        self,
        user_id: int,
        base_personality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get personality configuration adapted for specific user.

        Args:
            user_id: User ID
            base_personality: Base personality name

        Returns:
            Adapted personality configuration dict
        """
        # Get base personality
        if base_personality:
            personality = self.get_personality(base_personality)
        else:
            personality = self.get_current_personality()

        if not personality:
            return {}

        # Convert to dict
        config = personality.model_dump()

        # Apply user-specific adaptations
        if user_id in self._user_adaptations:
            adaptations = self._user_adaptations[user_id]
            for trait, adjustment in adaptations.items():
                if trait in config.get("traits", {}):
                    original = config["traits"][trait]
                    config["traits"][trait] = max(0, min(1, original + adjustment))

        return config

    def adapt_to_user(
        self,
        user_id: int,
        trait: str,
        adjustment: float,
    ) -> None:
        """Adapt personality trait for specific user.

        Args:
            user_id: User ID
            trait: Trait name to adjust
            adjustment: Adjustment value (-1 to 1)
        """
        if user_id not in self._user_adaptations:
            self._user_adaptations[user_id] = {}

        current = self._user_adaptations[user_id].get(trait, 0)
        # Gradual adjustment with decay
        new_value = current * 0.9 + adjustment * 0.1
        self._user_adaptations[user_id][trait] = max(-0.3, min(0.3, new_value))

        logger.debug(f"Adapted {trait} for user {user_id}: {new_value:.3f}")

    def get_expression(
        self,
        category: str,
        personality_name: Optional[str] = None,
    ) -> Optional[str]:
        """Get a random expression from category.

        Args:
            category: Expression category (greetings, affirmations, etc.)
            personality_name: Optional specific personality

        Returns:
            Random expression or None
        """
        import random

        if personality_name:
            personality = self.get_personality(personality_name)
        else:
            personality = self.get_current_personality()

        if not personality:
            return None

        expressions = personality.expressions.get(category, [])
        if expressions:
            return random.choice(expressions)
        return None

    def get_emotional_response_style(
        self,
        emotion: str,
        personality_name: Optional[str] = None,
    ) -> EmotionalResponse:
        """Get emotional response configuration.

        Args:
            emotion: Detected emotion
            personality_name: Optional specific personality

        Returns:
            EmotionalResponse configuration
        """
        if personality_name:
            personality = self.get_personality(personality_name)
        else:
            personality = self.get_current_personality()

        if personality and emotion in personality.emotional_responses:
            return personality.emotional_responses[emotion]

        return EmotionalResponse()

    def should_use_emoji(self, personality_name: Optional[str] = None) -> bool:
        """Check if emoji should be used based on personality.

        Args:
            personality_name: Optional specific personality

        Returns:
            True if emoji should be used
        """
        import random

        if personality_name:
            personality = self.get_personality(personality_name)
        else:
            personality = self.get_current_personality()

        if personality:
            return random.random() < personality.language_style.emoji_usage
        return False

    def get_topic_preference(
        self,
        topic: str,
        personality_name: Optional[str] = None,
    ) -> str:
        """Get preference level for a topic.

        Args:
            topic: Topic to check
            personality_name: Optional specific personality

        Returns:
            'preferred', 'neutral', or 'avoided'
        """
        if personality_name:
            personality = self.get_personality(personality_name)
        else:
            personality = self.get_current_personality()

        if not personality:
            return "neutral"

        prefs = personality.topic_preferences
        if topic in prefs.get("preferred", []):
            return "preferred"
        elif topic in prefs.get("avoided", []):
            return "avoided"
        return "neutral"

    def evolve_personality(
        self,
        user_id: int,
        interaction_data: Dict[str, Any],
    ) -> None:
        """Evolve personality based on interaction data.

        Args:
            user_id: User ID
            interaction_data: Data about the interaction
        """
        # Analyze interaction and adjust traits
        user_emotion = interaction_data.get("user_emotion")
        response_received_well = interaction_data.get("positive_feedback", False)
        topic = interaction_data.get("topic")

        if user_emotion == "happy" and response_received_well:
            # Reinforce current style
            pass
        elif user_emotion == "sad":
            # Increase empathy for this user
            self.adapt_to_user(user_id, "empathy", 0.05)
            self.adapt_to_user(user_id, "warmth", 0.03)
        elif user_emotion == "angry":
            # Increase patience, decrease assertiveness
            self.adapt_to_user(user_id, "patience", 0.05)
            self.adapt_to_user(user_id, "assertiveness", -0.03)

        logger.debug(f"Evolved personality for user {user_id} based on {user_emotion}")


# Global personality system instance
_personality_system: Optional[PersonalitySystem] = None


def get_personality_system() -> PersonalitySystem:
    """Get the global personality system instance."""
    global _personality_system
    if _personality_system is None:
        _personality_system = PersonalitySystem()
    return _personality_system


def init_personality_system(config_dir: Optional[str] = None) -> PersonalitySystem:
    """Initialize the global personality system."""
    global _personality_system
    _personality_system = PersonalitySystem(config_dir)
    return _personality_system
