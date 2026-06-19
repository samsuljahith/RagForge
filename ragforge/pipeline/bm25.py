"""
BM25 sparse retrieval for hybrid search.

BM25 complements dense (vector) search by handling keyword matches that dense
embeddings sometimes miss. The hybrid approach combines both for better recall.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from ragforge.core.models import Chunk


class BM25Index:
    """
    In-memory BM25 index for sparse retrieval.

    Standard BM25 implementation with configurable k1 and b parameters.
    Used alongside dense search in hybrid retrieval.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._doc_freqs: Counter = Counter()  # word -> num docs containing it
        self._doc_lens: list[int] = []
        self._doc_terms: list[Counter] = []  # term frequencies per doc
        self._avg_dl: float = 0.0
        self._n: int = 0

    def add(self, chunks: list[Chunk]) -> None:
        """Index chunks for BM25 retrieval."""
        for chunk in chunks:
            terms = self._tokenize(chunk.text)
            tf = Counter(terms)
            self._chunks.append(chunk)
            self._doc_terms.append(tf)
            self._doc_lens.append(len(terms))
            for term in set(terms):
                self._doc_freqs[term] += 1

        self._n = len(self._chunks)
        self._avg_dl = sum(self._doc_lens) / max(1, self._n)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Search using BM25 scoring. Returns (chunk, score) pairs."""
        query_terms = self._tokenize(query)
        if not query_terms or not self._chunks:
            return []

        scores: list[float] = []
        for i in range(self._n):
            score = 0.0
            dl = self._doc_lens[i]
            tf_doc = self._doc_terms[i]
            for term in query_terms:
                if term not in tf_doc:
                    continue
                tf = tf_doc[term]
                df = self._doc_freqs.get(term, 0)
                # IDF with smoothing
                idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 term score
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self._avg_dl)
                score += idf * numerator / denominator
            scores.append(score)

        # Rank by score
        ranked = sorted(
            [(self._chunks[i], scores[i]) for i in range(self._n)],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        import re
        return re.findall(r'\b\w+\b', text.lower())
