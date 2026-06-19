"""
Embedding models for the pipeline.

The default embedding uses a simple TF-IDF-like approach (no external dependencies).
For production, swap in sentence-transformers or OpenAI embeddings via the registry.

All embedding models follow the same contract: text in, vector out.
"""

from __future__ import annotations

import abc
import math
import hashlib
from collections import Counter

from ragforge.core.registry import register


class EmbeddingModel(abc.ABC):
    """Base class for embedding models. Maps text to a fixed-size vector."""

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector."""
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. Default: call embed() in a loop."""
        return [self.embed(t) for t in texts]

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """The dimensionality of the output vectors."""
        raise NotImplementedError


@register("embedding", "default")
class DefaultEmbedding(EmbeddingModel):
    """
    A simple hash-based embedding that requires no external dependencies.

    This is NOT production quality — it's a deterministic pseudo-embedding that
    allows the pipeline to work out-of-the-box for testing and development.
    For real use, install sentence-transformers and use a proper model.

    Strategy: hash each word to a bucket in a fixed-size vector, weight by frequency.
    Similar texts will have similar vectors because they share words.
    """

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        words = text.lower().split()
        if not words:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        word_counts = Counter(words)

        for word, count in word_counts.items():
            # Hash word to get a deterministic bucket index
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self._dim
            # Use log frequency weighting
            weight = 1.0 + math.log(count)
            # Alternate sign based on second hash to spread values
            sign = 1.0 if (h // self._dim) % 2 == 0 else -1.0
            vec[idx] += sign * weight

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
