"""Custom exceptions for AI Girlfriend Agent."""


class AIGFException(Exception):
    """Base exception for AI Girlfriend Agent."""
    pass


class ConfigurationError(AIGFException):
    """Configuration related errors."""
    pass


class AIServiceError(AIGFException):
    """AI service related errors."""
    pass


class AIProviderUnavailable(AIServiceError):
    """AI provider is unavailable."""
    pass


class AIRateLimitError(AIServiceError):
    """AI service rate limit exceeded."""
    pass


class MemoryError(AIGFException):
    """Memory system related errors."""
    pass


class MemoryExtractionError(MemoryError):
    """Failed to extract memories from conversation."""
    pass


class MemoryConsolidationError(MemoryError):
    """Failed to consolidate memories."""
    pass


class ConversationError(AIGFException):
    """Conversation related errors."""
    pass


class ContextOverflowError(ConversationError):
    """Conversation context exceeded limits."""
    pass


class WeChatError(AIGFException):
    """WeChat related errors."""
    pass


class WeChatLoginError(WeChatError):
    """WeChat login failed."""
    pass


class WeChatConnectionError(WeChatError):
    """WeChat connection lost."""
    pass


class WeChatMessageError(WeChatError):
    """Failed to send/receive WeChat message."""
    pass


class SecurityError(AIGFException):
    """Security related errors."""
    pass


class RateLimitExceeded(SecurityError):
    """Rate limit exceeded."""
    pass


class ContentFilterError(SecurityError):
    """Content failed security filter."""
    pass


class UserError(AIGFException):
    """User related errors."""
    pass


class UserNotFound(UserError):
    """User not found."""
    pass


class UserBlocked(UserError):
    """User is blocked."""
    pass


class DatabaseError(AIGFException):
    """Database related errors."""
    pass


class CacheError(AIGFException):
    """Cache related errors."""
    pass
