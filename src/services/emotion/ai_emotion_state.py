"""AI Emotion State management for tracking and responding with appropriate emotions."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from loguru import logger

from src.services.emotion.analyzer import EmotionType, EmotionResult, EmotionDimensions


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


# AI情绪的VAD维度映射
AI_MOOD_TO_VAD: Dict[AIMood, EmotionDimensions] = {
    AIMood.HAPPY: EmotionDimensions(valence=0.8, arousal=0.6, dominance=0.6),
    AIMood.CONTENT: EmotionDimensions(valence=0.3, arousal=0.3, dominance=0.5),
    AIMood.CARING: EmotionDimensions(valence=0.6, arousal=0.4, dominance=0.6),
    AIMood.PLAYFUL: EmotionDimensions(valence=0.7, arousal=0.7, dominance=0.6),
    AIMood.WORRIED: EmotionDimensions(valence=-0.2, arousal=0.5, dominance=0.3),
    AIMood.SAD: EmotionDimensions(valence=-0.5, arousal=0.3, dominance=0.3),
    AIMood.ANNOYED: EmotionDimensions(valence=-0.3, arousal=0.6, dominance=0.5),
    AIMood.SHY: EmotionDimensions(valence=0.4, arousal=0.4, dominance=0.2),
    AIMood.EXCITED: EmotionDimensions(valence=0.7, arousal=0.9, dominance=0.6),
}


class MoodHistoryEntry(BaseModel):
    """Single entry in mood history."""
    mood: AIMood
    intensity: float = Field(ge=0, le=1)
    trigger: str  # What caused this mood change
    user_emotion: Optional[EmotionType] = None
    # 新增：记录维度值
    dimensions: Optional[EmotionDimensions] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AIEmotionState(BaseModel):
    """AI's current emotional state."""
    current_mood: AIMood = AIMood.CONTENT
    mood_intensity: float = Field(default=0.5, ge=0, le=1)
    mood_history: List[MoodHistoryEntry] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    # 新增：AI的情绪维度状态
    dimensions: EmotionDimensions = Field(
        default_factory=lambda: EmotionDimensions(valence=0.3, arousal=0.3, dominance=0.5)
    )

    # Mood decay settings
    decay_rate: float = 0.1  # How fast mood returns to baseline per interaction
    baseline_mood: AIMood = AIMood.CONTENT
    baseline_dimensions: EmotionDimensions = Field(
        default_factory=lambda: EmotionDimensions(valence=0.3, arousal=0.3, dominance=0.5)
    )

    # Mood transition settings - controls how fast mood changes
    transition_rate: float = 0.3  # 0.3 means 30% towards target, 70% keep current

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

        # Calculate target intensity based on user emotion intensity
        target_intensity = min(
            user_emotion.intensity * intensity_mod + 0.2,
            1.0
        )

        # Smooth transition: blend current intensity with target
        # transition_rate controls how fast we move towards target (0.3 = 30% towards target)
        if new_mood == state.current_mood:
            # Same mood: gradual intensity change
            new_intensity = state.mood_intensity + (target_intensity - state.mood_intensity) * state.transition_rate
        else:
            # Different mood: slower transition, keep more of current intensity
            new_intensity = state.mood_intensity + (target_intensity - state.mood_intensity) * (state.transition_rate * 0.7)

        # 计算AI情绪维度：基于用户情绪维度进行响应式转换
        target_dimensions = self._calculate_ai_dimensions(user_emotion, new_mood)
        new_dimensions = state.dimensions.blend(target_dimensions, state.transition_rate)

        # Record history
        history_entry = MoodHistoryEntry(
            mood=new_mood,
            intensity=new_intensity,
            trigger=context or f"用户情绪: {user_emotion.primary_emotion.value}",
            user_emotion=user_emotion.primary_emotion,
            dimensions=new_dimensions,
            timestamp=datetime.now(),
        )

        state.mood_history.append(history_entry)

        # Enforce history limit
        if len(state.mood_history) > self.history_limit:
            state.mood_history = state.mood_history[-self.history_limit:]

        # Update state
        state.current_mood = new_mood
        state.mood_intensity = round(new_intensity, 2)
        state.dimensions = new_dimensions
        state.last_updated = datetime.now()

        logger.debug(
            f"AI mood updated for user {user_id}: "
            f"{new_mood.value} (intensity: {new_intensity:.2f}, "
            f"VAD: {new_dimensions.valence:.2f}/{new_dimensions.arousal:.2f}/{new_dimensions.dominance:.2f})"
        )

        return state

    def _calculate_ai_dimensions(
        self,
        user_emotion: EmotionResult,
        ai_mood: AIMood
    ) -> EmotionDimensions:
        """计算AI的情绪维度，基于用户情绪进行响应式转换

        AI的情绪维度会受用户情绪影响，但有自己的响应模式：
        - 用户消极时，AI保持积极但降低唤醒度（安慰模式）
        - 用户积极时，AI共鸣但稍微收敛（不过度兴奋）
        - AI的支配感保持稳定（作为支持者角色）

        Args:
            user_emotion: 用户情绪分析结果
            ai_mood: AI的目标情绪类型

        Returns:
            EmotionDimensions AI的目标情绪维度
        """
        user_dims = user_emotion.dimensions
        base_ai_dims = AI_MOOD_TO_VAD.get(ai_mood, AI_MOOD_TO_VAD[AIMood.CONTENT])

        # AI效价：倾向积极，但会受用户影响
        # 用户消极时AI保持温和积极，用户积极时AI共鸣
        if user_dims.valence < 0:
            # 用户消极：AI保持积极但不过度
            ai_valence = max(0.3, base_ai_dims.valence * 0.8)
        else:
            # 用户积极：AI共鸣但稍收敛
            ai_valence = base_ai_dims.valence * 0.9 + user_dims.valence * 0.1

        # AI唤醒度：与用户情绪强度相关，但更平稳
        # 用户激动时AI稍微跟随，用户平静时AI也平静
        ai_arousal = base_ai_dims.arousal * 0.7 + user_dims.arousal * 0.3

        # AI支配感：保持稳定的支持者角色
        # 用户无力时AI稍微主动，用户自信时AI配合
        if user_dims.dominance < 0.3:
            ai_dominance = min(0.7, base_ai_dims.dominance + 0.1)
        else:
            ai_dominance = base_ai_dims.dominance

        return EmotionDimensions(
            valence=round(max(-1, min(1, ai_valence)), 2),
            arousal=round(max(0, min(1, ai_arousal)), 2),
            dominance=round(max(0, min(1, ai_dominance)), 2),
        )

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

        # 获取对应情绪的维度
        dimensions = AI_MOOD_TO_VAD.get(mood, AI_MOOD_TO_VAD[AIMood.CONTENT])

        history_entry = MoodHistoryEntry(
            mood=mood,
            intensity=intensity,
            trigger=trigger,
            dimensions=dimensions,
            timestamp=datetime.now(),
        )

        state.mood_history.append(history_entry)
        state.current_mood = mood
        state.mood_intensity = intensity
        state.dimensions = dimensions
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

        # 添加维度描述
        dim_desc = state.dimensions.describe()

        return f"【当前心情】{description}{intensity_desc}（{dim_desc}）"

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
            "dimensions": {
                "valence": state.dimensions.valence,
                "arousal": state.dimensions.arousal,
                "dominance": state.dimensions.dominance,
                "description": state.dimensions.describe(),
            },
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
                "dimensions": {
                    "valence": entry.dimensions.valence,
                    "arousal": entry.dimensions.arousal,
                    "dominance": entry.dimensions.dominance,
                } if entry.dimensions else None,
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
