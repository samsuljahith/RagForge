"""
Vector store implementations.

The default is an in-memory store using brute-force cosine similarity. It works
for development and small datasets. For production, register a proper store
(Qdrant, Chroma, Pinecone, etc.) via the registry.
"""

from __future__ import annotations

import abc
import json
import math
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk
from ragforge.core.registry import register


class VectorStore(abc.ABC):
    """Base class for vector stores."""

    @abc.abstractmethod
    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Store chunks with their embedding vectors."""
        raise NotImplementedError

    @abc.abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Find the top-k most similar chunks to the query vector. Returns (chunk, score) pairs."""
        raise NotImplementedError

    @abc.abstractmethod
    def count(self) -> int:
        """Number of stored chunks."""
        raise NotImplementedError

    def save(self, path: str | Path) -> None:
        """Persist the store to disk (optional, not all stores support this)."""
        raise NotImplementedError(f"{type(self).__name__} does not support save()")

    @classmethod
    def load(cls, path: str | Path) -> "VectorStore":
        """Load a store from disk."""
        raise NotImplementedError(f"{cls.__name__} does not support load()")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@register("store", "memory")
class InMemoryStore(VectorStore):
    """
    In-memory vector store with brute-force cosine similarity search.

    Good for development and small datasets (< 10k chunks). For larger datasets,
    use a dedicated vector database registered via the plugin system.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[Chunk, float]]:
        if not self._chunks:
            return []

        scored = [
            (chunk, _cosine_similarity(query_vector, vec))
            for chunk, vec in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return len(self._chunks)

    def save(self, path: str | Path) -> None:
        """Save to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chunks": [c.to_dict() for c in self._chunks],
            "vectors": self._vectors,
        }
        p.write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "InMemoryStore":
        """Load from a JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Store not found: {path}")
        data = json.loads(p.read_text(encoding="utf-8"))
        store = cls()
        store._chunks = [Chunk.from_dict(c) for c in data["chunks"]]
        store._vectors = data["vectors"]
        return store
