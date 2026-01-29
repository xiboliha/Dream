"""Abstract base class for AI service providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional


class AIRole(str, Enum):
    """Message role for AI conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class AIMessage:
    """Message structure for AI conversations."""
    role: AIRole
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        d = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class AIResponse:
    """Response from AI service."""
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None

    @property
    def prompt_tokens(self) -> int:
        """Get prompt token count."""
        return self.usage.get("prompt_tokens", 0) if self.usage else 0

    @property
    def completion_tokens(self) -> int:
        """Get completion token count."""
        return self.usage.get("completion_tokens", 0) if self.usage else 0

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.usage.get("total_tokens", 0) if self.usage else 0


class AIServiceProvider(ABC):
    """Abstract base class for AI service providers."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize AI service provider.

        Args:
            api_key: API key for the service
            model: Model name to use
            base_url: Optional base URL for API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    async def chat(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AIResponse:
        """Send chat completion request.

        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            AIResponse with the generated content
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat completion request.

        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Yields:
            Content chunks as they are generated
        """
        pass

    async def simple_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Simple chat interface for single-turn conversations.

        Args:
            user_message: User's message
            system_prompt: Optional system prompt
            temperature: Sampling temperature

        Returns:
            Assistant's response content
        """
        messages = []
        if system_prompt:
            messages.append(AIMessage(role=AIRole.SYSTEM, content=system_prompt))
        messages.append(AIMessage(role=AIRole.USER, content=user_message))

        response = await self.chat(messages, temperature=temperature)
        return response.content

    @abstractmethod
    async def close(self) -> None:
        """Close the service and release resources."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(model={self.model})>"
