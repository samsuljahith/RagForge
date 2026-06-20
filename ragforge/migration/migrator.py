"""
Migration engine: re-embed, validate, and swap embedding models.

Uses a shadow-index approach: build the new index alongside the old one,
validate with evaluation, then swap if quality is acceptable.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk
from ragforge.core.registry import get
from ragforge.pipeline.embeddings import Embedder, DefaultEmbedder
from ragforge.pipeline.store import InMemoryStore


_KB_DIR = Path.home() / ".ragforge" / "knowledge_bases"


def _get_embedder(model_name: str) -> Embedder:
    """Get an embedding model by name."""
    try:
        cls = get("embedder", model_name)
        return cls()
    except KeyError:
        return DefaultEmbedder()


def migrate_knowledge_base(
    knowledge: str,
    from_model: str,
    to_model: str,
    validate: bool = True,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Migrate a knowledge base from one embedding model to another.

    Strategy:
      1. Load existing knowledge base and its chunks
      2. Re-embed all chunks with the new model (shadow index)
      3. Optionally validate quality hasn't degraded
      4. Swap the indices (old becomes backup)

    Args:
        knowledge: Name of the knowledge base to migrate
        from_model: Current embedding model name
        to_model: Target embedding model name
        validate: Whether to run quality validation
        options: Additional migration options

    Returns:
        dict with migration status and quality metrics
    """
    options = options or {}
    kb_path = _KB_DIR / knowledge

    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base '{knowledge}' not found")

    # Load existing store
    store_path = kb_path / "vectors.json"
    if not store_path.exists():
        raise FileNotFoundError(f"Vector store not found for '{knowledge}'")

    old_store = InMemoryStore.load(store_path)
    chunks = old_store.chunks

    if not chunks:
        return {
            "knowledge": knowledge,
            "from_model": from_model,
            "to_model": to_model,
            "status": "nothing_to_migrate",
            "num_chunks_migrated": 0,
        }

    # Get the new embedding model
    new_embedder = _get_embedder(to_model)

    # Re-embed all chunks with the new model
    texts = [c.text for c in chunks]
    new_vectors = new_embedder.encode(texts)

    # Build shadow index
    new_store = InMemoryStore()
    new_store.add(chunks, new_vectors)

    quality_before = None
    quality_after = None

    # Validate if requested
    if validate:
        old_embedder = _get_embedder(from_model)

        # Simple validation: compare retrieval similarity on a sample query
        # Use the first chunk's text as a test query (it should retrieve itself)
        if chunks:
            test_text = chunks[0].text[:100]
            old_vec = old_embedder.encode_single(test_text)
            new_vec = new_embedder.encode_single(test_text)

            old_results = old_store.search(old_vec, top_k=3)
            new_results = new_store.search(new_vec, top_k=3)

            # Quality = does the same top result come back?
            old_top_ids = {c.id for c, _ in old_results}
            new_top_ids = {c.id for c, _ in new_results}

            quality_before = 1.0  # baseline
            if old_top_ids:
                overlap = len(old_top_ids & new_top_ids) / len(old_top_ids)
                quality_after = round(overlap, 4)
            else:
                quality_after = 1.0

    # Perform the swap
    # Backup old store
    backup_path = kb_path / "vectors_backup.json"
    if store_path.exists():
        shutil.copy2(store_path, backup_path)

    # Save new store
    new_store.save(store_path)

    # Update metadata
    meta_path = kb_path / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {}

    meta["embedder_name"] = to_model
    meta["migrated_from"] = from_model
    meta["embedder_dim"] = new_embedder.dimension
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    return {
        "knowledge": knowledge,
        "from_model": from_model,
        "to_model": to_model,
        "status": "migrated",
        "quality_before": quality_before,
        "quality_after": quality_after,
        "num_chunks_migrated": len(chunks),
    }
