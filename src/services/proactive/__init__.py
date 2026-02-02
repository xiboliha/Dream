"""Proactive messaging service module."""

from .message_service import (
    ProactiveMessageService,
    get_proactive_service,
    init_proactive_service,
)

__all__ = [
    "ProactiveMessageService",
    "get_proactive_service",
    "init_proactive_service",
]
