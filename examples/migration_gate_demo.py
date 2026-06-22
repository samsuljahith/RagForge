#!/usr/bin/env python3
"""
Example: Migration Decision Gate

Demonstrates the full gated migration workflow:
  1. Build a small knowledge base with mock chunks
  2. Define a golden dataset (real queries + expected chunks)
  3. Run the decision gate comparing two embedders
  4. If GO → proceed with migration + run smoke test
  5. If NO_GO → abort and show why

Uses mock embedders (no API keys or model downloads needed).

Usage:
    python examples/migration_gate_demo.py

    # Or via CLI (if the KB were persisted):
    ragforge migrate gate my-kb golden.json --old default --new better -k 3
"""

from __future__ import annotations

import sys
sys.path.insert(0, ".")

from ragforge.core.models import Chunk
from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.pipeline.embeddings import Embedder
from ragforge.migration.gate import run_decision_gate, identify_hot_set, GateDecision


# ─── Mock Embedders (no downloads, works offline) ──────────────────────────────

class CurrentEmbedder(Embedder):
    """Simulates the current (old) embedding model. Decent but not great."""

    @property
    def name(self) -> str:
        return "current-model"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        t = text.lower()
        if "refund" in t:
            return [0.85, 0.1, 0.0, 0.05]
        elif "shipping" in t:
            return [0.1, 0.85, 0.0, 0.05]
        elif "pricing" in t or "cost" in t:
            return [0.1, 0.1, 0.8, 0.0]
        return [0.3, 0.3, 0.2, 0.2]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class BetterEmbedder(Embedder):
    """Simulates a better (new) model. Stronger separation between topics."""

    @property
    def name(self) -> str:
        return "better-model"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        t = text.lower()
        if "refund" in t:
            return [1.0, 0.0, 0.0, 0.0]
        elif "shipping" in t:
            return [0.0, 1.0, 0.0, 0.0]
        elif "pricing" in t or "cost" in t:
            return [0.0, 0.0, 1.0, 0.0]
        return [0.0, 0.0, 0.0, 1.0]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class WorseEmbedder(Embedder):
    """Simulates a worse model. Everything maps to similar vectors."""

    @property
    def name(self) -> str:
        return "worse-model"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, text: str) -> list[float]:
        return [0.5, 0.5, 0.5, 0.5]  # can't distinguish anything

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


# ─── Sample Data ──────────────────────────────────────────────────────────────

CHUNKS = [
    Chunk(text="Our refund policy allows returns within 30 days of purchase.", doc_id="d1", index=0, id="refund-1"),
    Chunk(text="Refund processing takes 3-5 business days after we receive the item.", doc_id="d1", index=1, id="refund-2"),
    Chunk(text="Standard shipping takes 5-7 business days.", doc_id="d2", index=0, id="ship-1"),
    Chunk(text="Express shipping ($15) delivers in 1-2 business days.", doc_id="d2", index=1, id="ship-2"),
    Chunk(text="Our pricing starts at $9/month for the starter plan.", doc_id="d3", index=0, id="price-1"),
    Chunk(text="Enterprise pricing is custom — contact sales for a quote.", doc_id="d3", index=1, id="price-2"),
    Chunk(text="Contact our support team at help@example.com for assistance.", doc_id="d4", index=0, id="other-1"),
]

GOLDEN = GoldenDataset(items=[
    GoldenItem(question="What is the refund window?", relevant_chunk_ids=["refund-1", "refund-2"]),
    GoldenItem(question="How long does shipping take?", relevant_chunk_ids=["ship-1", "ship-2"]),
    GoldenItem(question="How much does it cost?", relevant_chunk_ids=["price-1", "price-2"]),
])


# ─── Demo ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("  MIGRATION DECISION GATE DEMO")
    print("=" * 60)
    print()
    print(f"  Corpus: {len(CHUNKS)} chunks")
    print(f"  Golden: {len(GOLDEN)} queries with expected chunks")
    print()

    # Show hot-set identification
    hot, cold = identify_hot_set(CHUNKS, GOLDEN)
    print(f"  Hot set: {len(hot)} chunks (referenced by golden queries)")
    print(f"  Cold tail: {len(cold)} chunks (never queried)")
    print()

    # ─── Scenario 1: Better model → GO ─────────────────────────────────────
    print("─" * 60)
    print("  SCENARIO 1: Upgrade to a better model")
    print("─" * 60)

    decision = run_decision_gate(
        chunks=CHUNKS,
        old_embedder=CurrentEmbedder(),
        new_embedder=BetterEmbedder(),
        golden=GOLDEN,
        primary_metric="recall_at_k",
        threshold_margin=0.0,
        top_k=3,
    )
    decision.print_table()

    if decision.recommendation == "GO":
        print("  → Would proceed with migration (shadow index + cutover)")
        print("  → Then run smoke test to verify the swap worked")
    print()

    # ─── Scenario 2: Worse model → NO_GO ───────────────────────────────────
    print("─" * 60)
    print("  SCENARIO 2: Accidentally downgrade to a worse model")
    print("─" * 60)

    decision2 = run_decision_gate(
        chunks=CHUNKS,
        old_embedder=CurrentEmbedder(),
        new_embedder=WorseEmbedder(),
        golden=GOLDEN,
        primary_metric="recall_at_k",
        threshold_margin=0.0,
        top_k=3,
    )
    decision2.print_table()

    if decision2.recommendation == "NO_GO":
        print("  → Migration BLOCKED. No re-embedding happened.")
        print("  → Saved the cost of re-embedding the entire corpus.")
    print()

    # ─── Scenario 3: Margin allows slight regression ────────────────────────
    print("─" * 60)
    print("  SCENARIO 3: New model is slightly worse, but within allowed margin")
    print("─" * 60)

    decision3 = run_decision_gate(
        chunks=CHUNKS,
        old_embedder=BetterEmbedder(),
        new_embedder=CurrentEmbedder(),  # slightly worse
        golden=GOLDEN,
        primary_metric="recall_at_k",
        threshold_margin=0.3,  # allow up to 30% regression
        top_k=3,
    )
    decision3.print_table()

    # ─── Summary ────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("""
  The decision gate answers: "Will the new model actually
  retrieve better on MY queries?"

  • If yes → GO (proceed with shadow-index + cutover)
  • If no  → NO_GO (abort, nothing re-embedded, no cost)

  Key points:
  • Only embeds the HOT SET first (chunks real queries hit)
  • Uses recall@k / precision@k / MRR — real retrieval metrics
  • Threshold margin lets you accept slight regressions
  • Post-migration smoke test verifies the swap actually works

  CLI:
    ragforge migrate gate my-kb golden.json --old default --new openai
    ragforge migrate run my-kb --old default --new openai --gated --golden golden.json
    ragforge migrate smoke-test my-kb golden.json
""")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
