"""Main configuration settings using Pydantic Settings."""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    QIANWEN = "qianwen"
    WENXIN = "wenxin"
    ZHIPU = "zhipu"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AI Girlfriend Agent"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default=None)
    log_dir: Path = Field(default=None)

    # AI Provider Settings
    ai_provider: AIProvider = AIProvider.QIANWEN

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None

    # Qianwen (Aliyun DashScope)
    qianwen_api_key: Optional[str] = None
    qianwen_model: str = "deepseek-v3"

    # Wenxin (Baidu)
    wenxin_api_key: Optional[str] = None
    wenxin_secret_key: Optional[str] = None
    wenxin_model: str = "ernie-bot-4"

    # Database
    database_url: str = "sqlite:///./data/database/aigf.db"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None

    # WeChat
    wechat_hot_reload: bool = True
    wechat_qr_path: str = "./data/cache/qr.png"
    wechat_status_storage_dir: str = "./data/cache/wechat"

    # Memory Settings
    short_term_memory_limit: int = 20  # Number of recent messages to keep
    long_term_memory_threshold: float = 0.7  # Importance threshold for consolidation
    memory_consolidation_interval: int = 3600  # Seconds between consolidation runs

    # Conversation Settings
    max_context_messages: int = 10
    response_timeout: float = 30.0
    typing_delay_min: float = 0.5
    typing_delay_max: float = 2.0

    # Rate Limiting
    rate_limit_messages_per_minute: int = 30
    rate_limit_messages_per_hour: int = 200

    # Security
    content_filter_enabled: bool = True
    max_message_length: int = 2000

    # Scheduler
    morning_greeting_hour: int = 8
    noon_greeting_hour: int = 12  # 午饭提醒
    afternoon_nap_hour: int = 14  # 午睡结束
    dinner_greeting_hour: int = 18  # 晚饭提醒
    night_greeting_hour: int = 22

    # Logging
    log_level: str = "INFO"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

    # RAG / Vector Store
    rag_backend: str = "faiss"  # "faiss" or "qdrant"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "dialogues"

    @field_validator("data_dir", mode="before")
    @classmethod
    def set_data_dir(cls, v, info):
        if v is None:
            base = info.data.get("base_dir", Path(__file__).parent.parent)
            return Path(base) / "data"
        return Path(v)

    @field_validator("log_dir", mode="before")
    @classmethod
    def set_log_dir(cls, v, info):
        if v is None:
            base = info.data.get("base_dir", Path(__file__).parent.parent)
            return Path(base) / "data" / "logs"
        return Path(v)

    def get_ai_api_key(self) -> str:
        """Get the API key for the current AI provider."""
        if self.ai_provider == AIProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return self.openai_api_key
        elif self.ai_provider == AIProvider.QIANWEN:
            if not self.qianwen_api_key:
                raise ValueError("Qianwen API key not configured")
            return self.qianwen_api_key
        elif self.ai_provider == AIProvider.WENXIN:
            if not self.wenxin_api_key:
                raise ValueError("Wenxin API key not configured")
            return self.wenxin_api_key
        raise ValueError(f"Unknown AI provider: {self.ai_provider}")

    def get_ai_model(self) -> str:
        """Get the model name for the current AI provider."""
        if self.ai_provider == AIProvider.OPENAI:
            return self.openai_model
        elif self.ai_provider == AIProvider.QIANWEN:
            return self.qianwen_model
        elif self.ai_provider == AIProvider.WENXIN:
            return self.wenxin_model
        raise ValueError(f"Unknown AI provider: {self.ai_provider}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
