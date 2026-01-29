"""System-level data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SystemConfigKey(str, Enum):
    """System configuration keys."""
    CURRENT_PERSONALITY = "current_personality"
    MAINTENANCE_MODE = "maintenance_mode"
    AI_PROVIDER = "ai_provider"
    GREETING_ENABLED = "greeting_enabled"
    MEMORY_CONSOLIDATION_ENABLED = "memory_consolidation_enabled"


class SystemConfig(Base):
    """System configuration storage."""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.key}, value={self.value})>"


class SystemLog(Base):
    """System event logging."""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR
    category = Column(String(64), nullable=False, index=True)  # auth, message, memory, etc.
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)

    user_id = Column(Integer, nullable=True, index=True)
    conversation_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<SystemLog(level={self.level}, category={self.category})>"


class SystemStats(Base):
    """System statistics tracking."""
    __tablename__ = "system_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD

    # Message stats
    total_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)
    assistant_messages = Column(Integer, default=0)

    # User stats
    active_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)

    # AI stats
    total_tokens = Column(Integer, default=0)
    avg_response_time_ms = Column(Integer, default=0)

    # Memory stats
    memories_created = Column(Integer, default=0)
    memories_consolidated = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SystemStats(date={self.date})>"


# Pydantic models

class SystemConfigSchema(BaseModel):
    """Pydantic schema for system config."""
    key: str
    value: Optional[str] = None
    value_type: str = "string"
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SystemStatsSchema(BaseModel):
    """Pydantic schema for system stats."""
    date: str
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    active_users: int = 0
    new_users: int = 0
    total_tokens: int = 0
    avg_response_time_ms: int = 0
    memories_created: int = 0
    memories_consolidated: int = 0

    class Config:
        from_attributes = True


class AppInfo(BaseModel):
    """Application information."""
    name: str = "AI Girlfriend Agent"
    version: str = "0.1.0"
    environment: str = "development"
    ai_provider: str = "qianwen"
    current_personality: Optional[str] = None
    uptime_seconds: int = 0
    total_users: int = 0
    total_conversations: int = 0
