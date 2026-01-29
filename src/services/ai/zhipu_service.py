"""Zhipu AI (GLM) service implementation."""

from typing import List, Optional

from loguru import logger
from zhipuai import ZhipuAI

from src.services.ai.provider import AIMessage, AIResponse, AIRole, AIServiceProvider


class ZhipuService(AIServiceProvider):
    """Zhipu AI (GLM) service provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4",
        **kwargs,
    ):
        """Initialize Zhipu service.

        Args:
            api_key: Zhipu API key
            model: Model name (glm-4, glm-4-flash, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.client = ZhipuAI(api_key=api_key)
        logger.info(f"Zhipu service initialized with model: {model}")

    def _convert_messages(self, messages: List[AIMessage]) -> List[dict]:
        """Convert AIMessage to Zhipu format."""
        result = []
        for msg in messages:
            role = msg.role.value
            if role == "system":
                role = "system"
            elif role == "user":
                role = "user"
            else:
                role = "assistant"
            result.append({"role": role, "content": msg.content})
        return result

    async def chat(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> AIResponse:
        """Generate chat completion.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            AIResponse with generated content
        """
        try:
            zhipu_messages = self._convert_messages(messages)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=zhipu_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            usage = response.usage

            return AIResponse(
                content=content,
                model=self.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )

        except Exception as e:
            logger.error(f"Zhipu chat error: {e}")
            raise

    async def simple_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Simple chat with single user message.

        Args:
            user_message: User message
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated response text
        """
        messages = []
        if system_prompt:
            messages.append(AIMessage(role=AIRole.SYSTEM, content=system_prompt))
        messages.append(AIMessage(role=AIRole.USER, content=user_message))

        response = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content

    async def stream_chat(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ):
        """Stream chat completion.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Content chunks
        """
        try:
            zhipu_messages = self._convert_messages(messages)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=zhipu_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Zhipu stream chat error: {e}")
            raise
