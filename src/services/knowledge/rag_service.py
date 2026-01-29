"""RAG (Retrieval-Augmented Generation) service for dialogue retrieval."""

import json
import os
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.services.ai.embedding_service import EmbeddingService


class DialogueRAG:
    """RAG service for retrieving similar dialogue examples."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: Union["VectorStore", "QdrantStore"],
        dataset_path: Optional[str] = None,
        use_qdrant: bool = False,
    ):
        """Initialize RAG service.

        Args:
            embedding_service: Embedding service for text vectorization
            vector_store: Vector store for similarity search (FAISS or Qdrant)
            dataset_path: Path to dialogue dataset JSON file
            use_qdrant: Whether using Qdrant store
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.use_qdrant = use_qdrant
        self.dataset_path = dataset_path or os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "config", "knowledge", "dialogue_dataset.json"
        )
        self._initialized = False

        logger.info(f"DialogueRAG service created (backend: {'Qdrant' if use_qdrant else 'FAISS'})")

    async def initialize(self, force_rebuild: bool = False) -> bool:
        """Initialize RAG by loading and indexing dialogue dataset.

        Args:
            force_rebuild: Force rebuild index even if exists

        Returns:
            True if initialized successfully
        """
        if self._initialized and not force_rebuild:
            return True

        # Check if index already exists
        if not force_rebuild and self.vector_store.size > 0:
            logger.info(f"Using existing index with {self.vector_store.size} vectors")
            self._initialized = True
            return True

        # Load dataset
        dialogues = self._load_dataset()
        if not dialogues:
            # For Qdrant, we might have data already in the database
            if self.use_qdrant and self.vector_store.size > 0:
                logger.info(f"Using existing Qdrant data with {self.vector_store.size} vectors")
                self._initialized = True
                return True
            logger.warning("No dialogues loaded, RAG will be disabled")
            return False

        # Build index
        success = await self._build_index(dialogues)
        if success:
            self._initialized = True
            # Save index for FAISS (Qdrant persists automatically)
            if not self.use_qdrant and hasattr(self.vector_store, 'save'):
                self.vector_store.save()

        return success

    def _load_dataset(self) -> List[Dict[str, Any]]:
        """Load dialogue dataset from JSON file.

        Returns:
            List of dialogue entries
        """
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            dialogues = data.get("dialogues", [])
            logger.info(f"Loaded {len(dialogues)} dialogues from dataset")
            return dialogues

        except FileNotFoundError:
            logger.warning(f"Dataset file not found: {self.dataset_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse dataset: {e}")
            return []

    async def _build_index(self, dialogues: List[Dict[str, Any]]) -> bool:
        """Build vector index from dialogues.

        Args:
            dialogues: List of dialogue entries

        Returns:
            True if built successfully
        """
        if not dialogues:
            return False

        # Clear existing index
        self.vector_store.clear()

        # Extract user messages for embedding
        texts = [d["user"] for d in dialogues]

        # Get embeddings
        logger.info(f"Generating embeddings for {len(texts)} dialogues...")
        embeddings = await self.embedding_service.embed_batch(texts)

        if embeddings is None:
            logger.error("Failed to generate embeddings")
            return False

        # Prepare metadata
        metadata_list = [
            {
                "id": d.get("id", f"dialogue_{i}"),
                "user": d["user"],
                "response": d["response"],
                "category": d.get("category", ""),
                "mood": d.get("mood", "neutral"),
            }
            for i, d in enumerate(dialogues)
        ]

        # Add to index
        if self.use_qdrant:
            ids = [m["id"] for m in metadata_list]
            self.vector_store.add(embeddings, metadata_list, ids)
        else:
            self.vector_store.add(embeddings, metadata_list)

        logger.info(f"Built index with {self.vector_store.size} vectors")
        return True

    async def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5,
        filter_conditions: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar dialogues.

        Args:
            query: User query text
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            filter_conditions: Optional filter (Qdrant only)

        Returns:
            List of similar dialogue entries with scores
        """
        if not self._initialized:
            logger.warning("RAG not initialized, returning empty results")
            return []

        # Get query embedding
        query_embedding = await self.embedding_service.embed_text(query)
        if query_embedding is None:
            logger.error("Failed to embed query")
            return []

        # Search
        if self.use_qdrant and filter_conditions:
            results = self.vector_store.search(query_embedding, top_k, threshold, filter_conditions)
        else:
            results = self.vector_store.search(query_embedding, top_k, threshold)

        # Format results
        formatted = []
        for idx, score, meta in results:
            formatted.append({
                "id": meta.get("id"),
                "user": meta.get("user"),
                "response": meta.get("response"),
                "category": meta.get("category"),
                "mood": meta.get("mood"),
                "score": score,
            })

        logger.debug(f"Found {len(formatted)} similar dialogues for query: {query[:30]}...")
        return formatted

    def build_context_prompt(
        self,
        similar_dialogues: List[Dict[str, Any]],
        max_examples: int = 3,
    ) -> str:
        """Build context prompt from similar dialogues.

        Args:
            similar_dialogues: List of similar dialogue results
            max_examples: Maximum examples to include

        Returns:
            Formatted prompt string
        """
        if not similar_dialogues:
            return ""

        lines = ["## 相似对话参考（根据语义匹配）", ""]

        for i, d in enumerate(similar_dialogues[:max_examples]):
            score_pct = int(d["score"] * 100)
            lines.append(f"【示例{i+1}】相似度: {score_pct}%")
            lines.append(f"用户: {d['user']}")
            lines.append(f"回复: {d['response']}")
            if d.get("mood") and d["mood"] != "neutral":
                lines.append(f"情绪: {d['mood']}")
            lines.append("")

        lines.append("请参考以上示例的回复风格，但不要完全照搬。根据实际情况自然回复。")
        lines.append("")

        return "\n".join(lines)

    async def add_dialogue(
        self,
        user: str,
        response: str,
        category: str = "",
        mood: str = "neutral",
        dialogue_id: Optional[str] = None,
    ) -> bool:
        """Add a new dialogue to the index.

        Args:
            user: User message
            response: AI response
            category: Dialogue category
            mood: Response mood
            dialogue_id: Optional dialogue ID

        Returns:
            True if added successfully
        """
        # Get embedding
        embedding = await self.embedding_service.embed_text(user)
        if embedding is None:
            return False

        # Add to index
        metadata = {
            "id": dialogue_id or f"dynamic_{self.vector_store.size}",
            "user": user,
            "response": response,
            "category": category,
            "mood": mood,
        }

        if self.use_qdrant:
            self.vector_store.add([embedding], [metadata], [metadata["id"]])
        else:
            self.vector_store.add([embedding], [metadata])

        logger.debug(f"Added new dialogue to index: {user[:30]}...")
        return True

    async def add_dialogues_batch(
        self,
        dialogues: List[Dict[str, Any]],
    ) -> int:
        """Add multiple dialogues to the index.

        Args:
            dialogues: List of dialogue dicts with user, response, category, mood

        Returns:
            Number of dialogues added
        """
        if not dialogues:
            return 0

        texts = [d["user"] for d in dialogues]
        embeddings = await self.embedding_service.embed_batch(texts)

        if embeddings is None:
            return 0

        metadata_list = [
            {
                "id": d.get("id", f"batch_{i}"),
                "user": d["user"],
                "response": d["response"],
                "category": d.get("category", ""),
                "mood": d.get("mood", "neutral"),
            }
            for i, d in enumerate(dialogues)
        ]

        if self.use_qdrant:
            ids = [m["id"] for m in metadata_list]
            self.vector_store.add(embeddings, metadata_list, ids)
        else:
            self.vector_store.add(embeddings, metadata_list)

        return len(dialogues)

    @property
    def is_initialized(self) -> bool:
        """Check if RAG is initialized."""
        return self._initialized

    @property
    def index_size(self) -> int:
        """Get number of indexed dialogues."""
        return self.vector_store.size

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG statistics."""
        stats = {
            "initialized": self._initialized,
            "index_size": self.vector_store.size,
            "backend": "qdrant" if self.use_qdrant else "faiss",
        }
        if self.use_qdrant and hasattr(self.vector_store, 'get_stats'):
            stats.update(self.vector_store.get_stats())
        return stats
