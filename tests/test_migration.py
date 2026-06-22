"""
Tests for the migration module.

Covers the actual promise on the website's "Don't migrate blind" section:
  - The cutover is gated on real recall@k/MRR/hit_rate (old model vs new),
    not a no-op check that always swaps.
  - The hot set (chunks the golden questions reference) is re-embedded and
    gated first; a rejected migration never re-embeds the cold chunks.
  - `force=True` overrides a failed gate.
  - Without a golden set, migration still works (unguarded), unchanged.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from ragforge.core.registry import available, register
from ragforge.evaluation.golden import GoldenDataset
from ragforge.migration.migrator import migrate_knowledge_base
from ragforge.pipeline.embeddings import Embedder

_KB_DIR = Path.home() / ".ragforge" / "knowledge_bases"


class _BrokenEmbedder(Embedder):
    """
    Deterministic but content-blind: hashes the *reversed* text into a
    one-hot bucket, so it can't pick up on the words a real query shares
    with its relevant chunk. Used to simulate a model that's genuinely
    worse on retrieval, so the gate has something real to reject.
    """

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return "broken-test-embedder"

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        h = int(hashlib.md5(text[::-1].encode()).hexdigest(), 16)
        vec = [0.0] * self._dim
        vec[h % self._dim] = 1.0
        return vec


_GOOD_KEYWORDS = ["refund", "shipping", "return"]


class _GoodEmbedder(Embedder):
    """
    Deterministic keyword-matching embedder: one dimension per topic
    keyword. Guaranteed to discriminate cleanly between the 3 topics used
    in these tests, so it's a reliable "good" baseline for gate tests -
    unlike DefaultEmbedder's hashing, whose real-world discrimination on
    a tiny corpus isn't something these tests should depend on.
    """

    @property
    def dimension(self) -> int:
        return len(_GOOD_KEYWORDS)

    @property
    def name(self) -> str:
        return "good-test-embedder"

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        lower = text.lower()
        return [1.0 if kw in lower else 0.0 for kw in _GOOD_KEYWORDS]


for _name, _cls in [
    ("broken-test-embedder", _BrokenEmbedder),
    ("good-test-embedder", _GoodEmbedder),
]:
    if _name not in available("embedder"):
        register("embedder", _name)(_cls)


def _build_kb(name: str, tmp_path: Path, embedder: str = "good-test-embedder"):
    from ragforge.pipeline import KnowledgeBase

    docs = tmp_path / f"{name}-docs"
    docs.mkdir()
    (docs / "refunds.md").write_text("# Refunds\n\nRefunds are processed within 30 days of purchase.")
    (docs / "shipping.md").write_text("# Shipping\n\nShipping takes 5 to 7 business days for delivery.")
    (docs / "returns.md").write_text("# Returns\n\nReturns are accepted within 14 days of delivery.")
    (docs / "privacy.md").write_text("# Privacy\n\nWe never sell your personal data to third parties.")

    # Built with the same embedder passed as `from_model` in the tests below,
    # so the on-disk vectors actually live in that embedder's vector space.
    return KnowledgeBase.build(name=name, sources=[str(docs)], embedder=embedder, persist=True)


def _golden_for(kb, tmp_path: Path) -> Path:
    """3 questions, each pointing at a different chunk -> the hot set has
    real distractors, so the gate can actually distinguish model quality.
    The privacy chunk is never referenced, so it stays in the cold set."""
    chunks = kb.store.chunks
    refund = next(c for c in chunks if "Refunds are processed" in c.text)
    shipping = next(c for c in chunks if "Shipping takes" in c.text)
    returns = next(c for c in chunks if "Returns are accepted" in c.text)

    golden = GoldenDataset.from_dicts([
        {"question": "How long do refunds take?", "relevant_chunk_ids": [refund.id]},
        {"question": "How long does shipping take?", "relevant_chunk_ids": [shipping.id]},
        {"question": "How long can I return an item?", "relevant_chunk_ids": [returns.id]},
    ])
    golden_path = tmp_path / "golden.json"
    golden.save_json(golden_path)
    return golden_path


def _cleanup(name: str) -> None:
    kb_path = _KB_DIR / name
    if kb_path.exists():
        shutil.rmtree(kb_path)


class TestMigrationGate:
    def test_same_model_passes_gate_and_migrates(self, tmp_path):
        name = "migration-test-same-model"
        try:
            kb = _build_kb(name, tmp_path)
            golden_path = _golden_for(kb, tmp_path)

            result = migrate_knowledge_base(
                knowledge=name, from_model="good-test-embedder", to_model="good-test-embedder",
                validate=True, golden_path=str(golden_path), top_k=1,
            )

            assert result["status"] == "migrated"
            assert result["gate"]["passed"] is True
            assert result["gate"]["hot_set_size"] == 3
            assert result["gate"]["total_chunks"] == 4
            assert result["num_chunks_migrated"] == 4
        finally:
            _cleanup(name)

    def test_worse_model_rejected_by_gate(self, tmp_path):
        name = "migration-test-worse-model"
        try:
            kb = _build_kb(name, tmp_path)
            golden_path = _golden_for(kb, tmp_path)

            result = migrate_knowledge_base(
                knowledge=name, from_model="good-test-embedder", to_model="broken-test-embedder",
                validate=True, golden_path=str(golden_path), top_k=1,
            )

            assert result["status"] == "rejected_quality_gate"
            assert result["gate"]["passed"] is False
            assert result["gate"]["winner"] == "old_model"
            assert result["num_chunks_migrated"] == 0

            # Nothing was actually swapped.
            kb_path = _KB_DIR / name
            assert not (kb_path / "vectors_backup.json").exists()
            meta = json.loads((kb_path / "meta.json").read_text())
            assert meta["embedder_name"] == "good-test-embedder"
        finally:
            _cleanup(name)

    def test_hot_set_first_skips_cold_chunks_on_rejection(self, tmp_path):
        """The 4th (privacy) chunk is never referenced by the golden set.
        If the gate rejects the swap, it should never get re-embedded -
        only the hot chunks (and the golden questions themselves, for
        retrieval during the gate) ever reach the new embedder."""
        name = "migration-test-hot-set-first"
        try:
            kb = _build_kb(name, tmp_path)
            privacy_chunk = next(c for c in kb.store.chunks if "personal data" in c.text)
            golden_path = _golden_for(kb, tmp_path)

            encoded_texts: list[str] = []
            original_encode = _BrokenEmbedder.encode

            def _tracking_encode(self, texts):
                encoded_texts.extend(texts)
                return original_encode(self, texts)

            with patch.object(_BrokenEmbedder, "encode", _tracking_encode):
                result = migrate_knowledge_base(
                    knowledge=name, from_model="good-test-embedder", to_model="broken-test-embedder",
                    validate=True, golden_path=str(golden_path), top_k=1,
                )

            assert result["status"] == "rejected_quality_gate"
            # The cold (privacy) chunk's text never reached the new embedder.
            assert privacy_chunk.text not in encoded_texts
        finally:
            _cleanup(name)

    def test_force_overrides_rejected_gate(self, tmp_path):
        name = "migration-test-force"
        try:
            kb = _build_kb(name, tmp_path)
            golden_path = _golden_for(kb, tmp_path)

            result = migrate_knowledge_base(
                knowledge=name, from_model="good-test-embedder", to_model="broken-test-embedder",
                validate=True, golden_path=str(golden_path), top_k=1, force=True,
            )

            assert result["status"] == "migrated"
            assert result["gate"]["passed"] is False
            assert result["num_chunks_migrated"] == 4

            kb_path = _KB_DIR / name
            meta = json.loads((kb_path / "meta.json").read_text())
            assert meta["embedder_name"] == "broken-test-embedder"
        finally:
            _cleanup(name)

    def test_without_golden_set_migrates_unguarded(self, tmp_path):
        name = "migration-test-unguarded"
        try:
            kb = _build_kb(name, tmp_path)

            result = migrate_knowledge_base(
                knowledge=name, from_model="default", to_model="broken-test-embedder",
                validate=True,
            )

            assert result["status"] == "migrated"
            assert result["gate"] is None
            assert result["num_chunks_migrated"] == 4
        finally:
            _cleanup(name)

    def test_empty_knowledge_base(self, tmp_path):
        from ragforge.pipeline import KnowledgeBase

        name = "migration-test-empty"
        try:
            KnowledgeBase.build(name=name, sources=[], persist=True)
            result = migrate_knowledge_base(
                knowledge=name, from_model="default", to_model="broken-test-embedder",
            )
            assert result["status"] == "nothing_to_migrate"
            assert result["num_chunks_migrated"] == 0
        finally:
            _cleanup(name)

    def test_missing_knowledge_base_raises(self):
        with pytest.raises(FileNotFoundError):
            migrate_knowledge_base(
                knowledge="does-not-exist-migration-kb",
                from_model="default", to_model="default",
            )
