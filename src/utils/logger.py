"""Logging configuration using Loguru."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


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

    # File handlers
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # General log file
        logger.add(
            log_dir / "app.log",
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
        )

        # Error log file
        logger.add(
            log_dir / "error.log",
            format=log_format,
            level="ERROR",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
        )

        # Debug log file (only in debug mode)
        if log_level == "DEBUG":
            logger.add(
                log_dir / "debug.log",
                format=log_format,
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
