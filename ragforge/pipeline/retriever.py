"""
High-level pipeline operations: build knowledge bases and query them.

This module ties together parsing, chunking, embedding, and storage into
simple top-level functions that the API and CLI call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk, Document
from ragforge.core.registry import get
from ragforge.parsing import parse_file
from ragforge.chunking import chunk_document
from ragforge.pipeline.embeddings import EmbeddingModel, DefaultEmbedding
from ragforge.pipeline.store import InMemoryStore, VectorStore
from ragforge.pipeline.bm25 import BM25Index

# Store location for persisted knowledge bases
_KB_DIR = Path.home() / ".ragforge" / "knowledge_bases"


def _get_kb_path(name: str) -> Path:
    return _KB_DIR / name


def _get_embedding_model(model_name: str) -> EmbeddingModel:
    """Get an embedding model by name from the registry."""
    try:
        cls = get("embedding", model_name)
        return cls()
    except KeyError:
        # Fallback to default
        return DefaultEmbedding()


def build_knowledge_base(
    name: str,
    sources: list[str],
    embedding_model: str = "default",
    chunk_strategy: str = "structure",
    chunk_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a knowledge base: parse sources, chunk, embed, and store.

    Args:
        name: Name for the knowledge base (used for persistence)
        sources: File paths to parse and index
        embedding_model: Name of the embedding model to use
        chunk_strategy: Chunking strategy ('fixed' or 'structure')
        chunk_options: Options passed to the chunker

    Returns:
        dict with build results (name, status, counts, model used)
    """
    chunk_options = chunk_options or {}
    embedder = _get_embedding_model(embedding_model)
    store = InMemoryStore()
    bm25 = BM25Index()

    all_chunks: list[Chunk] = []
    num_documents = 0

    for source in sources:
        p = Path(source)
        if p.is_dir():
            files = [f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".")]
        else:
            files = [p]

        for file_path in files:
            try:
                doc = parse_file(str(file_path))
                chunks = chunk_document(doc, strategy=chunk_strategy, **chunk_options)
                all_chunks.extend(chunks)
                num_documents += 1
            except (ValueError, ImportError):
                # Skip files we can't parse
                continue

    if all_chunks:
        # Embed and store
        texts = [c.text for c in all_chunks]
        vectors = embedder.embed_batch(texts)
        store.add(all_chunks, vectors)
        bm25.add(all_chunks)

    # Persist
    kb_path = _get_kb_path(name)
    kb_path.mkdir(parents=True, exist_ok=True)
    store.save(kb_path / "vectors.json")

    # Save BM25 index data and metadata
    meta = {
        "name": name,
        "embedding_model": embedding_model,
        "chunk_strategy": chunk_strategy,
        "chunk_options": chunk_options,
        "num_documents": num_documents,
        "num_chunks": len(all_chunks),
        "embedding_dim": embedder.dimension,
    }
    (kb_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    return {
        "name": name,
        "status": "built",
        "num_documents": num_documents,
        "num_chunks": len(all_chunks),
        "embedding_model": embedding_model,
    }


def query_knowledge_base(
    knowledge: str,
    question: str,
    top_k: int = 5,
    rerank: bool = True,
) -> dict[str, Any]:
    """
    Query a knowledge base with hybrid search (dense + BM25) and optional reranking.

    Args:
        knowledge: Name of the knowledge base
        question: The question to answer
        top_k: Number of results to return
        rerank: Whether to apply reranking

    Returns:
        dict with question, knowledge name, retrieved chunks, and optional answer
    """
    kb_path = _get_kb_path(knowledge)
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base '{knowledge}' not found")

    # Load metadata and store
    meta = json.loads((kb_path / "meta.json").read_text(encoding="utf-8"))
    store = InMemoryStore.load(kb_path / "vectors.json")

    # Get embedding model
    embedder = _get_embedding_model(meta.get("embedding_model", "default"))

    # Dense search
    query_vector = embedder.embed(question)
    dense_results = store.search(query_vector, top_k=top_k * 2)

    # BM25 search (rebuild index from stored chunks)
    bm25 = BM25Index()
    # Get all chunks from the store for BM25
    all_chunks = store._chunks  # Access internal for BM25 rebuild
    if all_chunks:
        bm25.add(all_chunks)
    sparse_results = bm25.search(question, top_k=top_k * 2)

    # Hybrid: combine scores with Reciprocal Rank Fusion (RRF)
    chunk_scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}
    k = 60  # RRF constant

    for rank, (chunk, _score) in enumerate(dense_results):
        chunk_scores[chunk.id] = chunk_scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)
        chunk_map[chunk.id] = chunk

    for rank, (chunk, _score) in enumerate(sparse_results):
        chunk_scores[chunk.id] = chunk_scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)
        chunk_map[chunk.id] = chunk

    # Sort by combined score
    ranked = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

    # Simple reranking: boost chunks that have query terms as exact matches
    if rerank:
        query_terms = set(question.lower().split())
        reranked = []
        for chunk_id, score in ranked:
            chunk = chunk_map[chunk_id]
            chunk_lower = chunk.text.lower()
            # Boost for exact phrase overlap
            match_count = sum(1 for t in query_terms if t in chunk_lower)
            boost = 1.0 + (match_count / max(1, len(query_terms))) * 0.5
            reranked.append((chunk_id, score * boost))
        ranked = sorted(reranked, key=lambda x: x[1], reverse=True)

    # Take top_k
    final_chunks = []
    for chunk_id, score in ranked[:top_k]:
        chunk = chunk_map[chunk_id]
        final_chunks.append({
            "id": chunk.id,
            "text": chunk.text,
            "doc_id": chunk.doc_id,
            "index": chunk.index,
            "metadata": chunk.metadata,
            "score": round(score, 4),
        })

    return {
        "question": question,
        "knowledge": knowledge,
        "chunks": final_chunks,
        "answer": None,  # Answer generation requires an LLM — future feature
    }
