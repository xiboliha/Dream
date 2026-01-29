"""Qdrant vector store for large-scale dialogue retrieval."""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant client not installed. Install with: pip install qdrant-client")


def _to_uuid(id_str: str) -> str:
    """Convert string ID to UUID format for Qdrant compatibility."""
    # If already a valid UUID, return as-is
    try:
        uuid.UUID(id_str)
        return id_str
    except ValueError:
        pass
    # Generate deterministic UUID from string
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, id_str))


class QdrantStore:
    """Vector store using Qdrant for large-scale similarity search."""

    def __init__(
        self,
        collection_name: str = "dialogues",
        dimension: int = 1024,
        host: str = "localhost",
        port: int = 6333,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_memory: bool = False,
    ):
        """Initialize Qdrant store.

        Args:
            collection_name: Name of the collection
            dimension: Embedding dimension
            host: Qdrant server host
            port: Qdrant server port
            url: Full URL (overrides host/port)
            api_key: API key for Qdrant Cloud
            use_memory: Use in-memory storage (for testing)
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant client is required. Install with: pip install qdrant-client")

        self.collection_name = collection_name
        self.dimension = dimension

        # Initialize client
        if use_memory:
            self.client = QdrantClient(":memory:")
            logger.info("Qdrant initialized with in-memory storage")
        elif url:
            self.client = QdrantClient(url=url, api_key=api_key)
            logger.info(f"Qdrant initialized with URL: {url}")
        else:
            self.client = QdrantClient(host=host, port=port)
            logger.info(f"Qdrant initialized at {host}:{port}")

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure the collection exists, create if not."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE,
                ),
                # Optimize for large datasets
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,  # Start indexing after 20k points
                ),
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Using existing collection: {self.collection_name}")

    def add(
        self,
        embeddings: List[List[float]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add embeddings to the collection.

        Args:
            embeddings: List of embedding vectors
            metadata_list: Optional metadata for each embedding
            ids: Optional IDs (generated if not provided)

        Returns:
            List of assigned IDs
        """
        if not embeddings:
            return []

        # Generate UUIDs if not provided, or convert string IDs to UUIDs
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in embeddings]
        else:
            ids = [_to_uuid(id_str) for id_str in ids]

        # Build points
        points = []
        for i, (emb, point_id) in enumerate(zip(embeddings, ids)):
            payload = metadata_list[i] if metadata_list else {}
            points.append(PointStruct(
                id=point_id,
                vector=emb,
                payload=payload,
            ))

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

        logger.debug(f"Added {len(embeddings)} vectors to Qdrant")
        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        filter_conditions: Optional[Dict] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            filter_conditions: Optional filter conditions

        Returns:
            List of (id, score, payload) tuples
        """
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
            query_filter = models.Filter(must=must_conditions)

        # Search
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            score_threshold=threshold,
            query_filter=query_filter,
        ).points

        # Format results
        formatted = []
        for hit in results:
            formatted.append((
                str(hit.id),
                hit.score,
                hit.payload or {},
            ))

        return formatted

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs.

        Args:
            ids: List of IDs to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=ids),
            )
            logger.debug(f"Deleted {len(ids)} vectors from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    def clear(self) -> None:
        """Clear all vectors in the collection."""
        self.client.delete_collection(self.collection_name)
        self._ensure_collection()
        logger.info(f"Cleared collection: {self.collection_name}")

    @property
    def size(self) -> int:
        """Get number of vectors in the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
