"""
Vector store implementations for the RAGForge pipeline.

The default InMemoryStore uses numpy for fast cosine similarity when available,
falling back to pure-Python math when numpy is not installed. This means the
pipeline works with ZERO heavy deps but gets a speed boost with numpy.

Architecture:
    VectorStore (ABC)
    └── InMemoryStore — brute-force cosine sim, save/load to disk, always available

Adding a real vector DB (Qdrant, Chroma, Pinecone, etc.) is just another class
that implements VectorStore and registers itself. The KnowledgeBase and Retriever
don't care which backend is behind the interface.
"""

from __future__ import annotations

import abc
import json
import math
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk
from ragforge.core.registry import register

# Try numpy for fast cosine similarity; fall back to pure Python if unavailable
try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


class VectorStore(abc.ABC):
    """
    Base class for vector stores.

    Every store must support:
      - add(chunks, vectors): index new data
      - search(query_vector, top_k): find similar chunks
      - count(): how many chunks are stored
      - save/load: persistence to/from disk

    Register new backends with @register("store", "my-backend").
    """

    @abc.abstractmethod
    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Store chunks with their embedding vectors."""
        ...

    @abc.abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Find the top-k most similar chunks to the query vector.

        Returns:
            List of (chunk, score) pairs, sorted by descending similarity score.
        """
        ...

    @abc.abstractmethod
    def count(self) -> int:
        """Number of stored chunks."""
        ...

    @property
    def chunks(self) -> list[Chunk]:
        """Access all stored chunks (for BM25 index rebuilding, etc.)."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, path: str | Path) -> None:
        """Persist the store to disk."""
        ...

    @classmethod
    @abc.abstractmethod
    def load(cls, path: str | Path) -> "VectorStore":
        """Load a store from disk."""
        ...


@register("store", "memory")
class InMemoryStore(VectorStore):
    """
    In-memory vector store with cosine similarity search.

    Uses numpy for fast batch cosine similarity when available (recommended for
    datasets > 1000 chunks). Falls back to pure-Python for zero-dependency operation.

    Good for development and datasets up to ~50k chunks. For larger datasets,
    register a dedicated vector DB (Qdrant, Chroma, etc.) via the plugin system.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []
        # Numpy matrix cache (lazily built on first search)
        self._np_matrix: Any = None

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """
        Add chunks with their embedding vectors to the store.

        Args:
            chunks: List of Chunk objects to store.
            vectors: Corresponding embedding vectors (same length as chunks).

        Raises:
            ValueError: If chunks and vectors have different lengths.
        """
        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks and vectors must have the same length "
                f"(got {len(chunks)} chunks, {len(vectors)} vectors)"
            )
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)
        # Invalidate numpy cache
        self._np_matrix = None

    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Find the top-k most similar chunks using cosine similarity.

        Uses numpy batch operations when available for ~10-50x speedup on large stores.
        Falls back to pure-Python loop otherwise.
        """
        if not self._chunks:
            return []

        if _HAS_NUMPY:
            return self._search_numpy(query_vector, top_k)
        return self._search_python(query_vector, top_k)

    def _search_numpy(self, query_vector: list[float], top_k: int) -> list[tuple[Chunk, float]]:
        """Fast cosine similarity search using numpy."""
        # Build/use cached matrix
        if self._np_matrix is None:
            self._np_matrix = np.array(self._vectors, dtype=np.float32)
            # Pre-normalize rows for cosine sim
            norms = np.linalg.norm(self._np_matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            self._np_matrix = self._np_matrix / norms

        query = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        query = query / query_norm

        # Batch cosine similarity (dot product of normalized vectors)
        scores = self._np_matrix @ query

        # Get top-k indices
        k = min(top_k, len(self._chunks))
        # argpartition is O(n) vs argsort O(n log n)
        if k < len(scores):
            top_indices = np.argpartition(scores, -k)[-k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        else:
            top_indices = np.argsort(scores)[::-1][:k]

        return [(self._chunks[i], float(scores[i])) for i in top_indices]

    def _search_python(self, query_vector: list[float], top_k: int) -> list[tuple[Chunk, float]]:
        """Pure-Python fallback cosine similarity search."""
        query_norm = math.sqrt(sum(x * x for x in query_vector))
        if query_norm == 0:
            return []

        scored: list[tuple[Chunk, float]] = []
        for chunk, vec in zip(self._chunks, self._vectors):
            dot = sum(a * b for a, b in zip(query_vector, vec))
            vec_norm = math.sqrt(sum(x * x for x in vec))
            if vec_norm == 0:
                scored.append((chunk, 0.0))
            else:
                scored.append((chunk, dot / (query_norm * vec_norm)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        """Number of stored chunks."""
        return len(self._chunks)

    @property
    def chunks(self) -> list[Chunk]:
        """Access all stored chunks."""
        return self._chunks

    def save(self, path: str | Path) -> None:
        """
        Persist the store to a JSON file.

        The file contains serialized chunks and their vectors.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chunks": [c.to_dict() for c in self._chunks],
            "vectors": self._vectors,
        }
        p.write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "InMemoryStore":
        """Load a store from a JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Store not found: {path}")
        data = json.loads(p.read_text(encoding="utf-8"))
        store = cls()
        store._chunks = [Chunk.from_dict(c) for c in data["chunks"]]
        store._vectors = data["vectors"]
        return store
