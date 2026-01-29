"""Conversation and message data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MessageType(str, Enum):
    """Message type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    LINK = "link"
    SYSTEM = "system"


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    """Conversation status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class Conversation(Base):
    """Conversation session model."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)

    # Conversation metadata
    status = Column(String(20), default=ConversationStatus.ACTIVE.value)
    topic = Column(String(256), nullable=True)  # 对话主题
    mood = Column(String(32), nullable=True)  # 对话氛围

    # Statistics
    message_count = Column(Integer, default=0)
    user_message_count = Column(Integer, default=0)
    assistant_message_count = Column(Integer, default=0)

    # Context summary (for long conversations)
    context_summary = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session_id={self.session_id}, user_id={self.user_id})>"


class Message(Base):
    """Individual message model."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    message_type = Column(String(20), default=MessageType.TEXT.value)
    content = Column(Text, nullable=False)

    # Media (for non-text messages)
    media_url = Column(String(512), nullable=True)
    media_metadata = Column(JSON, default=dict)

    # Analysis results
    emotion_detected = Column(String(32), nullable=True)  # 检测到的情绪
    emotion_intensity = Column(Float, nullable=True)  # 情绪强度
    intent = Column(String(64), nullable=True)  # 用户意图
    keywords = Column(JSON, default=list)  # 关键词

    # Response metadata (for assistant messages)
    response_time_ms = Column(Integer, nullable=True)  # 响应时间
    model_used = Column(String(64), nullable=True)  # 使用的模型
    tokens_used = Column(Integer, nullable=True)  # token消耗

    # Flags
    is_important = Column(Boolean, default=False)  # 重要消息标记
    is_processed = Column(Boolean, default=False)  # 是否已处理（用于记忆提取）

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, type={self.message_type})>"


# Pydantic models for API/validation

class MessageSchema(BaseModel):
    """Pydantic schema for message."""
    id: Optional[int] = None
    conversation_id: Optional[int] = None
    user_id: int
    role: str
    message_type: str = MessageType.TEXT.value
    content: str
    media_url: Optional[str] = None
    media_metadata: Dict[str, Any] = Field(default_factory=dict)
    emotion_detected: Optional[str] = None
    emotion_intensity: Optional[float] = None
    intent: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    is_important: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    """Pydantic schema for conversation."""
    id: Optional[int] = None
    user_id: int
    session_id: str
    status: str = ConversationStatus.ACTIVE.value
    topic: Optional[str] = None
    mood: Optional[str] = None
    message_count: int = 0
    context_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationContext(BaseModel):
    """Context object for conversation processing."""
    user_id: int
    session_id: str
    messages: List[MessageSchema] = Field(default_factory=list)
    user_profile: Optional[Dict[str, Any]] = None
    relevant_memories: List[Dict[str, Any]] = Field(default_factory=list)
    current_mood: Optional[str] = None
    topic: Optional[str] = None

    def get_message_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get formatted message history for AI context."""
        history = []
        for msg in self.messages[-limit:]:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        return history

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the context."""
        msg = MessageSchema(
            user_id=self.user_id,
            role=role,
            content=content,
            created_at=datetime.utcnow(),
            **kwargs
        )
        self.messages.append(msg)
