"""Custom exceptions for AI Girlfriend Agent."""

from typing import Optional


class AIGFException(Exception):
    """Base exception for AI Girlfriend Agent."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    user_message: str = "服务暂时不可用，请稍后再试"

    def __init__(self, message: str = None, user_message: str = None):
        self.message = message or self.__class__.__doc__
        if user_message:
            self.user_message = user_message
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to API response dict."""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.user_message,
            "detail": self.message if self.message != self.user_message else None,
        }


class ConfigurationError(AIGFException):
    """Configuration related errors."""
    status_code = 500
    error_code = "CONFIG_ERROR"
    user_message = "系统配置错误"


class AIServiceError(AIGFException):
    """AI service related errors."""
    status_code = 503
    error_code = "AI_SERVICE_ERROR"
    user_message = "AI服务暂时不可用，请稍后再试"


class AIProviderUnavailable(AIServiceError):
    """AI provider is unavailable."""
    error_code = "AI_PROVIDER_UNAVAILABLE"
    user_message = "AI服务提供商暂时不可用"


class AIRateLimitError(AIServiceError):
    """AI service rate limit exceeded."""
    status_code = 429
    error_code = "AI_RATE_LIMIT"
    user_message = "请求太频繁，请稍后再试"


class MemoryError(AIGFException):
    """Memory system related errors."""
    error_code = "MEMORY_ERROR"
    user_message = "记忆系统错误"


class MemoryExtractionError(MemoryError):
    """Failed to extract memories from conversation."""
    error_code = "MEMORY_EXTRACTION_ERROR"


class MemoryConsolidationError(MemoryError):
    """Failed to consolidate memories."""
    error_code = "MEMORY_CONSOLIDATION_ERROR"


class ConversationError(AIGFException):
    """Conversation related errors."""
    error_code = "CONVERSATION_ERROR"
    user_message = "对话处理失败"


class ContextOverflowError(ConversationError):
    """Conversation context exceeded limits."""
    error_code = "CONTEXT_OVERFLOW"
    user_message = "对话内容过长，请开始新对话"


class RAGServiceError(AIGFException):
    """RAG service related errors."""
    status_code = 503
    error_code = "RAG_SERVICE_ERROR"
    user_message = "知识检索服务不可用"


class SearchServiceError(AIGFException):
    """Search service related errors."""
    status_code = 503
    error_code = "SEARCH_SERVICE_ERROR"
    user_message = "搜索服务暂时不可用"


class WeChatError(AIGFException):
    """WeChat related errors."""
    error_code = "WECHAT_ERROR"
    user_message = "微信服务错误"


class WeChatLoginError(WeChatError):
    """WeChat login failed."""
    error_code = "WECHAT_LOGIN_ERROR"
    user_message = "微信登录失败"


class WeChatConnectionError(WeChatError):
    """WeChat connection lost."""
    error_code = "WECHAT_CONNECTION_ERROR"
    user_message = "微信连接断开"


class WeChatMessageError(WeChatError):
    """Failed to send/receive WeChat message."""
    error_code = "WECHAT_MESSAGE_ERROR"
    user_message = "微信消息发送失败"


class SecurityError(AIGFException):
    """Security related errors."""
    status_code = 403
    error_code = "SECURITY_ERROR"
    user_message = "安全检查未通过"


class RateLimitExceeded(SecurityError):
    """Rate limit exceeded."""
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    user_message = "请求太频繁，请稍后再试"


class ContentFilterError(SecurityError):
    """Content failed security filter."""
    error_code = "CONTENT_FILTER_ERROR"
    user_message = "消息内容不合规"


class UserError(AIGFException):
    """User related errors."""
    status_code = 400
    error_code = "USER_ERROR"
    user_message = "用户操作错误"


class UserNotFound(UserError):
    """User not found."""
    status_code = 404
    error_code = "USER_NOT_FOUND"
    user_message = "用户不存在"


class UserBlocked(UserError):
    """User is blocked."""
    status_code = 403
    error_code = "USER_BLOCKED"
    user_message = "用户已被禁用"


class DatabaseError(AIGFException):
    """Database related errors."""
    error_code = "DATABASE_ERROR"
    user_message = "数据库服务错误"


class CacheError(AIGFException):
    """Cache related errors."""
    error_code = "CACHE_ERROR"
    user_message = "缓存服务错误"


class ServiceUnavailableError(AIGFException):
    """Service is not initialized or unavailable."""
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    user_message = "服务尚未初始化，请稍后再试"


class ValidationError(AIGFException):
    """Input validation error."""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    user_message = "输入参数无效"
