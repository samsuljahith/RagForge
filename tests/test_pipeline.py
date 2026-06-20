"""
Comprehensive tests for the pipeline module.

Covers:
  - Embeddings (DefaultEmbedder, mock-based tests for ST/OpenAI)
  - VectorStore (InMemoryStore: add, search, save/load, numpy vs python paths)
  - BM25 (add, search, save/load, edge cases)
  - Retriever (dense, bm25, hybrid modes + RRF fusion)
  - KnowledgeBase (build, query, save/load, end-to-end)
  - API endpoints (/knowledge, /query)
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ragforge.core.models import Chunk, Document
from ragforge.pipeline.embeddings import (
    Embedder,
    DefaultEmbedder,
    SentenceTransformerEmbedder,
    OpenAIEmbedder,
)
from ragforge.pipeline.store import InMemoryStore, VectorStore
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline.retriever import Retriever, reciprocal_rank_fusion
from ragforge.pipeline.knowledge import KnowledgeBase, build_knowledge_base, query_knowledge_base


# ===========================================================================
# Embeddings
# ===========================================================================


class TestDefaultEmbedder:
    def test_implements_interface(self):
        emb = DefaultEmbedder()
        assert isinstance(emb, Embedder)
        assert emb.dimension == 128
        assert emb.name == "default-hash-128d"

    def test_encode_returns_correct_shape(self):
        emb = DefaultEmbedder(dim=64)
        vecs = emb.encode(["hello world", "foo bar"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 64
        assert len(vecs[1]) == 64

    def test_encode_single(self):
        emb = DefaultEmbedder()
        vec = emb.encode_single("test text")
        assert len(vec) == 128

    def test_is_normalized(self):
        emb = DefaultEmbedder()
        vec = emb.encode_single("some text content here")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_empty_text_returns_zeros(self):
        emb = DefaultEmbedder()
        vec = emb.encode_single("")
        assert all(x == 0.0 for x in vec)

    def test_similar_texts_have_higher_similarity(self):
        emb = DefaultEmbedder()
        v1 = emb.encode_single("the cat sat on the mat")
        v2 = emb.encode_single("the cat sat on a mat")
        v3 = emb.encode_single("quantum physics and black holes")
        sim_12 = sum(a * b for a, b in zip(v1, v2))
        sim_13 = sum(a * b for a, b in zip(v1, v3))
        assert sim_12 > sim_13

    def test_deterministic(self):
        emb = DefaultEmbedder()
        v1 = emb.encode_single("hello world")
        v2 = emb.encode_single("hello world")
        assert v1 == v2

    def test_batch_equals_single(self):
        emb = DefaultEmbedder()
        texts = ["hello", "world", "test"]
        batch = emb.encode(texts)
        singles = [emb.encode_single(t) for t in texts]
        assert batch == singles

    def test_custom_dim(self):
        emb = DefaultEmbedder(dim=32)
        assert emb.dimension == 32
        vec = emb.encode_single("test")
        assert len(vec) == 32


class TestSentenceTransformerEmbedder:
    def test_raises_import_error_without_dep(self):
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="sentence-transformers"):
                SentenceTransformerEmbedder()


class TestOpenAIEmbedder:
    def test_raises_import_error_without_dep(self):
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai"):
                OpenAIEmbedder()

    def test_raises_value_error_without_api_key(self):
        # Mock openai being importable but no key set
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            with patch.dict("os.environ", {}, clear=True):
                import os
                with patch.object(os.environ, "get", return_value=None):
                    with pytest.raises((ValueError, ImportError)):
                        OpenAIEmbedder()


# ===========================================================================
# Vector Store
# ===========================================================================


class TestInMemoryStore:
    def _make_chunks_and_vectors(self):
        chunks = [
            Chunk(text="cats are great pets", doc_id="d1", index=0, id="c1"),
            Chunk(text="dogs are loyal friends", doc_id="d1", index=1, id="c2"),
            Chunk(text="quantum physics is hard", doc_id="d1", index=2, id="c3"),
        ]
        emb = DefaultEmbedder()
        vectors = emb.encode([c.text for c in chunks])
        return chunks, vectors

    def test_add_and_count(self):
        store = InMemoryStore()
        chunks, vectors = self._make_chunks_and_vectors()
        store.add(chunks, vectors)
        assert store.count() == 3

    def test_add_mismatched_lengths_raises(self):
        store = InMemoryStore()
        with pytest.raises(ValueError, match="same length"):
            store.add([Chunk(text="x", doc_id="d", index=0)], [[1.0], [2.0]])

    def test_search_returns_sorted_by_score(self):
        store = InMemoryStore()
        chunks, vectors = self._make_chunks_and_vectors()
        store.add(chunks, vectors)

        emb = DefaultEmbedder()
        query_vec = emb.encode_single("tell me about cats")
        results = store.search(query_vec, top_k=3)

        assert len(results) == 3
        # Scores should be descending
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)
        # Cat chunk should rank first
        assert results[0][0].id == "c1"

    def test_search_respects_top_k(self):
        store = InMemoryStore()
        chunks, vectors = self._make_chunks_and_vectors()
        store.add(chunks, vectors)

        emb = DefaultEmbedder()
        results = store.search(emb.encode_single("cats"), top_k=1)
        assert len(results) == 1

    def test_search_empty_store(self):
        store = InMemoryStore()
        results = store.search([1.0, 0.0, 0.0], top_k=5)
        assert results == []

    def test_chunks_property(self):
        store = InMemoryStore()
        chunks, vectors = self._make_chunks_and_vectors()
        store.add(chunks, vectors)
        assert store.chunks == chunks

    def test_save_and_load(self, tmp_path):
        store = InMemoryStore()
        chunks, vectors = self._make_chunks_and_vectors()
        store.add(chunks, vectors)

        path = tmp_path / "store.json"
        store.save(path)
        assert path.exists()

        loaded = InMemoryStore.load(path)
        assert loaded.count() == 3
        assert loaded.chunks[0].text == "cats are great pets"
        assert loaded.chunks[0].id == "c1"

        # Verify search still works after load
        emb = DefaultEmbedder()
        results = loaded.search(emb.encode_single("cats"), top_k=1)
        assert results[0][0].id == "c1"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            InMemoryStore.load(tmp_path / "nonexistent.json")

    def test_incremental_add(self):
        store = InMemoryStore()
        emb = DefaultEmbedder()

        c1 = [Chunk(text="first batch", doc_id="d1", index=0)]
        store.add(c1, emb.encode(["first batch"]))
        assert store.count() == 1

        c2 = [Chunk(text="second batch", doc_id="d1", index=1)]
        store.add(c2, emb.encode(["second batch"]))
        assert store.count() == 2


# ===========================================================================
# BM25
# ===========================================================================


class TestBM25Index:
    def _make_index(self):
        bm25 = BM25Index()
        chunks = [
            Chunk(text="the quick brown fox jumps over the lazy dog", doc_id="d1", index=0, id="c1"),
            Chunk(text="machine learning is a subset of artificial intelligence", doc_id="d1", index=1, id="c2"),
            Chunk(text="the fox ran quickly through the dark forest", doc_id="d1", index=2, id="c3"),
            Chunk(text="product SKU-12345 is available in warehouse B", doc_id="d1", index=3, id="c4"),
        ]
        bm25.add(chunks)
        return bm25, chunks

    def test_basic_search(self):
        bm25, _ = self._make_index()
        results = bm25.search("fox", top_k=2)
        assert len(results) == 2
        result_ids = [c.id for c, _ in results]
        assert "c1" in result_ids
        assert "c3" in result_ids

    def test_exact_keyword_match(self):
        bm25, _ = self._make_index()
        results = bm25.search("SKU-12345", top_k=1)
        # Should find the product chunk via keyword matching
        assert len(results) >= 1

    def test_empty_query(self):
        bm25, _ = self._make_index()
        results = bm25.search("", top_k=5)
        assert results == []

    def test_no_match(self):
        bm25, _ = self._make_index()
        results = bm25.search("xyznonexistentterm", top_k=5)
        assert results == []

    def test_empty_index(self):
        bm25 = BM25Index()
        results = bm25.search("anything", top_k=5)
        assert results == []

    def test_scores_are_positive(self):
        bm25, _ = self._make_index()
        results = bm25.search("fox jumps", top_k=5)
        for _, score in results:
            assert score > 0

    def test_chunks_property(self):
        bm25, chunks = self._make_index()
        assert bm25.chunks == chunks

    def test_save_and_load(self, tmp_path):
        bm25, _ = self._make_index()
        path = tmp_path / "bm25.json"
        bm25.save(path)
        assert path.exists()

        loaded = BM25Index.load(path)
        assert len(loaded.chunks) == 4

        # Verify search works after load
        results = loaded.search("fox", top_k=2)
        assert len(results) == 2
        result_ids = [c.id for c, _ in results]
        assert "c1" in result_ids

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            BM25Index.load(tmp_path / "nonexistent.json")

    def test_incremental_add(self):
        bm25 = BM25Index()
        bm25.add([Chunk(text="hello world", doc_id="d1", index=0)])
        bm25.add([Chunk(text="world hello again", doc_id="d1", index=1)])
        results = bm25.search("hello", top_k=5)
        assert len(results) == 2


# ===========================================================================
# Retriever & RRF
# ===========================================================================


class TestReciprocalRankFusion:
    def test_single_list(self):
        chunks = [
            Chunk(text="first", doc_id="d1", index=0, id="c1"),
            Chunk(text="second", doc_id="d1", index=1, id="c2"),
        ]
        ranked = [(chunks[0], 0.9), (chunks[1], 0.5)]
        fused = reciprocal_rank_fusion(ranked, k=60)
        assert len(fused) == 2
        assert fused[0][0].id == "c1"  # Higher rank → higher RRF score

    def test_two_lists_boost_overlap(self):
        c1 = Chunk(text="shared", doc_id="d1", index=0, id="shared")
        c2 = Chunk(text="only dense", doc_id="d1", index=1, id="dense_only")
        c3 = Chunk(text="only bm25", doc_id="d1", index=2, id="bm25_only")

        dense = [(c1, 0.9), (c2, 0.7)]
        bm25 = [(c1, 5.0), (c3, 3.0)]

        fused = reciprocal_rank_fusion(dense, bm25, k=60)
        # "shared" appears in both lists → highest RRF score
        assert fused[0][0].id == "shared"
        assert fused[0][1] > fused[1][1]

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([], [], k=60)
        assert fused == []


class TestRetriever:
    def _build_retriever(self):
        emb = DefaultEmbedder(dim=64)
        store = InMemoryStore()
        bm25 = BM25Index()

        chunks = [
            Chunk(text="refunds are processed within 30 days of purchase", doc_id="d1", index=0, id="c1"),
            Chunk(text="shipping takes 5 to 7 business days worldwide", doc_id="d1", index=1, id="c2"),
            Chunk(text="product code SKU-99887 is currently out of stock", doc_id="d1", index=2, id="c3"),
            Chunk(text="our refund policy covers all items except final sale", doc_id="d1", index=3, id="c4"),
        ]
        vectors = emb.encode([c.text for c in chunks])
        store.add(chunks, vectors)
        bm25.add(chunks)

        return Retriever(embedder=emb, store=store, bm25=bm25), chunks

    def test_dense_mode(self):
        retriever, _ = self._build_retriever()
        results = retriever.search("refund policy", top_k=2, mode="dense")
        assert len(results) == 2
        # Should return chunks with scores
        for chunk, score in results:
            assert isinstance(chunk, Chunk)
            assert isinstance(score, float)

    def test_bm25_mode(self):
        retriever, _ = self._build_retriever()
        results = retriever.search("refund refunds policy", top_k=2, mode="bm25")
        assert len(results) >= 1
        # BM25 should find refund-related chunks
        texts = [c.text for c, _ in results]
        assert any("refund" in t for t in texts)

    def test_hybrid_mode(self):
        retriever, _ = self._build_retriever()
        results = retriever.search("refund policy", top_k=3, mode="hybrid")
        assert len(results) == 3
        # Hybrid should find refund chunks (both dense and bm25 agree)
        ids = [c.id for c, _ in results]
        assert "c1" in ids or "c4" in ids

    def test_bm25_catches_exact_codes(self):
        retriever, _ = self._build_retriever()
        # BM25 should catch the exact product code that dense might miss
        results = retriever.search("SKU-99887", top_k=2, mode="bm25")
        assert any(c.id == "c3" for c, _ in results)

    def test_hybrid_default_mode(self):
        retriever, _ = self._build_retriever()
        # Default should be hybrid
        results = retriever.search("shipping time", top_k=2)
        assert len(results) == 2

    def test_invalid_mode_raises(self):
        retriever, _ = self._build_retriever()
        with pytest.raises(ValueError, match="Unknown retrieval mode"):
            retriever.search("test", mode="invalid")  # type: ignore

    def test_rerank_without_dep_degrades_gracefully(self):
        retriever, _ = self._build_retriever()
        # Reranking should not crash even if sentence-transformers isn't available
        # (it warns and returns original order)
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            retriever._reranker = None  # Reset cached reranker
            results = retriever.search("refund", top_k=2, mode="hybrid", rerank=True)
            assert len(results) == 2

    def test_top_k_respected(self):
        retriever, _ = self._build_retriever()
        results = retriever.search("refund shipping product", top_k=1, mode="hybrid")
        assert len(results) == 1


# ===========================================================================
# KnowledgeBase
# ===========================================================================


class TestKnowledgeBase:
    def test_build_from_files(self, tmp_path):
        (tmp_path / "doc1.md").write_text("# Refunds\n\nRefunds are processed within 30 days.")
        (tmp_path / "doc2.md").write_text("# Shipping\n\nShipping takes 5-7 business days.")

        kb = KnowledgeBase.build(
            name="test-kb-build",
            sources=[str(tmp_path)],
            embedder="default",
            chunk_strategy="structure",
            persist=False,
        )

        assert kb.name == "test-kb-build"
        assert kb.num_documents == 2
        assert kb.num_chunks >= 2
        assert kb.embedder.name == "default-hash-128d"

    def test_query_modes(self, tmp_path):
        (tmp_path / "doc.md").write_text(
            "# Refunds\n\nRefunds within 30 days.\n\n"
            "# Shipping\n\nShipping takes 5 days.\n\n"
            "# Code\n\nProduct SKU-55555 in stock."
        )

        kb = KnowledgeBase.build(name="test-kb-modes", sources=[str(tmp_path)], persist=False)

        # Dense mode
        results = kb.query("refund policy", top_k=2, mode="dense")
        assert len(results) <= 2

        # BM25 mode
        results = kb.query("refund", top_k=2, mode="bm25")
        assert len(results) <= 2

        # Hybrid mode (default)
        results = kb.query("refund policy", top_k=2, mode="hybrid")
        assert len(results) <= 2

    def test_save_and_load(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Hello\n\nThis is a test document with content.")

        kb = KnowledgeBase.build(
            name="test-kb-persist",
            sources=[str(tmp_path)],
            persist=False,
        )

        # Save to custom dir
        save_dir = tmp_path / "kbs"
        kb.save(base_dir=save_dir)
        assert (save_dir / "test-kb-persist" / "meta.json").exists()
        assert (save_dir / "test-kb-persist" / "vectors.json").exists()
        assert (save_dir / "test-kb-persist" / "bm25.json").exists()

        # Load
        loaded = KnowledgeBase.load("test-kb-persist", base_dir=save_dir)
        assert loaded.name == "test-kb-persist"
        assert loaded.num_chunks == kb.num_chunks

        # Query loaded KB
        results = loaded.query("hello", top_k=2)
        assert len(results) >= 1

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            KnowledgeBase.load("nonexistent-kb", base_dir=tmp_path)

    def test_exists(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nContent here.")
        save_dir = tmp_path / "kbs"

        assert not KnowledgeBase.exists("test-exists", base_dir=save_dir)

        kb = KnowledgeBase.build(name="test-exists", sources=[str(tmp_path)], persist=False)
        kb.save(base_dir=save_dir)

        assert KnowledgeBase.exists("test-exists", base_dir=save_dir)

    def test_empty_sources(self, tmp_path):
        # Empty directory = 0 documents
        empty = tmp_path / "empty"
        empty.mkdir()
        kb = KnowledgeBase.build(name="test-empty", sources=[str(empty)], persist=False)
        assert kb.num_chunks == 0
        assert kb.num_documents == 0

    def test_repr(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Hello world")
        kb = KnowledgeBase.build(name="test-repr", sources=[str(tmp_path)], persist=False)
        r = repr(kb)
        assert "test-repr" in r
        assert "default-hash-128d" in r


# ===========================================================================
# Functional interface (used by API/CLI)
# ===========================================================================


class TestFunctionalInterface:
    def test_build_knowledge_base(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Refunds\n\nRefund within 30 days.")

        result = build_knowledge_base(
            name="test-func-build",
            sources=[str(tmp_path)],
            embedding_model="default",
            chunk_strategy="structure",
        )

        assert result["status"] == "built"
        assert result["name"] == "test-func-build"
        assert result["num_documents"] == 1
        assert result["num_chunks"] >= 1
        assert result["embedding_model"] == "default-hash-128d"

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-func-build"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_knowledge_base(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Refunds\n\nRefunds processed within 30 days.")

        build_knowledge_base(
            name="test-func-query",
            sources=[str(tmp_path)],
        )

        result = query_knowledge_base(
            knowledge="test-func-query",
            question="How long for refunds?",
            top_k=2,
            mode="hybrid",
            rerank=False,
        )

        assert result["question"] == "How long for refunds?"
        assert result["knowledge"] == "test-func-query"
        assert len(result["chunks"]) <= 2
        for chunk in result["chunks"]:
            assert "id" in chunk
            assert "text" in chunk
            assert "score" in chunk

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-func-query"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_missing_kb(self):
        with pytest.raises(FileNotFoundError):
            query_knowledge_base(knowledge="totally-nonexistent-kb", question="test")


# ===========================================================================
# API endpoint tests
# ===========================================================================


class TestAPIEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app

        return TestClient(app)

    def test_knowledge_build(self, client, tmp_path):
        (tmp_path / "test.md").write_text("# API Test\n\nContent for API testing.")

        resp = client.post("/knowledge", json={
            "name": "api-test-kb",
            "sources": [str(tmp_path)],
            "embedding_model": "default",
            "chunk_strategy": "structure",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "built"
        assert data["num_documents"] >= 1

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-test-kb"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_missing_kb(self, client):
        resp = client.post("/query", json={
            "knowledge": "nonexistent-api-kb",
            "question": "test question",
            "top_k": 3,
            "mode": "hybrid",
            "rerank": False,
        })
        assert resp.status_code == 404

    def test_query_with_mode(self, client, tmp_path):
        (tmp_path / "test.md").write_text("# Refunds\n\nRefunds within 30 days.")

        # Build first
        client.post("/knowledge", json={
            "name": "api-query-test",
            "sources": [str(tmp_path)],
        })

        # Query with each mode
        for mode in ["dense", "bm25", "hybrid"]:
            resp = client.post("/query", json={
                "knowledge": "api-query-test",
                "question": "refund policy",
                "top_k": 2,
                "mode": mode,
                "rerank": False,
            })
            assert resp.status_code == 200, f"Failed for mode={mode}: {resp.text}"
            data = resp.json()
            assert data["question"] == "refund policy"
            assert isinstance(data["chunks"], list)

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-query-test"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_validation(self, client):
        # Invalid mode should be rejected by Pydantic
        resp = client.post("/query", json={
            "knowledge": "x",
            "question": "test",
            "mode": "invalid_mode",
        })
        assert resp.status_code == 422  # Validation error
