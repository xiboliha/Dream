"""WeChat interface module for AI Girlfriend Agent."""

from src.interfaces.wechat.client import WeChatClient
from src.interfaces.wechat.handler import WeChatHandler

__all__ = ["WeChatClient", "WeChatHandler"]
