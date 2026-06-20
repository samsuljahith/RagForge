"""
Pipeline module: embed, store, and retrieve chunks — the heart of RAG.

Turns Chunks into a working retrieval system: embed chunks, store them in a
vector store, retrieve the best ones for a query with hybrid search (dense + BM25)
and optional cross-encoder reranking.

The embedding model and vector store are pluggable via the registry, so you can
swap providers without rewriting your pipeline.

Quick start (library):
    from ragforge.pipeline import KnowledgeBase

    kb = KnowledgeBase.build(name="my-kb", sources=["docs/"])
    results = kb.query("How do refunds work?", mode="hybrid")
    for chunk, score in results:
        print(f"  [{score:.4f}] {chunk.text[:80]}...")

Quick start (functional, used by API/CLI):
    from ragforge.pipeline import build_knowledge_base, query_knowledge_base

    build_knowledge_base(name="my-kb", sources=["docs/"])
    result = query_knowledge_base(knowledge="my-kb", question="refund policy?")
"""

# Core abstractions
from ragforge.pipeline.embeddings import Embedder, DefaultEmbedder
from ragforge.pipeline.store import VectorStore, InMemoryStore
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline.retriever import Retriever, reciprocal_rank_fusion, RetrievalMode

# The main orchestrator
from ragforge.pipeline.knowledge import KnowledgeBase

# Functional interface (used by API routes and CLI)
from ragforge.pipeline.knowledge import build_knowledge_base, query_knowledge_base

# Backward-compatible aliases (used by quantization/migration modules)
from ragforge.pipeline.embeddings import EmbeddingModel, DefaultEmbedding

__all__ = [
    # Abstractions
    "Embedder",
    "VectorStore",
    "BM25Index",
    "Retriever",
    "RetrievalMode",
    # Implementations
    "DefaultEmbedder",
    "InMemoryStore",
    # Orchestrator
    "KnowledgeBase",
    # Functional API
    "build_knowledge_base",
    "query_knowledge_base",
    # Utilities
    "reciprocal_rank_fusion",
    # Backward compat
    "EmbeddingModel",
    "DefaultEmbedding",
]
