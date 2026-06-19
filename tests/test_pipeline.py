"""Tests for the pipeline module."""

import pytest
import shutil
from pathlib import Path

from ragforge.core.models import Chunk, Document
from ragforge.pipeline.embeddings import DefaultEmbedding
from ragforge.pipeline.store import InMemoryStore
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline import build_knowledge_base, query_knowledge_base


class TestDefaultEmbedding:
    def test_dimension(self):
        model = DefaultEmbedding(dim=64)
        assert model.dimension == 64

    def test_embed_returns_correct_size(self):
        model = DefaultEmbedding(dim=128)
        vec = model.embed("hello world")
        assert len(vec) == 128

    def test_embed_is_normalized(self):
        import math
        model = DefaultEmbedding()
        vec = model.embed("some text content")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_similar_texts_have_similar_embeddings(self):
        model = DefaultEmbedding()
        v1 = model.embed("the cat sat on the mat")
        v2 = model.embed("the cat sat on a mat")
        v3 = model.embed("quantum physics and black holes")
        # v1 and v2 should be more similar to each other than to v3
        sim_12 = sum(a * b for a, b in zip(v1, v2))
        sim_13 = sum(a * b for a, b in zip(v1, v3))
        assert sim_12 > sim_13

    def test_empty_text(self):
        model = DefaultEmbedding()
        vec = model.embed("")
        assert all(x == 0.0 for x in vec)

    def test_embed_batch(self):
        model = DefaultEmbedding()
        vecs = model.embed_batch(["hello", "world"])
        assert len(vecs) == 2
        assert len(vecs[0]) == model.dimension


class TestInMemoryStore:
    def test_add_and_search(self):
        store = InMemoryStore()
        chunks = [
            Chunk(text="cats are great", doc_id="d1", index=0),
            Chunk(text="dogs are loyal", doc_id="d1", index=1),
            Chunk(text="quantum physics", doc_id="d1", index=2),
        ]
        model = DefaultEmbedding()
        vectors = model.embed_batch([c.text for c in chunks])
        store.add(chunks, vectors)

        assert store.count() == 3

        # Search for something about cats
        query_vec = model.embed("tell me about cats")
        results = store.search(query_vec, top_k=2)
        assert len(results) == 2
        # The cat chunk should score highest
        assert results[0][0].text == "cats are great"

    def test_save_and_load(self, tmp_path):
        store = InMemoryStore()
        chunks = [Chunk(text="test chunk", doc_id="d1", index=0, id="c1")]
        vectors = [[1.0, 0.0, 0.0]]
        store.add(chunks, vectors)

        path = tmp_path / "store.json"
        store.save(path)

        loaded = InMemoryStore.load(path)
        assert loaded.count() == 1
        assert loaded._chunks[0].text == "test chunk"

    def test_empty_search(self):
        store = InMemoryStore()
        results = store.search([1.0, 0.0], top_k=5)
        assert results == []


class TestBM25:
    def test_basic_search(self):
        bm25 = BM25Index()
        chunks = [
            Chunk(text="the quick brown fox jumps over the lazy dog", doc_id="d1", index=0),
            Chunk(text="machine learning is a subset of artificial intelligence", doc_id="d1", index=1),
            Chunk(text="the fox ran quickly through the forest", doc_id="d1", index=2),
        ]
        bm25.add(chunks)

        results = bm25.search("fox", top_k=2)
        assert len(results) == 2
        # Both fox-related chunks should rank highest
        result_texts = [c.text for c, _ in results]
        assert any("fox" in t for t in result_texts)

    def test_empty_query(self):
        bm25 = BM25Index()
        chunks = [Chunk(text="hello world", doc_id="d1", index=0)]
        bm25.add(chunks)
        results = bm25.search("", top_k=5)
        assert results == []

    def test_no_results(self):
        bm25 = BM25Index()
        results = bm25.search("anything", top_k=5)
        assert results == []


class TestKnowledgeBase:
    def test_build_and_query(self, tmp_path):
        # Create test files
        (tmp_path / "doc1.md").write_text("# Refunds\n\nRefunds are processed within 30 days.")
        (tmp_path / "doc2.md").write_text("# Shipping\n\nShipping takes 5-7 business days.")

        result = build_knowledge_base(
            name="test-kb",
            sources=[str(tmp_path)],
            embedding_model="default",
            chunk_strategy="structure",
        )
        assert result["status"] == "built"
        assert result["num_documents"] == 2
        assert result["num_chunks"] >= 2

        # Query
        query_result = query_knowledge_base(
            knowledge="test-kb",
            question="How long do refunds take?",
            top_k=2,
        )
        assert query_result["question"] == "How long do refunds take?"
        assert len(query_result["chunks"]) <= 2

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-kb"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_missing_kb(self):
        with pytest.raises(FileNotFoundError):
            query_knowledge_base(
                knowledge="nonexistent-kb",
                question="test",
            )
