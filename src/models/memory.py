"""Memory data models for short-term and long-term memory."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MemoryType(str, Enum):
    """Memory type enumeration."""
    FACT = "fact"  # 事实信息（姓名、年龄等）
    PREFERENCE = "preference"  # 偏好信息
    EVENT = "event"  # 事件记忆
    EMOTION = "emotion"  # 情感记忆
    RELATIONSHIP = "relationship"  # 关系信息
    HABIT = "habit"  # 习惯信息
    GOAL = "goal"  # 目标/计划
    CONTEXT = "context"  # 上下文信息


class MemoryStatus(str, Enum):
    """Memory status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class Memory(Base):
    """Base memory model for all types of memories."""
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Memory classification
    memory_type = Column(String(32), nullable=False, index=True)
    category = Column(String(64), nullable=True)  # 子分类

    # Memory content
    content = Column(Text, nullable=False)  # 记忆内容
    summary = Column(String(512), nullable=True)  # 摘要
    keywords = Column(JSON, default=list)  # 关键词，用于检索

    # Source information
    source_message_id = Column(Integer, nullable=True)  # 来源消息ID
    source_conversation_id = Column(Integer, nullable=True)  # 来源对话ID

    # Importance and relevance
    importance = Column(Float, default=0.5)  # 重要性 0-1
    confidence = Column(Float, default=0.5)  # 置信度 0-1
    relevance_decay = Column(Float, default=0.01)  # 相关性衰减率

    # Access tracking
    access_count = Column(Integer, default=0)  # 访问次数
    last_accessed_at = Column(DateTime, nullable=True)  # 最后访问时间

    # Status
    status = Column(String(20), default=MemoryStatus.ACTIVE.value)
    is_consolidated = Column(Boolean, default=False)  # 是否已固化为长期记忆

    # Timestamps
    occurred_at = Column(DateTime, nullable=True)  # 事件发生时间
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Memory(id={self.id}, type={self.memory_type}, user_id={self.user_id})>"


class ShortTermMemory(Base):
    """Short-term memory for recent conversation context."""
    __tablename__ = "short_term_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    conversation_id = Column(Integer, nullable=False, index=True)

    # Memory content
    content = Column(Text, nullable=False)
    memory_type = Column(String(32), default=MemoryType.CONTEXT.value)

    # Extracted information
    extracted_info = Column(JSON, default=dict)  # 提取的结构化信息
    emotion_state = Column(JSON, default=dict)  # 情绪状态

    # Relevance
    relevance_score = Column(Float, default=1.0)  # 相关性分数，随时间衰减

    # Consolidation tracking
    consolidation_score = Column(Float, default=0.0)  # 固化评分
    should_consolidate = Column(Boolean, default=False)  # 是否应该固化

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ShortTermMemory(id={self.id}, user_id={self.user_id})>"


class LongTermMemory(Base):
    """Long-term memory for persistent user information."""
    __tablename__ = "long_term_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Memory classification
    memory_type = Column(String(32), nullable=False, index=True)
    category = Column(String(64), nullable=True, index=True)
    subcategory = Column(String(64), nullable=True)

    # Memory content
    key = Column(String(256), nullable=False)  # 记忆键（如 "favorite_food"）
    value = Column(Text, nullable=False)  # 记忆值
    context = Column(Text, nullable=True)  # 上下文说明

    # Metadata
    keywords = Column(JSON, default=list)
    related_memories = Column(JSON, default=list)  # 关联记忆ID列表

    # Importance metrics
    importance = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)
    reinforcement_count = Column(Integer, default=1)  # 强化次数

    # Access tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    # Source tracking
    source_short_term_ids = Column(JSON, default=list)  # 来源短期记忆ID
    first_mentioned_at = Column(DateTime, default=datetime.utcnow)
    last_reinforced_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(20), default=MemoryStatus.ACTIVE.value)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<LongTermMemory(id={self.id}, key={self.key}, user_id={self.user_id})>"


# Pydantic models for API/validation

class MemorySchema(BaseModel):
    """Pydantic schema for memory."""
    id: Optional[int] = None
    user_id: int
    memory_type: str
    category: Optional[str] = None
    content: str
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5
    status: str = MemoryStatus.ACTIVE.value
    is_consolidated: bool = False
    occurred_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShortTermMemorySchema(BaseModel):
    """Pydantic schema for short-term memory."""
    id: Optional[int] = None
    user_id: int
    conversation_id: int
    content: str
    memory_type: str = MemoryType.CONTEXT.value
    extracted_info: Dict[str, Any] = Field(default_factory=dict)
    emotion_state: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = 1.0
    consolidation_score: float = 0.0
    should_consolidate: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LongTermMemorySchema(BaseModel):
    """Pydantic schema for long-term memory."""
    id: Optional[int] = None
    user_id: int
    memory_type: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    key: str
    value: str
    context: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5
    reinforcement_count: int = 1
    access_count: int = 0
    status: str = MemoryStatus.ACTIVE.value
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemorySearchResult(BaseModel):
    """Search result for memory queries."""
    memory: MemorySchema
    relevance_score: float
    match_type: str  # keyword, semantic, exact


class UserMemoryProfile(BaseModel):
    """Aggregated memory profile for a user."""
    user_id: int
    facts: List[LongTermMemorySchema] = Field(default_factory=list)
    preferences: List[LongTermMemorySchema] = Field(default_factory=list)
    events: List[LongTermMemorySchema] = Field(default_factory=list)
    relationships: List[LongTermMemorySchema] = Field(default_factory=list)
    recent_context: List[ShortTermMemorySchema] = Field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Convert memory profile to prompt context string."""
        lines = []

        if self.facts:
            lines.append("【用户基本信息】")
            for fact in self.facts:
                lines.append(f"- {fact.key}: {fact.value}")

        if self.preferences:
            lines.append("\n【用户偏好】")
            for pref in self.preferences:
                lines.append(f"- {pref.key}: {pref.value}")

        if self.relationships:
            lines.append("\n【人际关系】")
            for rel in self.relationships:
                lines.append(f"- {rel.key}: {rel.value}")

        if self.events:
            lines.append("\n【重要事件】")
            for event in self.events[:5]:  # 只取最近5个
                lines.append(f"- {event.value}")

        return "\n".join(lines)
