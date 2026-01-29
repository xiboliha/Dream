"""Vector store service using FAISS for similarity search."""

import json
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS package not installed. Install with: pip install faiss-cpu")


class VectorStore:
    """Vector store using FAISS for efficient similarity search."""

    def __init__(
        self,
        dimension: int = 1024,
        index_type: str = "flat",
        storage_path: Optional[str] = None,
    ):
        """Initialize vector store.

        Args:
            dimension: Embedding dimension
            index_type: FAISS index type ('flat' or 'ivf')
            storage_path: Path to store/load index
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS package is required. Install with: pip install faiss-cpu")

        self.dimension = dimension
        self.index_type = index_type
        self.storage_path = storage_path

        # Initialize FAISS index
        if index_type == "flat":
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity for normalized vectors)
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
        else:
            raise ValueError(f"Unknown index type: {index_type}")

        # Metadata storage (id -> metadata)
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self.id_counter = 0

        # Try to load existing index
        if storage_path and os.path.exists(storage_path):
            self.load()

        logger.info(f"Vector store initialized with dimension={dimension}, type={index_type}")

    def add(
        self,
        embeddings: List[List[float]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        """Add embeddings to the index.

        Args:
            embeddings: List of embedding vectors
            metadata_list: Optional metadata for each embedding

        Returns:
            List of assigned IDs
        """
        if not embeddings:
            return []

        # Convert to numpy array and normalize
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        # Assign IDs
        ids = list(range(self.id_counter, self.id_counter + len(embeddings)))
        self.id_counter += len(embeddings)

        # Add to index
        self.index.add(vectors)

        # Store metadata
        if metadata_list:
            for i, meta in enumerate(metadata_list):
                self.metadata[ids[i]] = meta

        logger.debug(f"Added {len(embeddings)} vectors to index, total: {self.index.ntotal}")
        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Search for similar vectors.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (id, score, metadata) tuples
        """
        if self.index.ntotal == 0:
            return []

        # Convert and normalize query
        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)

        # Search
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))

        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score >= threshold:
                meta = self.metadata.get(idx, {})
                results.append((int(idx), float(score), meta))

        return results

    def save(self, path: Optional[str] = None) -> None:
        """Save index and metadata to disk.

        Args:
            path: Storage path (uses self.storage_path if not provided)
        """
        save_path = path or self.storage_path
        if not save_path:
            logger.warning("No storage path specified, cannot save")
            return

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, f"{save_path}.faiss")

        # Save metadata
        meta_data = {
            "metadata": self.metadata,
            "id_counter": self.id_counter,
            "dimension": self.dimension,
            "index_type": self.index_type,
        }
        with open(f"{save_path}.meta", "wb") as f:
            pickle.dump(meta_data, f)

        logger.info(f"Vector store saved to {save_path}")

    def load(self, path: Optional[str] = None) -> bool:
        """Load index and metadata from disk.

        Args:
            path: Storage path (uses self.storage_path if not provided)

        Returns:
            True if loaded successfully
        """
        load_path = path or self.storage_path
        if not load_path:
            return False

        faiss_path = f"{load_path}.faiss"
        meta_path = f"{load_path}.meta"

        if not os.path.exists(faiss_path) or not os.path.exists(meta_path):
            return False

        try:
            # Load FAISS index
            self.index = faiss.read_index(faiss_path)

            # Load metadata
            with open(meta_path, "rb") as f:
                meta_data = pickle.load(f)

            self.metadata = meta_data["metadata"]
            self.id_counter = meta_data["id_counter"]

            logger.info(f"Vector store loaded from {load_path}, {self.index.ntotal} vectors")
            return True

        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            return False

    def clear(self) -> None:
        """Clear all vectors and metadata."""
        if self.index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)

        self.metadata.clear()
        self.id_counter = 0
        logger.info("Vector store cleared")

    @property
    def size(self) -> int:
        """Get number of vectors in the index."""
        return self.index.ntotal
