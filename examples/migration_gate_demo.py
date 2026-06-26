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

import os
import sys

# Allow running from repo root or from within examples/
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from ragforge.core.models import Chunk
from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.pipeline.embeddings import Embedder
from ragforge.migration.gate import run_decision_gate, identify_hot_set, GateDecision


# ─── Mock Embedders (no downloads, works offline) ──────────────────────────────

class CurrentEmbedder(Embedder):
    """Simulates the current (old) model. Decent but noisy — topics overlap."""

    @property
    def name(self) -> str:
        return "current-model"

    @property
    def dimension(self) -> int:
        return 8

    def embed(self, text: str) -> list[float]:
        t = text.lower()
        # Noisy embeddings — topics leak into each other
        if "refund" in t and "30 day" in t:
            return [0.8, 0.15, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0]
        elif "refund" in t:
            return [0.6, 0.2, 0.1, 0.05, 0.05, 0.0, 0.0, 0.0]
        elif "shipping" in t and "express" in t:
            return [0.1, 0.7, 0.1, 0.05, 0.05, 0.0, 0.0, 0.0]
        elif "shipping" in t:
            return [0.15, 0.6, 0.15, 0.05, 0.05, 0.0, 0.0, 0.0]
        elif "pricing" in t or "plan" in t or "$" in t:
            return [0.1, 0.1, 0.6, 0.1, 0.05, 0.05, 0.0, 0.0]
        elif "cost" in t or "how much" in t:
            # Query about cost maps poorly — confuses with shipping/other topics
            return [0.15, 0.25, 0.3, 0.15, 0.1, 0.05, 0.0, 0.0]
        elif "support" in t or "contact" in t:
            return [0.1, 0.1, 0.1, 0.5, 0.1, 0.1, 0.0, 0.0]
        elif "api" in t or "endpoint" in t:
            return [0.05, 0.05, 0.1, 0.1, 0.5, 0.1, 0.05, 0.05]
        return [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class BetterEmbedder(Embedder):
    """Simulates a better (new) model. Cleaner separation between topics."""

    @property
    def name(self) -> str:
        return "better-model"

    @property
    def dimension(self) -> int:
        return 8

    def embed(self, text: str) -> list[float]:
        t = text.lower()
        # Clean, well-separated embeddings — also understands cost/how-much as pricing
        if "refund" in t:
            return [0.95, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0]
        elif "shipping" in t:
            return [0.0, 0.95, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0]
        elif "pricing" in t or "plan" in t or "$" in t or "cost" in t or "how much" in t:
            return [0.0, 0.0, 0.95, 0.0, 0.0, 0.0, 0.05, 0.0]
        elif "support" in t or "contact" in t:
            return [0.0, 0.0, 0.0, 0.95, 0.0, 0.0, 0.0, 0.05]
        elif "api" in t or "endpoint" in t:
            return [0.0, 0.0, 0.0, 0.0, 0.95, 0.0, 0.05, 0.0]
        return [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.2]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class WorseEmbedder(Embedder):
    """Simulates a worse model. Everything maps to near-identical vectors."""

    @property
    def name(self) -> str:
        return "worse-model"

    @property
    def dimension(self) -> int:
        return 8

    def embed(self, text: str) -> list[float]:
        # Barely distinguishable — retrieval is nearly random
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest()[:4], 16) / 0xFFFF
        return [0.35 + h * 0.01, 0.35 - h * 0.01, 0.12, 0.12, 0.03, 0.02, 0.005, 0.005]

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
    # Distractors — make retrieval harder
    Chunk(text="Our API endpoint documentation is at /docs on the server.", doc_id="d5", index=0, id="distract-1"),
    Chunk(text="The API rate limit is 1000 requests per minute for enterprise accounts.", doc_id="d5", index=1, id="distract-2"),
    Chunk(text="We use AES-256 encryption for all data at rest.", doc_id="d6", index=0, id="distract-3"),
    Chunk(text="Multi-factor authentication is required for all administrator accounts.", doc_id="d6", index=1, id="distract-4"),
    Chunk(text="Our uptime SLA guarantees 99.9% availability.", doc_id="d7", index=0, id="distract-5"),
    Chunk(text="Data backups are taken every 6 hours and retained for 30 days.", doc_id="d7", index=1, id="distract-6"),
    Chunk(text="We support integration with Slack, Teams, and custom webhooks.", doc_id="d8", index=0, id="distract-7"),
    Chunk(text="The onboarding process takes about 15 minutes for most users.", doc_id="d8", index=1, id="distract-8"),
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
    print("  SCENARIO 1: Better model improves recall → GO (safe to migrate)")
    print("─" * 60)

    decision = run_decision_gate(
        chunks=CHUNKS,
        old_embedder=CurrentEmbedder(),
        new_embedder=BetterEmbedder(),
        golden=GOLDEN,
        primary_metric="recall_at_k",
        threshold_margin=0.0,
        top_k=3,
        hot_set_only=False,  # Use full corpus so distractors make it harder
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
        hot_set_only=False,
    )
    decision2.print_table()

    if decision2.recommendation == "NO_GO":
        print("  → Migration BLOCKED. No re-embedding happened.")
        print("  → Saved the cost of re-embedding the entire corpus.")
    print()

    # ─── Scenario 3: Margin allows regression ──────────────────────────────
    print("─" * 60)
    print("  SCENARIO 3: Regression within margin → GO (margin covers the drop)")
    print("─" * 60)

    decision3 = run_decision_gate(
        chunks=CHUNKS,
        old_embedder=BetterEmbedder(),
        new_embedder=CurrentEmbedder(),  # worse on cost queries
        golden=GOLDEN,
        primary_metric="recall_at_k",
        threshold_margin=0.4,  # allow up to 40% regression
        top_k=3,
        hot_set_only=False,
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
