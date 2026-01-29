"""Content security filter for message safety."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger
from pydantic import BaseModel, Field


class FilterResult(BaseModel):
    """Result of content filtering."""
    is_safe: bool = True
    action: str = "allow"  # allow, warn, block, redirect
    reason: Optional[str] = None
    matched_patterns: List[str] = Field(default_factory=list)
    modified_content: Optional[str] = None


class ContentFilter:
    """Filter for content safety and moderation."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize content filter.

        Args:
            config_path: Path to filter configuration file
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "config", "security", "filters.yaml"
            )

        self.config = self._load_config(config_path)
        self._compile_patterns()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load filter configuration from file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Filter config not found: {config_path}")
            return {}

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self._crisis_patterns: List[re.Pattern] = []

        # Compile crisis keywords
        mental_health = self.config.get("mental_health", {})
        crisis_keywords = mental_health.get("crisis_keywords", [])
        for keyword in crisis_keywords:
            self._crisis_patterns.append(
                re.compile(re.escape(keyword), re.IGNORECASE)
            )

        # Compile blocked topic patterns
        topic_restrictions = self.config.get("topic_restrictions", {})
        self._blocked_topics = topic_restrictions.get("blocked_topics", [])
        self._warning_topics = topic_restrictions.get("warning_topics", [])

    def filter_input(self, content: str) -> FilterResult:
        """Filter user input content.

        Args:
            content: User input to filter

        Returns:
            FilterResult with safety assessment
        """
        if not content:
            return FilterResult()

        # Check input validation rules
        validation = self.config.get("input_validation", {})
        max_length = validation.get("max_length", 2000)
        min_length = validation.get("min_length", 1)

        if len(content) > max_length:
            return FilterResult(
                is_safe=False,
                action="block",
                reason=f"消息太长了，最多{max_length}个字符哦",
            )

        if len(content) < min_length:
            return FilterResult(
                is_safe=False,
                action="block",
                reason="消息不能为空",
            )

        # Check for crisis keywords (highest priority)
        crisis_result = self._check_crisis_keywords(content)
        if crisis_result:
            return crisis_result

        # Check for blocked topics
        topic_result = self._check_topics(content)
        if topic_result:
            return topic_result

        return FilterResult(is_safe=True, action="allow")

    def filter_output(self, content: str) -> FilterResult:
        """Filter AI output content.

        Args:
            content: AI output to filter

        Returns:
            FilterResult with safety assessment
        """
        if not content:
            return FilterResult()

        output_config = self.config.get("output_filtering", {})
        max_length = output_config.get("max_response_length", 1000)

        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length] + "..."
            return FilterResult(
                is_safe=True,
                action="allow",
                modified_content=content,
            )

        # Remove personal info if configured
        if output_config.get("remove_personal_info", True):
            content = self._mask_personal_info(content)
            return FilterResult(
                is_safe=True,
                action="allow",
                modified_content=content,
            )

        return FilterResult(is_safe=True, action="allow")

    def _check_crisis_keywords(self, content: str) -> Optional[FilterResult]:
        """Check for mental health crisis keywords.

        Args:
            content: Content to check

        Returns:
            FilterResult if crisis detected, None otherwise
        """
        matched = []
        for pattern in self._crisis_patterns:
            if pattern.search(content):
                matched.append(pattern.pattern)

        if matched:
            mental_health = self.config.get("mental_health", {})
            crisis_response = mental_health.get("crisis_response", "")

            return FilterResult(
                is_safe=False,
                action="redirect",
                reason="crisis_detected",
                matched_patterns=matched,
                modified_content=crisis_response,
            )

        return None

    def _check_topics(self, content: str) -> Optional[FilterResult]:
        """Check for blocked or warning topics.

        Args:
            content: Content to check

        Returns:
            FilterResult if topic matched, None otherwise
        """
        content_lower = content.lower()

        # Check blocked topics
        for topic in self._blocked_topics:
            if topic.lower() in content_lower:
                redirect_msg = self.config.get("topic_restrictions", {}).get(
                    "redirect_message",
                    "这个话题我不太方便讨论，我们聊点别的好吗？"
                )
                return FilterResult(
                    is_safe=False,
                    action="redirect",
                    reason=f"blocked_topic:{topic}",
                    matched_patterns=[topic],
                    modified_content=redirect_msg,
                )

        # Check warning topics
        for topic in self._warning_topics:
            if topic.lower() in content_lower:
                return FilterResult(
                    is_safe=True,
                    action="warn",
                    reason=f"warning_topic:{topic}",
                    matched_patterns=[topic],
                )

        return None

    def _mask_personal_info(self, content: str) -> str:
        """Mask personal information in content.

        Args:
            content: Content to mask

        Returns:
            Masked content
        """
        # Mask phone numbers
        content = re.sub(r'1[3-9]\d{9}', '1**********', content)

        # Mask email addresses
        content = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '***@***.***', content)

        # Mask ID numbers
        content = re.sub(r'\d{17}[\dXx]', '******************', content)

        return content


class RateLimiter:
    """Rate limiter for message frequency control."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize rate limiter.

        Args:
            config_path: Path to rate limit configuration
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "config", "security", "rate_limits.yaml"
            )

        self.config = self._load_config(config_path)
        self._user_counts: Dict[int, Dict[str, int]] = {}
        self._user_timestamps: Dict[int, List[float]] = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load rate limit configuration."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Rate limit config not found: {config_path}")
            return {}

    def check_rate_limit(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user is within rate limits.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        import time

        if not self.config.get("global", {}).get("enabled", True):
            return True, None

        now = time.time()
        message_rate = self.config.get("message_rate", {})

        # Initialize user tracking
        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = []

        # Clean old timestamps
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        timestamps = self._user_timestamps[user_id]
        timestamps = [t for t in timestamps if t > day_ago]
        self._user_timestamps[user_id] = timestamps

        # Count messages in each window
        per_minute = sum(1 for t in timestamps if t > minute_ago)
        per_hour = sum(1 for t in timestamps if t > hour_ago)
        per_day = len(timestamps)

        # Check limits
        limit_per_minute = message_rate.get("per_minute", 30)
        limit_per_hour = message_rate.get("per_hour", 200)
        limit_per_day = message_rate.get("per_day", 1000)

        exceeded_response = message_rate.get(
            "exceeded_response",
            "你发消息太快啦，让我喘口气~"
        )

        if per_minute >= limit_per_minute:
            return False, exceeded_response

        if per_hour >= limit_per_hour:
            return False, "这一小时聊得太多啦，休息一下吧~"

        if per_day >= limit_per_day:
            return False, "今天聊得够多啦，明天再继续吧~"

        # Record this message
        timestamps.append(now)

        return True, None

    def reset_user(self, user_id: int) -> None:
        """Reset rate limit for user.

        Args:
            user_id: User ID to reset
        """
        if user_id in self._user_timestamps:
            del self._user_timestamps[user_id]
        if user_id in self._user_counts:
            del self._user_counts[user_id]


# Global instances
_content_filter: Optional[ContentFilter] = None
_rate_limiter: Optional[RateLimiter] = None


def get_content_filter() -> ContentFilter:
    """Get global content filter instance."""
    global _content_filter
    if _content_filter is None:
        _content_filter = ContentFilter()
    return _content_filter


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
