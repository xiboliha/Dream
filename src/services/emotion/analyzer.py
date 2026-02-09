"""Emotion analysis service for detecting and responding to user emotions."""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, Field


class EmotionType(str, Enum):
    """Emotion type enumeration."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    LOVING = "loving"
    EXCITED = "excited"
    TIRED = "tired"
    CONFUSED = "confused"


class EmotionDimensions(BaseModel):
    """VAD情绪维度模型 (Valence-Arousal-Dominance)

    - valence: 效价，情绪的正负性 (-1=消极, 0=中性, +1=积极)
    - arousal: 唤醒度，情绪的激活程度 (0=平静, 1=激动)
    - dominance: 支配感，控制感程度 (0=被动/无力, 1=主动/掌控)
    """
    valence: float = Field(default=0.0, ge=-1, le=1)
    arousal: float = Field(default=0.5, ge=0, le=1)
    dominance: float = Field(default=0.5, ge=0, le=1)

    def describe(self) -> str:
        """生成情绪维度的自然语言描述"""
        parts = []

        # 效价描述
        if self.valence > 0.3:
            parts.append("积极")
        elif self.valence < -0.3:
            parts.append("消极")
        else:
            parts.append("中性")

        # 唤醒度描述
        if self.arousal > 0.7:
            parts.append("激动")
        elif self.arousal < 0.3:
            parts.append("平静")
        else:
            parts.append("适中")

        # 支配感描述
        if self.dominance > 0.7:
            parts.append("自信")
        elif self.dominance < 0.3:
            parts.append("无力")

        return "、".join(parts)

    def blend(self, other: "EmotionDimensions", weight: float = 0.5) -> "EmotionDimensions":
        """混合两个情绪维度"""
        return EmotionDimensions(
            valence=self.valence * (1 - weight) + other.valence * weight,
            arousal=self.arousal * (1 - weight) + other.arousal * weight,
            dominance=self.dominance * (1 - weight) + other.dominance * weight,
        )


# 每种离散情绪对应的VAD维度值
EMOTION_TO_VAD: Dict[EmotionType, EmotionDimensions] = {
    EmotionType.HAPPY: EmotionDimensions(valence=0.8, arousal=0.6, dominance=0.7),
    EmotionType.SAD: EmotionDimensions(valence=-0.7, arousal=0.3, dominance=0.2),
    EmotionType.ANGRY: EmotionDimensions(valence=-0.6, arousal=0.8, dominance=0.7),
    EmotionType.ANXIOUS: EmotionDimensions(valence=-0.5, arousal=0.7, dominance=0.2),
    EmotionType.SURPRISED: EmotionDimensions(valence=0.2, arousal=0.8, dominance=0.4),
    EmotionType.FEARFUL: EmotionDimensions(valence=-0.7, arousal=0.8, dominance=0.1),
    EmotionType.DISGUSTED: EmotionDimensions(valence=-0.6, arousal=0.5, dominance=0.6),
    EmotionType.NEUTRAL: EmotionDimensions(valence=0.0, arousal=0.3, dominance=0.5),
    EmotionType.LOVING: EmotionDimensions(valence=0.9, arousal=0.5, dominance=0.5),
    EmotionType.EXCITED: EmotionDimensions(valence=0.7, arousal=0.9, dominance=0.6),
    EmotionType.TIRED: EmotionDimensions(valence=-0.3, arousal=0.1, dominance=0.3),
    EmotionType.CONFUSED: EmotionDimensions(valence=-0.2, arousal=0.4, dominance=0.2),
}


class EmotionResult(BaseModel):
    """Result of emotion analysis."""
    primary_emotion: EmotionType = EmotionType.NEUTRAL
    intensity: float = Field(default=0.5, ge=0, le=1)
    secondary_emotion: Optional[EmotionType] = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    keywords_found: List[str] = Field(default_factory=list)
    # 新增：情绪维度
    dimensions: EmotionDimensions = Field(default_factory=EmotionDimensions)

    def get_dimension_description(self) -> str:
        """获取情绪维度描述"""
        return self.dimensions.describe()


class EmotionAnalyzer:
    """Analyzer for detecting emotions from text."""

    # Emotion keyword patterns
    EMOTION_PATTERNS: Dict[EmotionType, List[str]] = {
        EmotionType.HAPPY: [
            "开心", "高兴", "快乐", "幸福", "太好了", "棒", "赞", "哈哈",
            "嘻嘻", "耶", "好开心", "真好", "太棒了", "爽", "美滋滋",
            "笑死", "乐", "喜欢", "爱", "感谢", "谢谢"
        ],
        EmotionType.SAD: [
            "难过", "伤心", "悲伤", "哭", "泪", "痛苦", "失落", "沮丧",
            "郁闷", "心痛", "难受", "不开心", "唉", "呜呜", "委屈",
            "失望", "遗憾", "可惜", "心酸", "想哭"
        ],
        EmotionType.ANGRY: [
            "生气", "愤怒", "气死", "烦", "讨厌", "恨", "火大", "怒",
            "可恶", "混蛋", "该死", "受不了", "忍无可忍", "气愤",
            "恼火", "暴躁", "发火", "不爽"
        ],
        EmotionType.ANXIOUS: [
            "焦虑", "担心", "紧张", "害怕", "不安", "忐忑", "慌",
            "着急", "急", "压力", "崩溃", "受不了", "怎么办",
            "完蛋", "糟糕", "惨了", "烦躁"
        ],
        EmotionType.SURPRISED: [
            "惊讶", "震惊", "天哪", "我靠", "卧槽", "啊", "哇",
            "不敢相信", "真的吗", "居然", "竟然", "没想到", "意外"
        ],
        EmotionType.LOVING: [
            "爱你", "想你", "喜欢你", "亲爱的", "宝贝", "甜蜜",
            "温暖", "幸福", "心动", "暖心", "感动", "珍惜"
        ],
        EmotionType.EXCITED: [
            "兴奋", "激动", "期待", "迫不及待", "太刺激", "好期待",
            "终于", "等不及", "超级", "特别", "非常"
        ],
        EmotionType.TIRED: [
            "累", "疲惫", "困", "乏", "没精神", "好累", "累死",
            "筋疲力尽", "撑不住", "想睡", "休息", "歇歇"
        ],
        EmotionType.CONFUSED: [
            "迷茫", "困惑", "不懂", "不明白", "为什么", "怎么回事",
            "搞不懂", "纠结", "犹豫", "不知道", "不确定"
        ],
    }

    # Intensity modifiers
    INTENSITY_BOOSTERS = ["很", "非常", "特别", "超级", "太", "极其", "真的", "好"]
    INTENSITY_REDUCERS = ["有点", "稍微", "略微", "一点点", "些许"]

    def __init__(self):
        """Initialize emotion analyzer."""
        # Compile patterns for efficiency
        self._compiled_patterns: Dict[EmotionType, re.Pattern] = {}
        for emotion, keywords in self.EMOTION_PATTERNS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            self._compiled_patterns[emotion] = re.compile(pattern)

    def analyze(self, text: str) -> EmotionResult:
        """Analyze text for emotional content.

        Args:
            text: Text to analyze

        Returns:
            EmotionResult with detected emotion
        """
        if not text:
            return EmotionResult()

        text_lower = text.lower()

        # Count matches for each emotion
        emotion_scores: Dict[EmotionType, Tuple[int, List[str]]] = {}

        for emotion, pattern in self._compiled_patterns.items():
            matches = pattern.findall(text_lower)
            if matches:
                emotion_scores[emotion] = (len(matches), matches)

        if not emotion_scores:
            return EmotionResult(
                primary_emotion=EmotionType.NEUTRAL,
                intensity=0.3,
                confidence=0.5,
            )

        # Find primary emotion (most matches)
        sorted_emotions = sorted(
            emotion_scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )

        primary_emotion = sorted_emotions[0][0]
        primary_count, primary_keywords = sorted_emotions[0][1]

        # Calculate intensity
        base_intensity = min(0.5 + primary_count * 0.1, 0.9)
        intensity = self._adjust_intensity(text_lower, base_intensity)

        # Find secondary emotion if exists
        secondary_emotion = None
        if len(sorted_emotions) > 1:
            secondary_emotion = sorted_emotions[1][0]

        # Calculate confidence based on match count and text length
        confidence = min(0.5 + primary_count * 0.15, 0.95)

        # 计算情绪维度 (VAD)
        dimensions = self._calculate_dimensions(
            sorted_emotions, intensity
        )

        return EmotionResult(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotion=secondary_emotion,
            confidence=confidence,
            keywords_found=primary_keywords,
            dimensions=dimensions,
        )

    def _calculate_dimensions(
        self,
        sorted_emotions: List[Tuple[EmotionType, Tuple[int, List[str]]]],
        intensity: float
    ) -> EmotionDimensions:
        """计算复合情绪的VAD维度值

        通过加权混合多种检测到的情绪来计算最终维度值

        Args:
            sorted_emotions: 按匹配数排序的情绪列表
            intensity: 情绪强度

        Returns:
            EmotionDimensions 复合情绪维度
        """
        if not sorted_emotions:
            return EMOTION_TO_VAD[EmotionType.NEUTRAL]

        # 计算总权重
        total_weight = sum(count for _, (count, _) in sorted_emotions)

        # 加权混合各情绪的VAD值
        valence = 0.0
        arousal = 0.0
        dominance = 0.0

        for emotion, (count, _) in sorted_emotions:
            weight = count / total_weight
            base_vad = EMOTION_TO_VAD.get(emotion, EMOTION_TO_VAD[EmotionType.NEUTRAL])

            valence += base_vad.valence * weight
            arousal += base_vad.arousal * weight
            dominance += base_vad.dominance * weight

        # 根据强度调整唤醒度
        arousal = arousal * (0.5 + intensity * 0.5)

        return EmotionDimensions(
            valence=round(max(-1, min(1, valence)), 2),
            arousal=round(max(0, min(1, arousal)), 2),
            dominance=round(max(0, min(1, dominance)), 2),
        )

    def _adjust_intensity(self, text: str, base_intensity: float) -> float:
        """Adjust intensity based on modifiers.

        Args:
            text: Text to check for modifiers
            base_intensity: Base intensity value

        Returns:
            Adjusted intensity
        """
        intensity = base_intensity

        # Check for boosters
        for booster in self.INTENSITY_BOOSTERS:
            if booster in text:
                intensity = min(intensity + 0.1, 1.0)
                break

        # Check for reducers
        for reducer in self.INTENSITY_REDUCERS:
            if reducer in text:
                intensity = max(intensity - 0.15, 0.2)
                break

        # Check for exclamation marks (intensity boost)
        exclamation_count = text.count("!") + text.count("！")
        if exclamation_count > 0:
            intensity = min(intensity + exclamation_count * 0.05, 1.0)

        # Check for repeated characters (intensity boost)
        if re.search(r"(.)\1{2,}", text):
            intensity = min(intensity + 0.1, 1.0)

        return round(intensity, 2)

    def get_response_suggestion(self, emotion: EmotionResult) -> Dict[str, Any]:
        """Get response suggestions based on detected emotion.

        Args:
            emotion: Detected emotion result

        Returns:
            Dict with response suggestions
        """
        suggestions = {
            EmotionType.HAPPY: {
                "tone": "enthusiastic",
                "approach": "share_joy",
                "emoji_boost": True,
            },
            EmotionType.SAD: {
                "tone": "gentle",
                "approach": "comfort",
                "emoji_boost": False,
            },
            EmotionType.ANGRY: {
                "tone": "calm",
                "approach": "validate_then_calm",
                "emoji_boost": False,
            },
            EmotionType.ANXIOUS: {
                "tone": "reassuring",
                "approach": "support_and_rationalize",
                "emoji_boost": False,
            },
            EmotionType.SURPRISED: {
                "tone": "curious",
                "approach": "engage",
                "emoji_boost": True,
            },
            EmotionType.LOVING: {
                "tone": "warm",
                "approach": "reciprocate",
                "emoji_boost": True,
            },
            EmotionType.EXCITED: {
                "tone": "enthusiastic",
                "approach": "match_energy",
                "emoji_boost": True,
            },
            EmotionType.TIRED: {
                "tone": "caring",
                "approach": "encourage_rest",
                "emoji_boost": False,
            },
            EmotionType.CONFUSED: {
                "tone": "patient",
                "approach": "clarify_and_help",
                "emoji_boost": False,
            },
            EmotionType.NEUTRAL: {
                "tone": "friendly",
                "approach": "engage",
                "emoji_boost": True,
            },
        }

        base_suggestion = suggestions.get(
            emotion.primary_emotion,
            suggestions[EmotionType.NEUTRAL]
        )

        # Adjust based on intensity
        if emotion.intensity > 0.7:
            base_suggestion["intensity_response"] = "high"
        elif emotion.intensity < 0.4:
            base_suggestion["intensity_response"] = "low"
        else:
            base_suggestion["intensity_response"] = "moderate"

        return base_suggestion


class EmotionTracker:
    """Tracker for monitoring emotion trends over time."""

    def __init__(self, history_limit: int = 50):
        """Initialize emotion tracker.

        Args:
            history_limit: Maximum history entries per user
        """
        self.history_limit = history_limit
        self._user_history: Dict[int, List[EmotionResult]] = {}

    def record(self, user_id: int, emotion: EmotionResult) -> None:
        """Record emotion for user.

        Args:
            user_id: User ID
            emotion: Emotion result to record
        """
        if user_id not in self._user_history:
            self._user_history[user_id] = []

        self._user_history[user_id].append(emotion)

        # Enforce limit
        if len(self._user_history[user_id]) > self.history_limit:
            self._user_history[user_id] = self._user_history[user_id][-self.history_limit:]

    def get_trend(self, user_id: int, window: int = 10) -> Dict[str, Any]:
        """Get emotion trend for user.

        Args:
            user_id: User ID
            window: Number of recent entries to analyze

        Returns:
            Dict with trend information
        """
        history = self._user_history.get(user_id, [])
        if not history:
            return {"trend": "unknown", "dominant_emotion": None}

        recent = history[-window:]

        # Count emotions
        emotion_counts: Dict[EmotionType, int] = {}
        total_intensity = 0.0

        for entry in recent:
            emotion_counts[entry.primary_emotion] = emotion_counts.get(
                entry.primary_emotion, 0
            ) + 1
            total_intensity += entry.intensity

        # Find dominant emotion
        dominant = max(emotion_counts.items(), key=lambda x: x[1])

        # Calculate average intensity
        avg_intensity = total_intensity / len(recent)

        # Determine trend
        if len(recent) >= 3:
            recent_intensities = [e.intensity for e in recent[-3:]]
            if all(recent_intensities[i] < recent_intensities[i+1] for i in range(len(recent_intensities)-1)):
                trend = "increasing"
            elif all(recent_intensities[i] > recent_intensities[i+1] for i in range(len(recent_intensities)-1)):
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "dominant_emotion": dominant[0].value,
            "dominant_count": dominant[1],
            "average_intensity": round(avg_intensity, 2),
            "sample_size": len(recent),
        }

    def get_baseline(self, user_id: int) -> Optional[EmotionType]:
        """Get emotional baseline for user.

        Args:
            user_id: User ID

        Returns:
            Most common emotion type or None
        """
        history = self._user_history.get(user_id, [])
        if len(history) < 10:
            return None

        emotion_counts: Dict[EmotionType, int] = {}
        for entry in history:
            emotion_counts[entry.primary_emotion] = emotion_counts.get(
                entry.primary_emotion, 0
            ) + 1

        return max(emotion_counts.items(), key=lambda x: x[1])[0]


# Global instances
_analyzer: Optional[EmotionAnalyzer] = None
_tracker: Optional[EmotionTracker] = None


def get_emotion_analyzer() -> EmotionAnalyzer:
    """Get global emotion analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = EmotionAnalyzer()
    return _analyzer


def get_emotion_tracker() -> EmotionTracker:
    """Get global emotion tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = EmotionTracker()
    return _tracker
