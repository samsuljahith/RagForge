"""
Tests for the Migration Decision Gate.

Uses mocked embedders (no real model downloads) to test:
- Gate returns GO when new model has higher recall
- Gate returns NO_GO when new model regresses
- Threshold/margin logic
- Hot-set identification
- Smoke test passes on good index, fails on broken one
- CLI argument parsing
"""

from __future__ import annotations

import pytest

from ragforge.core.models import Chunk
from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.pipeline.embeddings import Embedder
from ragforge.migration.gate import (
    run_decision_gate,
    GateDecision,
    identify_hot_set,
    smoke_test,
    SmokeTestResult,
    GATE_METRICS,
)


# ─── Mock Embedders ────────────────────────────────────────────────────────────

class GoodEmbedder(Embedder):
    """Mock embedder that produces vectors placing relevant chunks near queries."""

    @property
    def name(self) -> str:
        return "good-mock"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        # Chunks about "refund" get a vector near [1,0,0,0]
        # Chunks about "shipping" get a vector near [0,1,0,0]
        if "refund" in text.lower():
            return [0.9, 0.1, 0.0, 0.0]
        elif "shipping" in text.lower():
            return [0.1, 0.9, 0.0, 0.0]
        else:
            return [0.3, 0.3, 0.3, 0.1]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class BadEmbedder(Embedder):
    """Mock embedder that produces random-ish vectors (poor retrieval)."""

    @property
    def name(self) -> str:
        return "bad-mock"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        # Everything maps to roughly the same vector — can't distinguish anything
        return [0.5, 0.5, 0.5, 0.5]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class SlightlyBetterEmbedder(Embedder):
    """Mock embedder slightly better than GoodEmbedder — stronger signal."""

    @property
    def name(self) -> str:
        return "better-mock"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        if "refund" in text.lower():
            return [1.0, 0.0, 0.0, 0.0]
        elif "shipping" in text.lower():
            return [0.0, 1.0, 0.0, 0.0]
        else:
            return [0.0, 0.0, 0.5, 0.5]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


# ─── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_chunks():
    return [
        Chunk(text="Our refund policy allows returns within 30 days.", doc_id="doc1", index=0, id="chunk-refund-1"),
        Chunk(text="Refund processing takes 3-5 business days.", doc_id="doc1", index=1, id="chunk-refund-2"),
        Chunk(text="Shipping takes 2-7 days depending on location.", doc_id="doc2", index=0, id="chunk-shipping-1"),
        Chunk(text="Express shipping is available for $15 extra.", doc_id="doc2", index=1, id="chunk-shipping-2"),
        Chunk(text="Contact support at help@example.com.", doc_id="doc3", index=0, id="chunk-other"),
    ]


@pytest.fixture
def sample_golden():
    return GoldenDataset(items=[
        GoldenItem(
            question="What is the refund window?",
            relevant_chunk_ids=["chunk-refund-1", "chunk-refund-2"],
        ),
        GoldenItem(
            question="How long does shipping take?",
            relevant_chunk_ids=["chunk-shipping-1", "chunk-shipping-2"],
        ),
    ])


# ─── Decision Gate Tests ───────────────────────────────────────────────────────

class TestDecisionGate:
    """Core gate logic tests."""

    def test_go_when_new_model_is_better(self, sample_chunks, sample_golden):
        """Gate returns GO when new model has higher recall."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=SlightlyBetterEmbedder(),
            golden=sample_golden,
            primary_metric="recall_at_k",
            top_k=3,
        )
        assert decision.recommendation == "GO"
        assert decision.new_metrics["recall_at_k"] >= decision.old_metrics["recall_at_k"]

    def test_no_go_when_new_model_regresses(self, sample_chunks, sample_golden):
        """Gate returns NO_GO when new model is worse."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=BadEmbedder(),
            golden=sample_golden,
            primary_metric="recall_at_k",
            top_k=3,
        )
        assert decision.recommendation == "NO_GO"
        assert "regresses" in decision.reason.lower() or "regress" in decision.reason.lower()

    def test_go_when_tie(self, sample_chunks, sample_golden):
        """Gate returns GO when models are equal (tie)."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=GoodEmbedder(),  # same model = same results
            golden=sample_golden,
            primary_metric="recall_at_k",
            top_k=3,
        )
        assert decision.recommendation == "GO"
        assert "tie" in decision.reason.lower() or "within margin" in decision.reason.lower()

    def test_margin_allows_slight_regression(self, sample_chunks, sample_golden):
        """With a margin, slight regression is OK → GO."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=SlightlyBetterEmbedder(),
            new_embedder=GoodEmbedder(),  # slightly worse
            golden=sample_golden,
            primary_metric="recall_at_k",
            threshold_margin=0.5,  # generous margin
            top_k=3,
        )
        assert decision.recommendation == "GO"
        assert "margin" in decision.reason.lower()

    def test_no_go_exceeds_margin(self, sample_chunks, sample_golden):
        """Regression beyond margin → NO_GO."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=BadEmbedder(),
            golden=sample_golden,
            primary_metric="recall_at_k",
            threshold_margin=0.01,  # tiny margin, bad embedder will exceed it
            top_k=3,
        )
        assert decision.recommendation == "NO_GO"

    def test_empty_golden_skips_gate(self, sample_chunks):
        """No golden dataset → gate skipped → GO (nothing to compare against)."""
        empty = GoldenDataset(items=[])
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=BadEmbedder(),
            golden=empty,
        )
        assert decision.recommendation == "GO"
        assert "skipped" in decision.reason.lower()

    def test_decision_has_metrics(self, sample_chunks, sample_golden):
        """Decision includes all gate metrics."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=SlightlyBetterEmbedder(),
            golden=sample_golden,
            top_k=3,
        )
        for metric in GATE_METRICS:
            assert metric in decision.old_metrics
            assert metric in decision.new_metrics
            assert metric in decision.deltas

    def test_decision_to_dict(self, sample_chunks, sample_golden):
        """GateDecision serializes to dict."""
        decision = run_decision_gate(
            chunks=sample_chunks,
            old_embedder=GoodEmbedder(),
            new_embedder=GoodEmbedder(),
            golden=sample_golden,
            top_k=3,
        )
        d = decision.to_dict()
        assert d["recommendation"] in ("GO", "NO_GO")
        assert "old_metrics" in d
        assert "primary_metric" in d


# ─── Hot-Set Tests ─────────────────────────────────────────────────────────────

class TestHotSet:
    """Hot-set identification logic."""

    def test_identifies_hot_chunks(self, sample_chunks, sample_golden):
        """Hot set = chunks referenced by golden queries."""
        hot, cold = identify_hot_set(sample_chunks, sample_golden)
        hot_ids = {c.id for c in hot}
        assert "chunk-refund-1" in hot_ids
        assert "chunk-refund-2" in hot_ids
        assert "chunk-shipping-1" in hot_ids
        assert "chunk-shipping-2" in hot_ids
        assert "chunk-other" not in hot_ids

        cold_ids = {c.id for c in cold}
        assert "chunk-other" in cold_ids

    def test_hot_set_count(self, sample_chunks, sample_golden):
        """4 chunks referenced by golden, 1 is cold."""
        hot, cold = identify_hot_set(sample_chunks, sample_golden)
        assert len(hot) == 4
        assert len(cold) == 1

    def test_empty_golden_returns_no_hot(self, sample_chunks):
        """Empty golden → no hot chunks identified."""
        empty = GoldenDataset(items=[])
        hot, cold = identify_hot_set(sample_chunks, empty)
        assert len(hot) == 0
        assert len(cold) == 5

    def test_missing_ids_ignored(self, sample_chunks):
        """Golden referencing nonexistent chunk IDs doesn't crash."""
        golden = GoldenDataset(items=[
            GoldenItem(question="test", relevant_chunk_ids=["nonexistent-id"]),
        ])
        hot, cold = identify_hot_set(sample_chunks, golden)
        assert len(hot) == 0
        assert len(cold) == 5


# ─── Smoke Test Tests ──────────────────────────────────────────────────────────

class TestSmokeTest:
    """Post-migration smoke test."""

    def test_smoke_passes_on_good_kb(self, sample_chunks, sample_golden, tmp_path):
        """Smoke test passes when KB is properly loaded and returns results."""
        from ragforge.pipeline.knowledge import KnowledgeBase
        from ragforge.pipeline.store import InMemoryStore
        from ragforge.pipeline.bm25 import BM25Index
        from unittest.mock import patch
        import json

        # Create a KB on disk
        kb_dir = tmp_path / "knowledge_bases" / "test-smoke"
        kb_dir.mkdir(parents=True)

        embedder = GoodEmbedder()
        store = InMemoryStore()
        vectors = embedder.encode([c.text for c in sample_chunks])
        store.add(sample_chunks, vectors)
        store.save(kb_dir / "vectors.json")

        meta = {"embedder_name": "good-mock", "embedder_dim": 4}
        (kb_dir / "meta.json").write_text(json.dumps(meta))

        # Build the KB object that load would return (with our mock embedder)
        kb = KnowledgeBase(name="test-smoke", embedder=embedder, store=store, bm25=BM25Index())

        # Patch KnowledgeBase.load to return our pre-built KB
        with patch.object(KnowledgeBase, 'load', return_value=kb):
            result = smoke_test("test-smoke", sample_golden, top_k=3)
            assert result.passed
            assert all(c["passed"] for c in result.checks)

    def test_smoke_fails_on_missing_kb(self, sample_golden):
        """Smoke test fails when KB doesn't exist."""
        result = smoke_test("nonexistent-kb-xyz", sample_golden, top_k=3)
        assert not result.passed
        assert any("load" in c["detail"].lower() or "not found" in c["detail"].lower()
                   for c in result.checks if not c["passed"])


# ─── CLI Tests ─────────────────────────────────────────────────────────────────

class TestMigrateCLI:
    """CLI argument parsing for migrate subcommands."""

    def test_gate_args(self):
        from ragforge.cli import build_parser
        p = build_parser()
        args = p.parse_args(["migrate", "gate", "my-kb", "golden.json",
                             "--old", "default", "--new", "openai", "-k", "3"])
        assert args.knowledge == "my-kb"
        assert args.golden == "golden.json"
        assert args.old == "default"
        assert args.new == "openai"
        assert args.k == 3
        assert args.metric == "recall_at_k"
        assert args.margin == 0.0

    def test_run_gated_args(self):
        from ragforge.cli import build_parser
        p = build_parser()
        args = p.parse_args(["migrate", "run", "my-kb", "--old", "x", "--new", "y",
                             "--gated", "--golden", "g.json", "--force"])
        assert args.gated is True
        assert args.force is True
        assert args.golden == "g.json"

    def test_smoke_test_args(self):
        from ragforge.cli import build_parser
        p = build_parser()
        args = p.parse_args(["migrate", "smoke-test", "my-kb", "golden.json", "-k", "10"])
        assert args.knowledge == "my-kb"
        assert args.golden == "golden.json"
        assert args.k == 10
