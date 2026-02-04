"""AI Emotion State management for tracking and responding with appropriate emotions."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from loguru import logger

from src.services.emotion.analyzer import EmotionType, EmotionResult


class AIMood(str, Enum):
    """AI mood states - simplified from EmotionType for AI's own state."""
    HAPPY = "happy"          # 开心
    CONTENT = "content"      # 满足/平静
    CARING = "caring"        # 关心/体贴
    PLAYFUL = "playful"      # 俏皮/调皮
    WORRIED = "worried"      # 担心
    SAD = "sad"              # 难过
    ANNOYED = "annoyed"      # 小生气/撒娇式生气
    SHY = "shy"              # 害羞
    EXCITED = "excited"      # 兴奋


class MoodHistoryEntry(BaseModel):
    """Single entry in mood history."""
    mood: AIMood
    intensity: float = Field(ge=0, le=1)
    trigger: str  # What caused this mood change
    user_emotion: Optional[EmotionType] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AIEmotionState(BaseModel):
    """AI's current emotional state."""
    current_mood: AIMood = AIMood.CONTENT
    mood_intensity: float = Field(default=0.5, ge=0, le=1)
    mood_history: List[MoodHistoryEntry] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    # Mood decay settings
    decay_rate: float = 0.1  # How fast mood returns to baseline per interaction
    baseline_mood: AIMood = AIMood.CONTENT

    class Config:
        arbitrary_types_allowed = True


class AIEmotionManager:
    """Manager for AI's emotional state with transition logic."""

    # Emotion transition rules: user_emotion -> (ai_mood, intensity_modifier)
    EMOTION_TRANSITIONS: Dict[EmotionType, Tuple[AIMood, float]] = {
        EmotionType.HAPPY: (AIMood.HAPPY, 0.8),
        EmotionType.SAD: (AIMood.CARING, 0.7),
        EmotionType.ANGRY: (AIMood.CARING, 0.6),  # Comfort when user is angry
        EmotionType.ANXIOUS: (AIMood.CARING, 0.7),
        EmotionType.SURPRISED: (AIMood.PLAYFUL, 0.6),
        EmotionType.LOVING: (AIMood.SHY, 0.8),  # Shy when receiving love
        EmotionType.EXCITED: (AIMood.EXCITED, 0.8),
        EmotionType.TIRED: (AIMood.CARING, 0.6),
        EmotionType.CONFUSED: (AIMood.CARING, 0.5),
        EmotionType.NEUTRAL: (AIMood.CONTENT, 0.5),
    }

    # Mood descriptions for prompt injection
    MOOD_DESCRIPTIONS: Dict[AIMood, str] = {
        AIMood.HAPPY: "你现在心情很好，说话带着愉悦和活力，会用更多积极的语气词",
        AIMood.CONTENT: "你现在心情平静满足，说话温和自然",
        AIMood.CARING: "你现在很关心对方，说话温柔体贴，想要安慰和照顾对方",
        AIMood.PLAYFUL: "你现在心情俏皮，喜欢开玩笑和调侃，说话带点小调皮",
        AIMood.WORRIED: "你现在有点担心对方，说话会更加关切，想要了解对方的情况",
        AIMood.SAD: "你现在有点难过，说话会比较低落，但还是想陪伴对方",
        AIMood.ANNOYED: "你现在有点小生气，会撒娇式地抱怨，但不是真的生气",
        AIMood.SHY: "你现在有点害羞，说话会比较含蓄，可能会有点脸红的感觉",
        AIMood.EXCITED: "你现在很兴奋，说话会比较激动，语气更加热情",
    }

    # Mood emoji hints for responses
    MOOD_EMOJI_HINTS: Dict[AIMood, List[str]] = {
        AIMood.HAPPY: ["~", "！", "哈哈", "嘻嘻"],
        AIMood.CONTENT: ["~", "呢"],
        AIMood.CARING: ["...", "呢", "嘛"],
        AIMood.PLAYFUL: ["哼", "嘿嘿", "~"],
        AIMood.WORRIED: ["...", "呢"],
        AIMood.SAD: ["...", "唉"],
        AIMood.ANNOYED: ["哼", "！", "喂"],
        AIMood.SHY: ["...", "那个", "嗯"],
        AIMood.EXCITED: ["！", "哇", "耶"],
    }

    def __init__(self, history_limit: int = 100):
        """Initialize AI emotion manager.

        Args:
            history_limit: Maximum mood history entries to keep
        """
        self.history_limit = history_limit
        self._user_states: Dict[int, AIEmotionState] = {}

    def get_state(self, user_id: int) -> AIEmotionState:
        """Get AI emotion state for a specific user.

        Args:
            user_id: User ID

        Returns:
            AIEmotionState for this user
        """
        if user_id not in self._user_states:
            self._user_states[user_id] = AIEmotionState()
        return self._user_states[user_id]

    def update_mood(
        self,
        user_id: int,
        user_emotion: EmotionResult,
        context: str = ""
    ) -> AIEmotionState:
        """Update AI mood based on user's emotion.

        Args:
            user_id: User ID
            user_emotion: Detected user emotion
            context: Additional context for the mood change

        Returns:
            Updated AIEmotionState
        """
        state = self.get_state(user_id)

        # Get transition based on user emotion
        new_mood, intensity_mod = self.EMOTION_TRANSITIONS.get(
            user_emotion.primary_emotion,
            (AIMood.CONTENT, 0.5)
        )

        # Calculate new intensity based on user emotion intensity
        new_intensity = min(
            user_emotion.intensity * intensity_mod + 0.2,
            1.0
        )

        # Apply mood decay towards baseline if same mood
        if new_mood == state.current_mood:
            # Reinforce current mood
            new_intensity = min(state.mood_intensity + 0.1, 1.0)

        # Record history
        history_entry = MoodHistoryEntry(
            mood=new_mood,
            intensity=new_intensity,
            trigger=context or f"用户情绪: {user_emotion.primary_emotion.value}",
            user_emotion=user_emotion.primary_emotion,
            timestamp=datetime.now(),
        )

        state.mood_history.append(history_entry)

        # Enforce history limit
        if len(state.mood_history) > self.history_limit:
            state.mood_history = state.mood_history[-self.history_limit:]

        # Update state
        state.current_mood = new_mood
        state.mood_intensity = round(new_intensity, 2)
        state.last_updated = datetime.now()

        logger.debug(
            f"AI mood updated for user {user_id}: "
            f"{new_mood.value} (intensity: {new_intensity:.2f})"
        )

        return state

    def set_mood(
        self,
        user_id: int,
        mood: AIMood,
        intensity: float = 0.5,
        trigger: str = "手动设置"
    ) -> AIEmotionState:
        """Manually set AI mood (for testing/debugging).

        Args:
            user_id: User ID
            mood: New mood to set
            intensity: Mood intensity
            trigger: Reason for mood change

        Returns:
            Updated AIEmotionState
        """
        state = self.get_state(user_id)

        history_entry = MoodHistoryEntry(
            mood=mood,
            intensity=intensity,
            trigger=trigger,
            timestamp=datetime.now(),
        )

        state.mood_history.append(history_entry)
        state.current_mood = mood
        state.mood_intensity = intensity
        state.last_updated = datetime.now()

        logger.info(f"AI mood manually set for user {user_id}: {mood.value}")

        return state

    def get_mood_prompt(self, user_id: int) -> str:
        """Get mood description for prompt injection.

        Args:
            user_id: User ID

        Returns:
            Mood description string for system prompt
        """
        state = self.get_state(user_id)
        description = self.MOOD_DESCRIPTIONS.get(
            state.current_mood,
            self.MOOD_DESCRIPTIONS[AIMood.CONTENT]
        )

        # Add intensity modifier
        if state.mood_intensity > 0.7:
            intensity_desc = "（情绪比较强烈）"
        elif state.mood_intensity < 0.4:
            intensity_desc = "（情绪比较轻微）"
        else:
            intensity_desc = ""

        return f"【当前心情】{description}{intensity_desc}"

    def get_mood_stats(self, user_id: int) -> Dict[str, Any]:
        """Get mood statistics for monitoring.

        Args:
            user_id: User ID

        Returns:
            Dict with mood statistics
        """
        state = self.get_state(user_id)

        # Count mood occurrences
        mood_counts: Dict[str, int] = {}
        for entry in state.mood_history:
            mood_counts[entry.mood.value] = mood_counts.get(entry.mood.value, 0) + 1

        # Calculate average intensity
        if state.mood_history:
            avg_intensity = sum(e.intensity for e in state.mood_history) / len(state.mood_history)
        else:
            avg_intensity = 0.5

        return {
            "user_id": user_id,
            "current_mood": state.current_mood.value,
            "mood_intensity": state.mood_intensity,
            "last_updated": state.last_updated.isoformat(),
            "history_count": len(state.mood_history),
            "mood_distribution": mood_counts,
            "average_intensity": round(avg_intensity, 2),
        }

    def get_recent_history(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent mood history for monitoring.

        Args:
            user_id: User ID
            limit: Number of entries to return

        Returns:
            List of mood history entries
        """
        state = self.get_state(user_id)
        recent = state.mood_history[-limit:]

        return [
            {
                "mood": entry.mood.value,
                "intensity": entry.intensity,
                "trigger": entry.trigger,
                "user_emotion": entry.user_emotion.value if entry.user_emotion else None,
                "timestamp": entry.timestamp.isoformat(),
            }
            for entry in reversed(recent)  # Most recent first
        ]

    def get_all_user_states(self) -> Dict[int, Dict[str, Any]]:
        """Get all user emotion states for monitoring.

        Returns:
            Dict mapping user_id to their emotion stats
        """
        return {
            user_id: self.get_mood_stats(user_id)
            for user_id in self._user_states.keys()
        }

    def decay_mood(self, user_id: int) -> AIEmotionState:
        """Apply mood decay towards baseline.

        Args:
            user_id: User ID

        Returns:
            Updated AIEmotionState
        """
        state = self.get_state(user_id)

        # Gradually move intensity towards 0.5 (neutral)
        if state.mood_intensity > 0.5:
            state.mood_intensity = max(
                state.mood_intensity - state.decay_rate,
                0.5
            )
        elif state.mood_intensity < 0.5:
            state.mood_intensity = min(
                state.mood_intensity + state.decay_rate,
                0.5
            )

        # If intensity is low enough, return to baseline mood
        if state.mood_intensity <= 0.5 and state.current_mood != state.baseline_mood:
            state.current_mood = state.baseline_mood

        return state


# Global instance
_ai_emotion_manager: Optional[AIEmotionManager] = None


def get_ai_emotion_manager() -> AIEmotionManager:
    """Get global AI emotion manager instance."""
    global _ai_emotion_manager
    if _ai_emotion_manager is None:
        _ai_emotion_manager = AIEmotionManager()
    return _ai_emotion_manager
