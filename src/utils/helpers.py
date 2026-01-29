"""Utility functions and helpers."""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def get_current_time(timezone: str = "Asia/Shanghai") -> datetime:
    """Get current time in specified timezone."""
    tz = pytz.timezone(timezone)
    return datetime.now(tz)


def get_time_greeting(timezone: str = "Asia/Shanghai") -> str:
    """Get appropriate greeting based on time of day."""
    hour = get_current_time(timezone).hour

    if 5 <= hour < 9:
        return "早上好"
    elif 9 <= hour < 12:
        return "上午好"
    elif 12 <= hour < 14:
        return "中午好"
    elif 14 <= hour < 18:
        return "下午好"
    elif 18 <= hour < 22:
        return "晚上好"
    else:
        return "夜深了"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_message(text: str) -> str:
    """Clean and normalize message text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from text."""
    pattern = r'@(\S+)'
    return re.findall(pattern, text)


def mask_sensitive_info(text: str) -> str:
    """Mask sensitive information in text."""
    # Mask phone numbers
    text = re.sub(r'1[3-9]\d{9}', '1**********', text)
    # Mask email addresses
    text = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '***@***.***', text)
    # Mask ID numbers
    text = re.sub(r'\d{17}[\dXx]', '******************', text)
    return text


def calculate_typing_delay(text: str, min_delay: float = 0.5, max_delay: float = 3.0) -> float:
    """Calculate realistic typing delay based on text length."""
    # Assume ~5 characters per second typing speed
    base_delay = len(text) / 50
    return max(min_delay, min(base_delay, max_delay))


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}小时"
    else:
        days = seconds // 86400
        return f"{days}天"


def parse_date_reference(text: str) -> Optional[datetime]:
    """Parse date references from text (今天, 明天, 后天, etc.)."""
    now = get_current_time()

    date_patterns = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
        "昨天": -1,
        "前天": -2,
    }

    for pattern, days in date_patterns.items():
        if pattern in text:
            from datetime import timedelta
            return now + timedelta(days=days)

    return None
