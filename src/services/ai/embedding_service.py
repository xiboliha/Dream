"""Embedding service using Aliyun DashScope."""

import asyncio
from typing import List, Optional

from loguru import logger

try:
    import dashscope
    from dashscope import TextEmbedding
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("DashScope package not installed")


class EmbeddingService:
    """Embedding service using Aliyun DashScope text-embedding API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v3",
        dimension: int = 1024,
    ):
        """Initialize embedding service.

        Args:
            api_key: DashScope API key
            model: Embedding model name
            dimension: Output embedding dimension (512, 1024, or 1536)
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("DashScope package is required. Install with: pip install dashscope")

        dashscope.api_key = api_key
        self.model = model
        self.dimension = dimension
        logger.info(f"Embedding service initialized with model: {model}, dimension: {dimension}")

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        result = await self.embed_texts([text])
        return result[0] if result else None

    async def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors or None if failed
        """
        if not texts:
            return []

        loop = asyncio.get_event_loop()

        def _call():
            return TextEmbedding.call(
                model=self.model,
                input=texts,
                dimension=self.dimension,
            )

        try:
            response = await loop.run_in_executor(None, _call)

            if response.status_code == 200:
                embeddings = [item["embedding"] for item in response.output["embeddings"]]
                logger.debug(f"Generated {len(embeddings)} embeddings")
                return embeddings
            else:
                logger.error(f"Embedding API error: {response.code} - {response.message}")
                return None

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> Optional[List[List[float]]]:
        """Get embeddings for texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch (max 10 for DashScope)

        Returns:
            List of embedding vectors or None if failed
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embed_texts(batch)

            if embeddings is None:
                logger.error(f"Failed to embed batch {i // batch_size}")
                return None

            all_embeddings.extend(embeddings)

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings
