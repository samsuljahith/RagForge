#!/usr/bin/env python3
"""
RAGForge Evaluation Demo — prove your RAG is getting better, not worse.

Demonstrates:
  1. Build a small KB with known content
  2. Define a golden dataset (ground truth Q&A pairs)
  3. Run retrieval metrics (hit_rate, MRR, precision@k)
  4. A/B compare "fixed" vs "structure" chunking on the same golden set
  5. Show how to detect a regression

Runs with the light install — retrieval metrics need zero heavy deps.
LLM-judge metrics are shown as comments (need a configured LLM).

Run:
    python examples/eval_demo.py
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ragforge.pipeline import KnowledgeBase
from ragforge.evaluation import (
    GoldenDataset,
    Evaluator,
    RETRIEVAL_METRICS,
)


def main():
    print("=" * 60)
    print("RAGForge Evaluation Demo")
    print("Prove changes help. Catch regressions. Stop flying blind.")
    print("=" * 60)

    tmp_dir = Path(tempfile.mkdtemp(prefix="ragforge_eval_"))

    # ─── Step 1: Create sample documents ────────────────────────────────
    print("\n[1/5] Creating sample knowledge base...")

    docs_dir = tmp_dir / "docs"
    docs_dir.mkdir()

    (docs_dir / "refund_policy.md").write_text("""\
# Refund Policy

## Standard Refunds

All purchases are eligible for a full refund within 30 days.
Items must be in original condition.

## Electronics

Electronics have a 14-day return window.
A 15% restocking fee applies.

## Digital Products

Digital products are non-refundable once activated.
""")

    (docs_dir / "shipping.md").write_text("""\
# Shipping

## Domestic

Standard shipping: 5-7 business days, free.
Express: 2-3 days, $9.99.
Overnight: next business day, $24.99.

## International

Canada/Mexico: 5-10 business days.
Europe: 7-14 business days.
""")

    # ─── Step 2: Build two KBs with different strategies ────────────────
    print("[2/5] Building two KBs: 'fixed' chunking vs 'structure' chunking...")

    kb_fixed = KnowledgeBase.build(
        name="eval-demo-fixed",
        sources=[str(docs_dir)],
        chunk_strategy="fixed",
        chunk_options={"chunk_tokens": 64},
        persist=False,
    )

    kb_structure = KnowledgeBase.build(
        name="eval-demo-structure",
        sources=[str(docs_dir)],
        chunk_strategy="structure",
        persist=False,
    )

    print(f"   Fixed:     {kb_fixed.num_chunks} chunks")
    print(f"   Structure: {kb_structure.num_chunks} chunks")

    # ─── Step 3: Define a golden dataset ────────────────────────────────
    print("\n[3/5] Defining golden dataset (the ground truth)...")

    # In real usage, you'd load this from a file:
    #   golden = GoldenDataset.load("golden.json")
    # Here we define it inline for the demo.

    # Get actual chunk IDs so we can set up relevant_chunk_ids
    # (In practice you'd build the golden set from known-good results)
    structure_chunks = kb_structure.store.chunks

    # Find chunks that contain refund/shipping info
    refund_chunk_ids = [c.id for c in structure_chunks if "30 days" in c.text]
    shipping_chunk_ids = [c.id for c in structure_chunks if "5-7" in c.text or "Express" in c.text]

    golden = GoldenDataset.from_dicts([
        {
            "question": "What is the standard refund window?",
            "expected_answer": "30 days",
            "relevant_chunk_ids": refund_chunk_ids,
        },
        {
            "question": "How long does express shipping take?",
            "expected_answer": "2-3 business days",
            "relevant_chunk_ids": shipping_chunk_ids,
        },
        {
            "question": "Are digital products refundable?",
            "expected_answer": "non-refundable once activated",
            "relevant_chunk_ids": [c.id for c in structure_chunks if "non-refundable" in c.text],
        },
        {
            "question": "What is the electronics restocking fee?",
            "expected_answer": "15%",
            "relevant_chunk_ids": [c.id for c in structure_chunks if "15%" in c.text],
        },
    ])

    print(f"   {len(golden)} test questions defined")

    # Save it for CLI usage demo
    golden_path = tmp_dir / "golden.json"
    golden.save_json(golden_path)
    print(f"   Saved to {golden_path}")

    # ─── Step 4: Run evaluation on the structure KB ─────────────────────
    print("\n[4/5] Running evaluation (structure-aware chunking)...")

    evaluator = Evaluator(kb_structure)
    report = evaluator.run(
        golden,
        metrics=["hit_rate", "mrr", "precision_at_k", "recall_at_k"],
        top_k=3,
        mode="hybrid",
    )

    report.print_table()

    # ─── Step 5: A/B compare fixed vs structure ─────────────────────────
    print("\n[5/5] A/B comparison: fixed vs structure chunking...")
    print("   (Same golden set, same retrieval settings, different chunking)")

    # For the compare to work fairly we use expected_answer (a substring
    # that should appear in the top retrieved chunk) rather than chunk IDs,
    # since chunk IDs differ between the two KBs.
    # Note: on this 2-doc toy corpus both strategies tend to tie — each
    # document fits inside a single fixed chunk, so both retrieve the same
    # content. On real corpora with longer sections, fixed chunking splits
    # across headings while structure-aware keeps them intact, producing a
    # visible precision difference (typically 10-30% on support/docs KBs).
    compare_golden = GoldenDataset.from_dicts([
        {"question": "What is the standard refund window?",   "expected_answer": "30 days"},
        {"question": "How long does express shipping take?",   "expected_answer": "2-3"},
        {"question": "Are digital products refundable?",       "expected_answer": "non-refundable"},
        {"question": "What is the electronics restocking fee?", "expected_answer": "15%"},
    ])

    comparison = Evaluator.compare(
        kb_fixed,
        kb_structure,
        compare_golden,
        metrics=["hit_rate", "mrr"],
        top_k=3,
        mode="hybrid",
        label_a="fixed (64 tok)",
        label_b="structure-aware",
    )

    Evaluator.print_comparison(comparison)

    # ─── Summary ────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("What this shows:")
    print("  • Retrieval metrics give you concrete numbers (not vibes)")
    print("  • A/B compare proves which config is better on YOUR data")
    print("  • Run this after every change to catch regressions early")
    print("─" * 60)
    print("\nCLI equivalent:")
    print("  ragforge eval run my-kb golden.json --mode hybrid -k 3")
    print("  ragforge eval compare kb-fixed kb-structure golden.json")
    print("  # (replace golden.json with the path you saved your golden dataset to)")
    print("\nAPI equivalent:")
    print("  POST /evaluate {knowledge: 'my-kb', golden_dataset: [...], metrics: [...]}")

    # Cleanup
    shutil.rmtree(tmp_dir)
    print("\n✓ Demo complete. Temp files cleaned up.")


if __name__ == "__main__":
    main()
