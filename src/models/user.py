"""User-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class User(Base):
    """User database model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wechat_id = Column(String(64), unique=True, nullable=False, index=True)
    nickname = Column(String(128), nullable=True)
    remark_name = Column(String(128), nullable=True)  # 备注名
    avatar_url = Column(String(512), nullable=True)

    # User status
    status = Column(String(20), default=UserStatus.ACTIVE.value)
    is_vip = Column(Boolean, default=False)

    # Relationship metrics
    intimacy_level = Column(Float, default=0.0)  # 亲密度 0-100
    trust_level = Column(Float, default=0.0)  # 信任度 0-100
    interaction_count = Column(Integer, default=0)  # 互动次数

    # Timestamps
    first_contact_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, wechat_id={self.wechat_id}, nickname={self.nickname})>"


class UserProfile(Base):
    """User profile for storing learned information about the user."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Basic info (learned from conversations)
    real_name = Column(String(64), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    birthday = Column(String(20), nullable=True)  # MM-DD format
    location = Column(String(128), nullable=True)
    occupation = Column(String(128), nullable=True)

    # Personality traits (learned)
    personality_tags = Column(JSON, default=list)  # ["内向", "理性", "幽默"]
    communication_style = Column(String(64), nullable=True)  # 沟通风格

    # Emotional profile
    emotional_baseline = Column(String(32), default="neutral")  # 情绪基线
    stress_indicators = Column(JSON, default=list)  # 压力信号词
    comfort_topics = Column(JSON, default=list)  # 舒适话题

    # Extended profile data (JSON for flexibility)
    extended_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class UserPreference(Base):
    """User preferences learned from interactions."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Preference category
    category = Column(String(64), nullable=False)  # food, music, movie, hobby, etc.

    # Preference details
    item = Column(String(256), nullable=False)  # 具体项目
    sentiment = Column(String(20), default="like")  # like, dislike, neutral
    intensity = Column(Float, default=0.5)  # 强度 0-1

    # Context
    context = Column(Text, nullable=True)  # 提及时的上下文
    mention_count = Column(Integer, default=1)  # 提及次数

    # Confidence
    confidence = Column(Float, default=0.5)  # 置信度 0-1

    # Timestamps
    first_mentioned_at = Column(DateTime, default=datetime.utcnow)
    last_mentioned_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id}, category={self.category}, item={self.item})>"


# Pydantic models for API/validation

class UserProfileSchema(BaseModel):
    """Pydantic schema for user profile."""
    user_id: int
    real_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    personality_tags: List[str] = Field(default_factory=list)
    communication_style: Optional[str] = None
    emotional_baseline: str = "neutral"
    stress_indicators: List[str] = Field(default_factory=list)
    comfort_topics: List[str] = Field(default_factory=list)
    extended_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class UserPreferenceSchema(BaseModel):
    """Pydantic schema for user preference."""
    user_id: int
    category: str
    item: str
    sentiment: str = "like"
    intensity: float = 0.5
    context: Optional[str] = None
    mention_count: int = 1
    confidence: float = 0.5

    class Config:
        from_attributes = True


class UserSchema(BaseModel):
    """Pydantic schema for user."""
    id: Optional[int] = None
    wechat_id: str
    nickname: Optional[str] = None
    remark_name: Optional[str] = None
    status: str = UserStatus.ACTIVE.value
    intimacy_level: float = 0.0
    trust_level: float = 0.0
    interaction_count: int = 0

    class Config:
        from_attributes = True
