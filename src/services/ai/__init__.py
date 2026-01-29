"""AI services for AI Girlfriend Agent."""

from typing import Optional

from loguru import logger

from src.services.ai.provider import AIMessage, AIResponse, AIRole, AIServiceProvider


def create_ai_service(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> AIServiceProvider:
    """Factory function to create AI service provider.

    Args:
        provider: Provider name (openai, qianwen, wenxin)
        api_key: API key
        model: Optional model name
        base_url: Optional base URL
        **kwargs: Additional provider-specific arguments

    Returns:
        AIServiceProvider instance
    """
    provider = provider.lower()

    if provider == "openai":
        from src.services.ai.openai_service import OpenAIService
        return OpenAIService(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url=base_url,
            **kwargs,
        )
    elif provider == "qianwen":
        from src.services.ai.qianwen_service import QianwenService
        return QianwenService(
            api_key=api_key,
            model=model or "qwen-turbo",
            **kwargs,
        )
    elif provider == "zhipu":
        from src.services.ai.zhipu_service import ZhipuService
        return ZhipuService(
            api_key=api_key,
            model=model or "glm-4",
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


__all__ = [
    "AIMessage",
    "AIResponse",
    "AIRole",
    "AIServiceProvider",
    "create_ai_service",
]
