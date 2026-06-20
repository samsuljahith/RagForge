"""
BM25 sparse retrieval for hybrid search.

BM25 complements dense (vector) search by handling exact keyword matches that
embedding models sometimes miss — product codes, IDs, model numbers, unusual
proper nouns. The hybrid approach (dense + BM25 fused via RRF) consistently
outperforms either alone.

This implementation is pure-Python with no external dependencies. For very large
corpora, the `rank-bm25` package (available via the [pipeline] extra) could be
used as a drop-in replacement behind the same interface.

Persistence: save/load to JSON so the BM25 index can be stored alongside the
vector store in a KnowledgeBase.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk


class BM25Index:
    """
    In-memory BM25 index for sparse retrieval.

    Standard BM25 (Okapi BM25) implementation with configurable k1 and b parameters.
    Used alongside dense search in hybrid retrieval via Reciprocal Rank Fusion.

    Usage:
        bm25 = BM25Index()
        bm25.add(chunks)
        results = bm25.search("product SKU-123", top_k=5)
        # -> [(chunk, score), ...]
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        """
        Args:
            k1: Term frequency saturation parameter (higher = more weight to frequency).
            b:  Length normalization (0 = no normalization, 1 = full normalization).
        """
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._doc_freqs: Counter = Counter()  # term -> num docs containing it
        self._doc_lens: list[int] = []
        self._doc_terms: list[Counter] = []  # per-doc term frequency counters
        self._avg_dl: float = 0.0
        self._n: int = 0

    def add(self, chunks: list[Chunk]) -> None:
        """
        Index chunks for BM25 retrieval.

        Can be called multiple times to add more chunks incrementally.
        """
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
        """
        Search using BM25 scoring.

        Args:
            query: The search query string.
            top_k: Number of top results to return.

        Returns:
            List of (chunk, score) pairs, sorted by descending BM25 score.
            Only chunks with score > 0 are returned.
        """
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
                # IDF with smoothing (Robertson-Sparck Jones formula)
                idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 term score
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self._avg_dl)
                score += idf * numerator / denominator
            scores.append(score)

        # Rank by score, filter out zeros
        ranked = sorted(
            [(self._chunks[i], scores[i]) for i in range(self._n) if scores[i] > 0],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]

    @property
    def chunks(self) -> list[Chunk]:
        """Access all indexed chunks."""
        return self._chunks

    def save(self, path: str | Path) -> None:
        """
        Persist the BM25 index to a JSON file.

        Saves the indexed chunks and precomputed statistics so the index
        can be rebuilt without re-tokenizing everything.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k1": self.k1,
            "b": self.b,
            "chunks": [c.to_dict() for c in self._chunks],
            "doc_freqs": dict(self._doc_freqs),
            "doc_lens": self._doc_lens,
            "doc_terms": [dict(tf) for tf in self._doc_terms],
            "avg_dl": self._avg_dl,
            "n": self._n,
        }
        p.write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        """Load a BM25 index from a JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"BM25 index not found: {path}")
        data = json.loads(p.read_text(encoding="utf-8"))

        bm25 = cls(k1=data.get("k1", 1.5), b=data.get("b", 0.75))
        bm25._chunks = [Chunk.from_dict(c) for c in data["chunks"]]
        bm25._doc_freqs = Counter(data["doc_freqs"])
        bm25._doc_lens = data["doc_lens"]
        bm25._doc_terms = [Counter(tf) for tf in data["doc_terms"]]
        bm25._avg_dl = data["avg_dl"]
        bm25._n = data["n"]
        return bm25

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        Simple whitespace + lowercase tokenization.

        Splits on word boundaries, lowercases, keeps alphanumeric tokens.
        Good enough for BM25 keyword matching (not meant to be a full NLP pipeline).
        """
        return re.findall(r"\b\w+\b", text.lower())
