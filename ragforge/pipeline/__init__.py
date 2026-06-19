"""
Pipeline module: embed, store, and retrieve chunks — the heart of RAG.

Turns Chunks into a working retrieval system: embed chunks, store them in a
vector store, retrieve the best ones for a query with hybrid search (dense + BM25)
and optional reranking.

The embedding model and vector store are pluggable via the registry, so you can
swap providers without rewriting your pipeline.

Quick start:
    from ragforge.pipeline import build_knowledge_base, query_knowledge_base

    result = build_knowledge_base(
        name="my-kb",
        sources=["docs/"],
        embedding_model="default",
    )
    answer = query_knowledge_base(knowledge="my-kb", question="How do refunds work?")
"""

from ragforge.pipeline.embeddings import EmbeddingModel, DefaultEmbedding
from ragforge.pipeline.store import VectorStore, InMemoryStore
from ragforge.pipeline.retriever import build_knowledge_base, query_knowledge_base

__all__ = [
    "EmbeddingModel",
    "DefaultEmbedding",
    "VectorStore",
    "InMemoryStore",
    "build_knowledge_base",
    "query_knowledge_base",
]
