"""Qianwen (Aliyun DashScope) API service implementation."""

import asyncio
from typing import AsyncGenerator, List, Optional

from loguru import logger

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("DashScope package not installed")

from src.services.ai.provider import AIMessage, AIResponse, AIServiceProvider


class QianwenService(AIServiceProvider):
    """Qianwen (Aliyun DashScope) API service implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-turbo",
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize Qianwen service.

        Args:
            api_key: DashScope API key
            model: Model name (default: qwen-turbo)
            base_url: Not used for DashScope
            timeout: Request timeout
            max_retries: Maximum retries
        """
        super().__init__(api_key, model, base_url, timeout, max_retries)

        if not DASHSCOPE_AVAILABLE:
            raise ImportError("DashScope package is required. Install with: pip install dashscope")

        dashscope.api_key = api_key
        self._retries = max_retries
        logger.info(f"Qianwen service initialized with model: {model}")

    async def chat(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AIResponse:
        """Send chat completion request to Qianwen.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Returns:
            AIResponse with generated content
        """
        # Convert messages to DashScope format
        formatted_messages = [m.to_dict() for m in messages]

        # Run in executor since dashscope is synchronous
        loop = asyncio.get_event_loop()

        def _call():
            return Generation.call(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format="message",
                **kwargs,
            )

        try:
            for attempt in range(self._retries):
                try:
                    response = await loop.run_in_executor(None, _call)

                    if response.status_code == 200:
                        output = response.output
                        usage = response.usage

                        return AIResponse(
                            content=output.choices[0].message.content,
                            model=self.model,
                            finish_reason=output.choices[0].finish_reason,
                            usage={
                                "prompt_tokens": usage.input_tokens if usage else 0,
                                "completion_tokens": usage.output_tokens if usage else 0,
                                "total_tokens": (usage.input_tokens + usage.output_tokens) if usage else 0,
                            },
                            raw_response=response,
                        )
                    else:
                        logger.warning(f"Qianwen API error: {response.code} - {response.message}")
                        if attempt < self._retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))
                            continue
                        raise Exception(f"Qianwen API error: {response.code} - {response.message}")

                except Exception as e:
                    if attempt < self._retries - 1:
                        logger.warning(f"Qianwen request failed (attempt {attempt + 1}): {e}")
                        await asyncio.sleep(1 * (attempt + 1))
                        continue
                    raise

        except Exception as e:
            logger.error(f"Qianwen chat error: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat completion request.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Yields:
            Content chunks
        """
        formatted_messages = [m.to_dict() for m in messages]

        loop = asyncio.get_event_loop()

        def _stream_call():
            responses = Generation.call(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format="message",
                stream=True,
                incremental_output=True,
                **kwargs,
            )
            return list(responses)

        try:
            # Get all chunks (dashscope streaming is synchronous)
            chunks = await loop.run_in_executor(None, _stream_call)

            for response in chunks:
                if response.status_code == 200:
                    content = response.output.choices[0].message.content
                    if content:
                        yield content
                else:
                    logger.warning(f"Qianwen stream error: {response.code}")

        except Exception as e:
            logger.error(f"Qianwen stream error: {e}")
            raise

    async def close(self) -> None:
        """Close the service (no-op for DashScope)."""
        logger.info("Qianwen service closed")
