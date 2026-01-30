"""Logging configuration using Loguru."""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import deque
import threading

from loguru import logger


# 全局日志存储，用于实时监控
class LogStore:
    """Store recent logs for monitoring."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._logs = deque(maxlen=1000)  # 保留最近1000条
                    cls._instance._chat_logs = deque(maxlen=500)  # 对话日志
                    cls._instance._error_logs = deque(maxlen=200)  # 错误日志
        return cls._instance

    def add_log(self, record: Dict[str, Any]):
        """Add a log record."""
        log_entry = {
            "time": record.get("time", datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.get("level", {}).name if hasattr(record.get("level", {}), "name") else str(record.get("level", "INFO")),
            "module": record.get("name", "unknown"),
            "function": record.get("function", ""),
            "message": record.get("message", ""),
        }
        self._logs.append(log_entry)

        # 分类存储
        level = log_entry["level"]
        if level in ("ERROR", "CRITICAL"):
            self._error_logs.append(log_entry)

    def add_chat_log(self, user_id: int, user_msg: str, ai_response: str,
                     response_time: float, tokens: int = 0):
        """Add a chat log entry."""
        self._chat_logs.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "user_message": user_msg[:100] + "..." if len(user_msg) > 100 else user_msg,
            "ai_response": ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
            "response_time_ms": round(response_time, 2),
            "tokens": tokens,
        })

    def get_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict]:
        """Get recent logs."""
        logs = list(self._logs)
        if level:
            logs = [l for l in logs if l["level"] == level.upper()]
        return logs[-limit:]

    def get_chat_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent chat logs."""
        return list(self._chat_logs)[-limit:]

    def get_error_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent error logs."""
        return list(self._error_logs)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics."""
        logs = list(self._logs)
        chat_logs = list(self._chat_logs)

        # 统计各级别日志数量
        level_counts = {}
        for log in logs:
            level = log["level"]
            level_counts[level] = level_counts.get(level, 0) + 1

        # 计算平均响应时间
        avg_response_time = 0
        if chat_logs:
            avg_response_time = sum(c["response_time_ms"] for c in chat_logs) / len(chat_logs)

        return {
            "total_logs": len(logs),
            "total_chats": len(chat_logs),
            "total_errors": len(list(self._error_logs)),
            "level_counts": level_counts,
            "avg_response_time_ms": round(avg_response_time, 2),
        }


def get_log_store() -> LogStore:
    """Get the global log store instance."""
    return LogStore()


def log_sink(message):
    """Custom sink to store logs."""
    record = message.record
    get_log_store().add_log(record)


def setup_logger(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_format: Optional[str] = None,
) -> None:
    """Setup application logger.

    Args:
        log_level: Logging level
        log_dir: Directory for log files
        log_format: Log message format
    """
    # Remove default handler
    logger.remove()

    # Default format
    if log_format is None:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    # Console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
    )

    # Memory handler for monitoring
    logger.add(
        log_sink,
        format="{message}",
        level=log_level,
    )

    # File handlers - 默认启用
    if log_dir is None:
        log_dir = Path("data/logs")

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 简化的文件格式（无颜色）
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )

    # General log file
    logger.add(
        log_dir / "app.log",
        format=file_format,
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )

    # Error log file
    logger.add(
        log_dir / "error.log",
        format=file_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # Chat log file
    logger.add(
        log_dir / "chat.log",
        format=file_format,
        level="INFO",
        rotation="50 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "chat_log" in record["extra"],
    )

    # Debug log file (only in debug mode)
    if log_level == "DEBUG":
        logger.add(
            log_dir / "debug.log",
            format=file_format,
            level="DEBUG",
            rotation="50 MB",
            retention="3 days",
            compression="zip",
            encoding="utf-8",
        )

    logger.info(f"Logger initialized with level: {log_level}")


def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)
