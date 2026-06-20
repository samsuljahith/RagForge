"""
Embedding models for the RAGForge pipeline.

Every embedder follows the same contract: texts in, vectors out. The registry
makes them discoverable by name so the CLI, API, and KnowledgeBase can all
look up "sentence-transformers" or "openai" without hard-coding imports.

Architecture:
    Embedder (ABC)
    ├── DefaultEmbedder      — hash-based, zero deps, always available
    ├── SentenceTransformerEmbedder — local models via sentence-transformers [pipeline extra]
    └── OpenAIEmbedder       — OpenAI API via env key [openai extra]

The default path (DefaultEmbedder) works with NO heavy dependencies so anyone
can try the pipeline immediately. Real quality comes from the optional backends.
"""

from __future__ import annotations

import abc
import hashlib
import math
from collections import Counter
from typing import Any

from ragforge.core.registry import register


class Embedder(abc.ABC):
    """
    Base class for all embedding models.

    Subclass this, implement encode() and dimension, then register via:
        @register("embedder", "my-backend")
    """

    @abc.abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a batch of texts into vectors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of vectors, one per input text. Each vector has length == self.dimension.
        """
        ...

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the output vectors."""
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name for this embedder (e.g. 'BAAI/bge-small-en-v1.5')."""
        ...

    def encode_single(self, text: str) -> list[float]:
        """Convenience: embed a single text. Default calls encode() with a 1-item list."""
        return self.encode([text])[0]


# ---------------------------------------------------------------------------
# Default embedder: hash-based, zero dependencies, always available
# ---------------------------------------------------------------------------


@register("embedder", "default")
class DefaultEmbedder(Embedder):
    """
    A deterministic hash-based pseudo-embedder. Zero external dependencies.

    NOT production quality — but it lets the full pipeline (build → query → retrieve)
    work out-of-the-box so developers can try RAGForge before installing heavy ML deps.

    Strategy: hash each word into a bucket in a fixed-size vector, weight by frequency,
    then L2-normalize. Similar texts share words → similar vectors.
    """

    def __init__(self, dim: int = 128, model_name: str = "default-hash-128d") -> None:
        self._dim = dim
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode texts using deterministic hashing."""
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        words = text.lower().split()
        if not words:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        word_counts = Counter(words)

        for word, count in word_counts.items():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self._dim
            weight = 1.0 + math.log(count)
            sign = 1.0 if (h // self._dim) % 2 == 0 else -1.0
            vec[idx] += sign * weight

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


# ---------------------------------------------------------------------------
# Sentence-transformers embedder: local models, high quality, heavy dep
# ---------------------------------------------------------------------------


@register("embedder", "sentence-transformers")
class SentenceTransformerEmbedder(Embedder):
    """
    Local embedding models via the sentence-transformers library.

    Default model: BAAI/bge-small-en-v1.5 (fast, good quality, 384d).
    The model is downloaded on first use and cached locally.

    Install: pip install ragforge[pipeline]
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", **kwargs: Any) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for the 'sentence-transformers' embedder.\n"
                "Install it with:  pip install ragforge[pipeline]\n"
                "Or directly:      pip install sentence-transformers"
            )
        self._model_name = model_name
        self._model = SentenceTransformer(model_name, **kwargs)
        self._dim: int = self._model.get_sentence_embedding_dimension()  # type: ignore[assignment]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Batch encode using the sentence-transformers model."""
        # sentence-transformers returns numpy arrays; convert to list[list[float]]
        embeddings = self._model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()


# ---------------------------------------------------------------------------
# OpenAI embedder: remote API, needs OPENAI_API_KEY env var
# ---------------------------------------------------------------------------


@register("embedder", "openai")
class OpenAIEmbedder(Embedder):
    """
    OpenAI embedding models via the API.

    Default model: text-embedding-3-small (1536d).
    Requires OPENAI_API_KEY environment variable.

    Install: pip install ragforge[openai]
    """

    def __init__(self, model_name: str = "text-embedding-3-small", **kwargs: Any) -> None:
        import os

        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for the OpenAI embedder.\n"
                "Install it with:  pip install ragforge[openai]\n"
                "Or directly:      pip install openai"
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set.\n"
                "Set it with:  export OPENAI_API_KEY='sk-...'"
            )

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, **kwargs)
        self._model_name = model_name
        # Dimension lookup for known models
        self._dim = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }.get(model_name, 1536)

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Batch encode via the OpenAI embeddings API.

        Handles batching internally (OpenAI supports up to ~2048 texts per call).
        """
        if not texts:
            return []

        batch_size = 2048
        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.embeddings.create(input=batch, model=self._model_name)
            # Response data is sorted by index
            batch_vectors = [item.embedding for item in response.data]
            all_vectors.extend(batch_vectors)

        return all_vectors


# ---------------------------------------------------------------------------
# Backward-compatible aliases (the old code used EmbeddingModel/DefaultEmbedding)
# ---------------------------------------------------------------------------

# Keep these so existing code (quantization, migration modules) doesn't break
EmbeddingModel = Embedder
DefaultEmbedding = DefaultEmbedder
