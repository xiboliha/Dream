"""Batch import script for dialogue data into Qdrant."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger


async def import_dialogues(
    input_file: str,
    api_key: str,
    qdrant_url: str = None,
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    collection_name: str = "dialogues",
    batch_size: int = 100,
    embedding_batch_size: int = 10,
    use_memory: bool = False,
):
    """Import dialogues from JSON file into Qdrant.

    Args:
        input_file: Path to JSON file with dialogues
        api_key: DashScope API key for embeddings
        qdrant_url: Qdrant server URL (optional)
        qdrant_host: Qdrant host
        qdrant_port: Qdrant port
        collection_name: Qdrant collection name
        batch_size: Number of dialogues per batch for Qdrant
        embedding_batch_size: Number of texts per embedding API call
        use_memory: Use in-memory Qdrant (for testing)
    """
    from src.services.ai.embedding_service import EmbeddingService
    from src.services.knowledge.qdrant_store import QdrantStore

    # Load dialogues
    logger.info(f"Loading dialogues from {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    dialogues = data.get("dialogues", [])
    if not dialogues:
        logger.error("No dialogues found in input file")
        return

    logger.info(f"Found {len(dialogues)} dialogues to import")

    # Initialize services
    embedding_service = EmbeddingService(
        api_key=api_key,
        model="text-embedding-v3",
        dimension=1024,
    )

    qdrant_store = QdrantStore(
        collection_name=collection_name,
        dimension=1024,
        host=qdrant_host,
        port=qdrant_port,
        url=qdrant_url,
        use_memory=use_memory,
    )

    # Process in batches
    total_imported = 0
    total_batches = (len(dialogues) + batch_size - 1) // batch_size

    for batch_idx in range(0, len(dialogues), batch_size):
        batch = dialogues[batch_idx:batch_idx + batch_size]
        current_batch = batch_idx // batch_size + 1

        logger.info(f"Processing batch {current_batch}/{total_batches} ({len(batch)} dialogues)")

        # Extract texts for embedding
        texts = [d["user"] for d in batch]

        # Generate embeddings
        embeddings = await embedding_service.embed_batch(texts, batch_size=embedding_batch_size)
        if embeddings is None:
            logger.error(f"Failed to generate embeddings for batch {current_batch}")
            continue

        # Prepare metadata
        metadata_list = [
            {
                "id": d.get("id", f"dialogue_{batch_idx + i}"),
                "user": d["user"],
                "response": d["response"],
                "category": d.get("category", ""),
                "mood": d.get("mood", "neutral"),
            }
            for i, d in enumerate(batch)
        ]

        # Prepare IDs
        ids = [m["id"] for m in metadata_list]

        # Add to Qdrant
        qdrant_store.add(embeddings, metadata_list, ids)
        total_imported += len(batch)

        logger.info(f"Imported {total_imported}/{len(dialogues)} dialogues")

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.1)

    # Print stats
    stats = qdrant_store.get_stats()
    logger.info(f"Import complete! Total vectors in collection: {stats.get('points_count', 0)}")


async def import_from_csv(
    input_file: str,
    api_key: str,
    user_column: str = "user",
    response_column: str = "response",
    category_column: str = "category",
    mood_column: str = "mood",
    **kwargs,
):
    """Import dialogues from CSV file.

    Args:
        input_file: Path to CSV file
        api_key: DashScope API key
        user_column: Column name for user message
        response_column: Column name for response
        category_column: Column name for category
        mood_column: Column name for mood
        **kwargs: Additional arguments for import_dialogues
    """
    import csv

    logger.info(f"Loading CSV from {input_file}")

    dialogues = []
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            dialogues.append({
                "id": f"csv_{i}",
                "user": row.get(user_column, ""),
                "response": row.get(response_column, ""),
                "category": row.get(category_column, ""),
                "mood": row.get(mood_column, "neutral"),
            })

    # Save as temp JSON and import
    temp_file = input_file + ".temp.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump({"dialogues": dialogues}, f, ensure_ascii=False)

    try:
        await import_dialogues(temp_file, api_key, **kwargs)
    finally:
        os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser(description="Import dialogue data into Qdrant")
    parser.add_argument("input_file", help="Input file (JSON or CSV)")
    parser.add_argument("--api-key", required=True, help="DashScope API key")
    parser.add_argument("--qdrant-url", help="Qdrant server URL")
    parser.add_argument("--qdrant-host", default="localhost", help="Qdrant host")
    parser.add_argument("--qdrant-port", type=int, default=6333, help="Qdrant port")
    parser.add_argument("--collection", default="dialogues", help="Collection name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for Qdrant")
    parser.add_argument("--embedding-batch-size", type=int, default=10, help="Batch size for embeddings")
    parser.add_argument("--memory", action="store_true", help="Use in-memory Qdrant")

    # CSV specific options
    parser.add_argument("--user-column", default="user", help="CSV column for user message")
    parser.add_argument("--response-column", default="response", help="CSV column for response")
    parser.add_argument("--category-column", default="category", help="CSV column for category")
    parser.add_argument("--mood-column", default="mood", help="CSV column for mood")

    args = parser.parse_args()

    # Determine file type
    if args.input_file.endswith(".csv"):
        asyncio.run(import_from_csv(
            args.input_file,
            args.api_key,
            user_column=args.user_column,
            response_column=args.response_column,
            category_column=args.category_column,
            mood_column=args.mood_column,
            qdrant_url=args.qdrant_url,
            qdrant_host=args.qdrant_host,
            qdrant_port=args.qdrant_port,
            collection_name=args.collection,
            batch_size=args.batch_size,
            embedding_batch_size=args.embedding_batch_size,
            use_memory=args.memory,
        ))
    else:
        asyncio.run(import_dialogues(
            args.input_file,
            args.api_key,
            qdrant_url=args.qdrant_url,
            qdrant_host=args.qdrant_host,
            qdrant_port=args.qdrant_port,
            collection_name=args.collection,
            batch_size=args.batch_size,
            embedding_batch_size=args.embedding_batch_size,
            use_memory=args.memory,
        ))


if __name__ == "__main__":
    main()
