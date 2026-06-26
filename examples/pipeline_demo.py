#!/usr/bin/env python3
"""
RAGForge Pipeline End-to-End Demo

This script demonstrates the full pipeline using ONLY the default (light) install
path — no sentence-transformers, no OpenAI key, no external vector DB required.

What it does:
    1. Creates sample documents (a mini knowledge base about a fictional company)
    2. Parses them with the parsing module
    3. Chunks them with structure-aware chunking
    4. Builds a KnowledgeBase (embeds + stores + BM25 indexes)
    5. Runs queries in all three retrieval modes (dense, bm25, hybrid)
    6. Shows how hybrid search catches things that pure dense or bm25 alone might miss

Run it:
    python examples/pipeline_demo.py

Requirements:
    pip install -e .   (just the core — zero heavy deps)
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

# RAGForge imports
from ragforge.pipeline import KnowledgeBase


def main():
    print("=" * 70)
    print("RAGForge Pipeline Demo — end-to-end RAG with zero heavy dependencies")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Step 1: Create sample documents
    # -------------------------------------------------------------------------
    print("\n[1/5] Creating sample documents...")

    tmp_dir = Path(tempfile.mkdtemp(prefix="ragforge_demo_"))
    docs_dir = tmp_dir / "docs"
    docs_dir.mkdir()

    (docs_dir / "refund_policy.md").write_text("""\
# Refund Policy

## Standard Refunds

All purchases are eligible for a full refund within 30 days of the original
purchase date. Items must be returned in their original condition with all
packaging intact.

## Electronics

Electronics have a shorter return window of 14 days due to rapid depreciation.
A 15% restocking fee applies to opened electronics.

## Digital Products

Digital products (software licenses, e-books, online courses) are non-refundable
once the download or access link has been activated. Contact support within 24
hours of purchase if you experience technical issues.

## How to Request a Refund

1. Log into your account at portal.example.com
2. Navigate to Order History
3. Click "Request Refund" on the relevant order
4. Our team reviews requests within 2 business days

Refund reference codes follow the format REF-XXXXX (e.g., REF-48291).
""")

    (docs_dir / "shipping.md").write_text("""\
# Shipping Information

## Domestic Shipping

| Method       | Speed         | Cost    |
|-------------|---------------|---------|
| Standard    | 5-7 days      | Free    |
| Express     | 2-3 days      | $9.99   |
| Overnight   | Next business | $24.99  |

All orders ship from our warehouse in Austin, TX (warehouse code: WH-ATX-01).

## International Shipping

International orders ship via DHL or FedEx. Delivery times vary by destination:
- Canada/Mexico: 5-10 business days
- Europe: 7-14 business days  
- Asia-Pacific: 10-21 business days

Customs duties and import taxes are the responsibility of the recipient.

## Tracking

All shipments include tracking. Track your order at track.example.com
using your order number (format: ORD-XXXXXXX).
""")

    (docs_dir / "product_catalog.md").write_text("""\
# Product Catalog

## Flagship Products

### RAGForge Pro

SKU: SKU-RF-PRO-2024
Enterprise-grade RAG platform with priority support.
- Price: $299/month
- Includes: unlimited knowledge bases, custom embeddings, SLA

### RAGForge Starter

SKU: SKU-RF-START-2024
For individual developers and small teams.
- Price: $49/month
- Includes: 5 knowledge bases, community support

### RAGForge Open Source

Free and open source. Self-hosted, community-driven.
- Price: Free
- Includes: all core features, community support

## Add-ons

- **GPU Acceleration Pack**: $99/month
- **Custom Model Training**: Starting at $500
- **Dedicated Support**: $199/month
""")

    print(f"   Created 3 documents in {docs_dir}")

    # -------------------------------------------------------------------------
    # Step 2: Build a KnowledgeBase
    # -------------------------------------------------------------------------
    print("\n[2/5] Building knowledge base (parse → chunk → embed → store)...")

    kb = KnowledgeBase.build(
        name="demo-kb",
        sources=[str(docs_dir)],
        embedder="default",  # Hash-based embedder, zero deps
        chunk_strategy="structure",  # Structure-aware: keeps tables/code intact
        persist=False,  # Don't write to ~/.ragforge for this demo
    )

    print(f"   Built: {kb}")
    print(f"   Documents: {kb.num_documents}")
    print(f"   Chunks:    {kb.num_chunks}")

    # -------------------------------------------------------------------------
    # Step 3: Query with DENSE mode (vector similarity)
    # -------------------------------------------------------------------------
    print("\n[3/5] Query: 'refund policy for electronics' (dense mode)...")
    print("   Dense search uses semantic similarity — good for natural language questions.")

    results = kb.query("refund policy for electronics", top_k=3, mode="dense")
    _print_results(results)

    # -------------------------------------------------------------------------
    # Step 4: Query with BM25 mode (keyword matching)
    # -------------------------------------------------------------------------
    print("\n[4/5] Query: 'SKU-RF-PRO-2024' (bm25 mode)...")
    print("   BM25 catches exact keyword matches that dense embeddings often miss.")

    results = kb.query("SKU-RF-PRO-2024", top_k=3, mode="bm25")
    _print_results(results)

    # -------------------------------------------------------------------------
    # Step 5: Query with HYBRID mode (dense + BM25 fused via RRF)
    # -------------------------------------------------------------------------
    print("\n[5/5] Query: 'how much does overnight shipping cost' (hybrid mode)...")
    print("   Hybrid fuses both via Reciprocal Rank Fusion — best overall quality.")

    results = kb.query("how much does overnight shipping cost", top_k=3, mode="hybrid")
    _print_results(results)

    # -------------------------------------------------------------------------
    # Bonus: Show how hybrid catches what single modes miss
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("BONUS: 'REF-48291 refund status' — hybrid vs single modes")
    print("=" * 70)

    print("\n  Dense only:")
    results_dense = kb.query("REF-48291 refund status", top_k=2, mode="dense")
    _print_results(results_dense, indent=4)

    print("\n  BM25 only:")
    results_bm25 = kb.query("REF-48291 refund status", top_k=2, mode="bm25")
    _print_results(results_bm25, indent=4)

    print("\n  Hybrid (dense + BM25 via RRF):")
    results_hybrid = kb.query("REF-48291 refund status", top_k=2, mode="hybrid")
    _print_results(results_hybrid, indent=4)

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    shutil.rmtree(tmp_dir)
    print("\n✓ Demo complete. Temp files cleaned up.")
    print("\nNext steps:")
    print("  - Try with real docs:  ragforge knowledge build my-kb ./your-docs/")
    print("  - Query from CLI:      ragforge query my-kb 'your question' --mode hybrid")
    print("  - Start the API:       ragforge serve")
    print("  - Query from curl:     curl -X POST localhost:8000/query -H 'Content-Type: application/json' \\")
    print("                              -d '{\"knowledge\": \"my-kb\", \"question\": \"...\", \"mode\": \"hybrid\"}'")


def _print_results(results: list, indent: int = 2):
    """Pretty-print retrieval results."""
    prefix = " " * indent
    if not results:
        print(f"{prefix}(no results)")
        return
    for i, (chunk, score) in enumerate(results, 1):
        section = chunk.metadata.get("section", "")
        section_tag = f" [{section}]" if section else ""
        text_preview = chunk.text[:100].replace("\n", " ").strip()
        print(f"{prefix}{i}. score={score:.4f}{section_tag}")
        print(f"{prefix}   {text_preview}...")


if __name__ == "__main__":
    main()
