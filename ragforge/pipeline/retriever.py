"""
Hybrid retriever: dense + BM25 + Reciprocal Rank Fusion + optional reranking.

This is the core retrieval engine. It runs dense (vector) and sparse (BM25) search
together, fuses their ranked lists using RRF, and optionally re-scores the top
candidates with a cross-encoder reranker for maximum precision.

Modes:
    "dense"  — vector search only (fast, good for semantic similarity)
    "bm25"   — keyword search only (catches exact matches dense might miss)
    "hybrid" — both fused via RRF (default, best overall quality)

Reranking:
    When enabled, the top candidates from fusion are re-scored by a cross-encoder
    (default: cross-encoder/ms-marco-MiniLM-L-6-v2). This is optional — if the
    dependency isn't installed, reranking is silently skipped with a warning.
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

from ragforge.core.models import Chunk
from ragforge.pipeline.embeddings import Embedder
from ragforge.pipeline.store import VectorStore
from ragforge.pipeline.bm25 import BM25Index


# Type alias for retrieval mode
RetrievalMode = Literal["dense", "bm25", "hybrid"]


def reciprocal_rank_fusion(
    *ranked_lists: list[tuple[Chunk, float]],
    k: int = 60,
) -> list[tuple[Chunk, float]]:
    """
    Reciprocal Rank Fusion (RRF) — merges multiple ranked lists into one.

    RRF is model-free and score-agnostic: it only uses rank positions, making it
    robust when combining scores from different systems (cosine sim vs BM25 scores).

    Formula: RRF_score(d) = Σ 1 / (k + rank_i(d))
    where k is a constant (default 60, from the original RRF paper).

    Args:
        *ranked_lists: One or more lists of (chunk, score) pairs, each already
                       sorted by descending score.
        k: RRF constant. Higher values dampen the effect of rank differences.

    Returns:
        Merged list of (chunk, rrf_score) pairs, sorted by descending RRF score.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}

    for ranked_list in ranked_lists:
        for rank, (chunk, _score) in enumerate(ranked_list):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)
            chunk_map[chunk.id] = chunk

    # Sort by RRF score descending
    fused = [(chunk_map[cid], score) for cid, score in scores.items()]
    fused.sort(key=lambda x: x[1], reverse=True)
    return fused


class Retriever:
    """
    Hybrid retriever with configurable search modes and optional reranking.

    Ties together a VectorStore (dense search), a BM25Index (sparse search),
    and an Embedder (to encode queries). Fuses results via RRF and optionally
    re-scores with a cross-encoder.

    Usage:
        retriever = Retriever(embedder=emb, store=store, bm25=bm25)
        results = retriever.search("How do refunds work?", top_k=5, mode="hybrid")
        # -> [(chunk, score), ...]
    """

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        bm25: BM25Index,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        """
        Args:
            embedder: The embedding model (for encoding queries in dense search).
            store: The vector store containing indexed chunk embeddings.
            bm25: The BM25 keyword index over the same chunks.
            reranker_model: Cross-encoder model name for reranking (loaded on demand).
        """
        self.embedder = embedder
        self.store = store
        self.bm25 = bm25
        self._reranker_model_name = reranker_model
        self._reranker: Any = None  # Lazy-loaded cross-encoder

    def search(
        self,
        query: str,
        top_k: int = 5,
        mode: RetrievalMode = "hybrid",
        rerank: bool = False,
        rerank_top_n: int | None = None,
    ) -> list[tuple[Chunk, float]]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: The search query / question.
            top_k: Number of final results to return.
            mode: Search mode — "dense", "bm25", or "hybrid" (default).
            rerank: Whether to apply cross-encoder reranking on the top candidates.
            rerank_top_n: How many candidates to feed to the reranker (default: top_k * 3).

        Returns:
            List of (chunk, score) pairs, sorted by descending relevance.
        """
        if rerank_top_n is None:
            rerank_top_n = top_k * 3

        # Phase 1: Initial retrieval (depends on mode)
        candidates = self._retrieve(query, top_n=rerank_top_n if rerank else top_k, mode=mode)

        if not candidates:
            return []

        # Phase 2: Optional reranking
        if rerank:
            candidates = self._rerank(query, candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]

        return candidates

    def _retrieve(
        self,
        query: str,
        top_n: int,
        mode: RetrievalMode,
    ) -> list[tuple[Chunk, float]]:
        """Run the initial retrieval phase based on mode."""
        if mode == "dense":
            return self._dense_search(query, top_n)
        elif mode == "bm25":
            return self._bm25_search(query, top_n)
        elif mode == "hybrid":
            return self._hybrid_search(query, top_n)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode!r}. Use 'dense', 'bm25', or 'hybrid'.")

    def _dense_search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Pure dense (vector) search."""
        query_vector = self.embedder.encode_single(query)
        return self.store.search(query_vector, top_k=top_k)

    def _bm25_search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Pure BM25 (keyword) search."""
        return self.bm25.search(query, top_k=top_k)

    def _hybrid_search(self, query: str, top_n: int) -> list[tuple[Chunk, float]]:
        """
        Hybrid search: dense + BM25 fused via Reciprocal Rank Fusion.

        Retrieves top_n * 2 from each source to ensure good coverage before fusion.
        """
        fetch_k = top_n * 2
        dense_results = self._dense_search(query, fetch_k)
        bm25_results = self._bm25_search(query, fetch_k)

        # Fuse via RRF
        fused = reciprocal_rank_fusion(dense_results, bm25_results, k=60)
        return fused[:top_n]

    def _rerank(
        self,
        query: str,
        candidates: list[tuple[Chunk, float]],
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        """
        Re-score candidates using a cross-encoder reranker.

        Cross-encoders see (query, chunk_text) together, enabling much richer
        interaction modeling than bi-encoder similarity. This is slower but
        significantly more accurate for the final ranking.

        Degrades gracefully: if the cross-encoder dependency is not installed,
        logs a warning and returns candidates unchanged.
        """
        if not candidates:
            return []

        # Lazy-load the reranker
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(self._reranker_model_name)
            except ImportError:
                warnings.warn(
                    "Reranking requested but sentence-transformers is not installed. "
                    "Skipping reranking. Install with: pip install ragforge[pipeline]",
                    stacklevel=2,
                )
                return candidates[:top_k]
            except Exception as e:
                warnings.warn(
                    f"Failed to load reranker model '{self._reranker_model_name}': {e}. "
                    "Skipping reranking.",
                    stacklevel=2,
                )
                return candidates[:top_k]

        # Score all (query, chunk_text) pairs
        pairs = [(query, chunk.text) for chunk, _score in candidates]
        try:
            rerank_scores = self._reranker.predict(pairs)
        except Exception as e:
            warnings.warn(f"Reranking failed: {e}. Returning original ranking.", stacklevel=2)
            return candidates[:top_k]

        # Combine with reranker scores (reranker scores replace retrieval scores)
        reranked = [
            (chunk, float(rscore))
            for (chunk, _orig_score), rscore in zip(candidates, rerank_scores)
        ]
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked[:top_k]
