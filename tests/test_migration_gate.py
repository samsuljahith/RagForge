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

import json
import shutil
from pathlib import Path

import pytest

from ragforge.core.models import Chunk
from ragforge.core.registry import available, register
from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.pipeline.embeddings import Embedder
from ragforge.pipeline.store import InMemoryStore
from ragforge.migration.gate import (
    run_decision_gate,
    GateDecision,
    identify_hot_set,
    smoke_test,
    SmokeTestResult,
    GATE_METRICS,
)
from ragforge.migration.migrator import migrate_with_gate, _KB_DIR


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


class CountingEmbedder(Embedder):
    """
    Same retrieval quality as SlightlyBetterEmbedder, but counts how many
    times each text gets encoded. The count is a CLASS attribute (not
    instance) because `_get_embedder()` constructs a fresh instance on
    every lookup by name - an instance counter would miss calls made
    through a different instance of the same registered model.
    """

    calls: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "counting-mock"

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
        for t in texts:
            type(self).calls[t] = type(self).calls.get(t, 0) + 1
        return [self.embed(t) for t in texts]


class BadCountingEmbedder(Embedder):
    """Same poor retrieval quality as BadEmbedder, but counts encode() calls
    per text - same class-attribute rationale as CountingEmbedder."""

    calls: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "bad-counting-mock"

    @property
    def dimension(self) -> int:
        return 4

    def encode(self, texts: list[str]) -> list[list[float]]:
        for t in texts:
            type(self).calls[t] = type(self).calls.get(t, 0) + 1
        return [[0.5, 0.5, 0.5, 0.5] for _ in texts]


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


# ─── No-Double-Embed Tests ──────────────────────────────────────────────────────

class TestNoDoubleEmbed:
    """
    Prove migrate_with_gate() embeds each chunk with the new model AT MOST
    ONCE across the whole gate-then-migrate flow: once for the hot set
    (during the gate check), reused (not recomputed) during the actual
    migration, and once for the cold tail (only during the migration,
    since the gate never touches it).
    """

    @pytest.fixture(autouse=True)
    def _register_embedders(self):
        for embedder_name, cls in [
            ("old-mock", GoodEmbedder),
            ("counting-mock", CountingEmbedder),
            ("bad-counting-mock", BadCountingEmbedder),
        ]:
            if embedder_name not in available("embedder"):
                register("embedder", embedder_name)(cls)
        CountingEmbedder.calls.clear()
        BadCountingEmbedder.calls.clear()
        yield
        CountingEmbedder.calls.clear()
        BadCountingEmbedder.calls.clear()

    def _build_kb(self, name: str, chunks: list[Chunk]) -> None:
        kb_dir = _KB_DIR / name
        kb_dir.mkdir(parents=True, exist_ok=True)

        store = InMemoryStore()
        vectors = GoodEmbedder().encode([c.text for c in chunks])
        store.add(chunks, vectors)
        store.save(kb_dir / "vectors.json")
        (kb_dir / "meta.json").write_text(json.dumps({"embedder_name": "old-mock", "embedder_dim": 4}))

    def _cleanup(self, name: str) -> None:
        kb_dir = _KB_DIR / name
        if kb_dir.exists():
            shutil.rmtree(kb_dir)

    def test_each_chunk_embedded_at_most_once(self, sample_chunks, sample_golden, tmp_path):
        name = "migration-gate-no-double-embed"
        try:
            self._build_kb(name, sample_chunks)

            golden_path = tmp_path / "golden.json"
            sample_golden.save_json(golden_path)

            result = migrate_with_gate(
                knowledge=name,
                from_model="old-mock",
                to_model="counting-mock",
                golden_path=str(golden_path),
                top_k=3,
            )

            assert result["status"] == "migrated"
            assert result["gate_decision"]["recommendation"] == "GO"

            # Hot set (referenced by sample_golden): embedded once, during the
            # gate. Cold tail ("chunk-other"): embedded once, during the
            # migration. Nothing embedded twice, nothing skipped.
            hot_texts = [c.text for c in sample_chunks if c.id != "chunk-other"]
            cold_text = next(c.text for c in sample_chunks if c.id == "chunk-other")

            for text in hot_texts:
                assert CountingEmbedder.calls.get(text) == 1, f"hot chunk embedded {CountingEmbedder.calls.get(text)} times: {text!r}"
            assert CountingEmbedder.calls.get(cold_text) == 1

            # Sanity: every chunk text appears in the call log exactly once.
            # (The golden questions are also encoded, for retrieval during
            # the gate - that's expected and unrelated to chunk re-embedding.)
            chunk_call_counts = [CountingEmbedder.calls.get(c.text) for c in sample_chunks]
            assert chunk_call_counts == [1] * len(sample_chunks)
        finally:
            self._cleanup(name)

    def test_no_go_embeds_only_the_hot_set_once(self, sample_chunks, sample_golden, tmp_path):
        """NO_GO still embeds the hot set exactly once (for the gate check)
        and nothing else - migration never proceeds."""
        name = "migration-gate-no-go-embed-count"
        try:
            self._build_kb(name, sample_chunks)

            golden_path = tmp_path / "golden.json"
            sample_golden.save_json(golden_path)

            result = migrate_with_gate(
                knowledge=name,
                from_model="old-mock",
                to_model="bad-counting-mock",
                golden_path=str(golden_path),
                top_k=3,
            )

            assert result["status"] == "rejected_by_gate"
            assert result["gate_decision"]["recommendation"] == "NO_GO"
            assert result["num_chunks_migrated"] == 0

            # Only the 4 hot-set chunks were ever embedded (once each), for
            # the gate check. The cold chunk ("chunk-other") was never
            # touched since migration never proceeds.
            hot_texts = [c.text for c in sample_chunks if c.id != "chunk-other"]
            cold_text = next(c.text for c in sample_chunks if c.id == "chunk-other")

            for text in hot_texts:
                assert BadCountingEmbedder.calls.get(text) == 1
            assert cold_text not in BadCountingEmbedder.calls
            hot_call_counts = [BadCountingEmbedder.calls.get(t) for t in hot_texts]
            assert hot_call_counts == [1] * len(hot_texts)
        finally:
            self._cleanup(name)
