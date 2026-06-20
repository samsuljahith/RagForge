#!/usr/bin/env python3
"""
RAGForge Answer Generation Demo — full RAG loop with sources.

Demonstrates: question → retrieve → generate grounded answer → cite sources.

This script uses a MOCK LLM provider so it runs without API keys or Ollama.
To use a real LLM, replace MockLLM with:
  - llm="ollama"    (needs Ollama running locally — no API key)
  - llm="openai"    (needs OPENAI_API_KEY env var)
  - llm="anthropic" (needs ANTHROPIC_API_KEY env var)

Run:
    python examples/answer_demo.py

Requirements:
    pip install -e .   (just the core — zero heavy deps for this demo)
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ragforge.pipeline import KnowledgeBase
from ragforge.pipeline.generation import LLMProvider, build_grounded_prompt


# ---------------------------------------------------------------------------
# A mock LLM that demonstrates the answer format without needing real APIs.
# Replace this with llm="ollama" (or "openai"/"anthropic") for real usage.
# ---------------------------------------------------------------------------

class MockLLM(LLMProvider):
    """
    A mock LLM that parses the prompt and returns a reasonable-looking answer.
    Used so this demo runs without any API keys or external services.
    """

    @property
    def name(self) -> str:
        return "mock-demo-llm"

    def generate(self, prompt: str, **opts) -> str:
        # Look for key phrases in the context to craft a realistic mock answer
        if "30 days" in prompt and "refund" in prompt.lower():
            return (
                "Based on the provided context, the refund window is 30 days from "
                "the original purchase date. Items must be returned in their original "
                "condition with all packaging intact [Source 1]. Electronics have a "
                "shorter 14-day window with a 15% restocking fee [Source 2]."
            )
        elif "shipping" in prompt.lower():
            return (
                "Standard shipping takes 5-7 business days and is free. Express "
                "shipping (2-3 days) costs $9.99, and overnight is $24.99 [Source 1]."
            )
        elif "SKU" in prompt or "product" in prompt.lower():
            return (
                "RAGForge Pro (SKU-RF-PRO-2024) is the enterprise-grade plan at "
                "$299/month, including unlimited knowledge bases and custom "
                "embeddings [Source 1]."
            )
        else:
            return "I don't have enough information to answer that."


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("RAGForge Answer Generation Demo")
    print("Full loop: question → retrieve → generate answer → cite sources")
    print("=" * 70)

    # ── Step 1: Create sample docs ──────────────────────────────────────────
    print("\n[1/4] Creating sample knowledge base...")

    tmp_dir = Path(tempfile.mkdtemp(prefix="ragforge_answer_"))
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

Digital products (software licenses, e-books) are non-refundable once activated.
""")

    (docs_dir / "shipping.md").write_text("""\
# Shipping

## Domestic

| Method    | Speed       | Cost   |
|-----------|-------------|--------|
| Standard  | 5-7 days    | Free   |
| Express   | 2-3 days    | $9.99  |
| Overnight | Next day    | $24.99 |

All orders ship from Austin, TX (warehouse WH-ATX-01).
""")

    (docs_dir / "products.md").write_text("""\
# Products

## RAGForge Pro (SKU-RF-PRO-2024)

Enterprise-grade RAG platform.
- Price: $299/month
- Unlimited knowledge bases
- Custom embeddings
- Priority SLA

## RAGForge Starter (SKU-RF-START-2024)

For individual developers.
- Price: $49/month
- 5 knowledge bases
- Community support
""")

    # ── Step 2: Build knowledge base ────────────────────────────────────────
    kb = KnowledgeBase.build(
        name="answer-demo-kb",
        sources=[str(docs_dir)],
        chunk_strategy="structure",
        persist=False,
    )
    print(f"   Built: {kb.num_documents} docs, {kb.num_chunks} chunks")

    # ── Step 3: Ask questions with grounded answers ─────────────────────────
    mock = MockLLM()
    questions = [
        "What is the refund window for purchases?",
        "How much does express shipping cost?",
        "Tell me about the Pro plan and its SKU",
        "What is the meaning of life?",  # not in context → should refuse
    ]

    print("\n[2/4] Asking questions with answer generation...\n")

    for i, question in enumerate(questions, 1):
        print(f"{'─' * 70}")
        print(f"  Q{i}: {question}")
        print(f"{'─' * 70}")

        # Use the .answer() method directly with our mock LLM
        # In real usage: kb.answer(question, llm="ollama") or llm="openai"
        from ragforge.pipeline.generation import get_llm, build_grounded_prompt

        # Retrieve
        results = kb.query(question, top_k=3, mode="hybrid")

        # Build sources
        sources = [
            {
                "id": chunk.id,
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "index": chunk.index,
                "metadata": chunk.metadata,
                "score": round(score, 4),
            }
            for chunk, score in results
        ]

        # Build prompt and generate
        prompt = build_grounded_prompt(question, sources)
        answer = mock.generate(prompt)

        # Print answer
        print(f"\n  Answer ({mock.name}):")
        print(f"  {answer}\n")

        # Print sources
        print(f"  Sources:")
        for j, src in enumerate(sources, 1):
            section = src["metadata"].get("section", "")
            tag = f" [{section}]" if section else ""
            print(f"    [{j}] score={src['score']:.4f}{tag}")
            print(f"        {src['text'][:80]}...")
        print()

    # ── Step 4: Show how to do it with the functional API ───────────────────
    print(f"{'─' * 70}")
    print("[3/4] Same thing via the functional API (what the HTTP endpoint uses):")
    print(f"{'─' * 70}\n")

    print("  # With a real LLM (e.g. Ollama running locally):")
    print("  from ragforge.pipeline import query_knowledge_base")
    print()
    print('  result = query_knowledge_base(')
    print('      knowledge="my-kb",')
    print('      question="What is the refund policy?",')
    print('      generate=True,')
    print('      llm="ollama",  # or "openai", "anthropic"')
    print("  )")
    print('  print(result["answer"])')
    print('  for src in result["chunks"]:')
    print('      print(f"  [{src[\'score\']:.3f}] {src[\'text\'][:60]}")')

    # ── Step 5: Show CLI usage ──────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[4/4] CLI usage:")
    print(f"{'─' * 70}\n")
    print("  # Retrieval only (existing behavior, no LLM needed):")
    print('  ragforge query my-kb "What is the refund policy?"')
    print()
    print("  # With answer generation:")
    print('  ragforge query my-kb "What is the refund policy?" --generate --llm ollama')
    print()
    print("  # With a specific model:")
    print('  ragforge query my-kb "question" --generate --llm openai --model gpt-4o')
    print()
    print("  # Via the HTTP API:")
    print("  curl -X POST http://localhost:8000/query \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{")
    print('      "knowledge": "my-kb",')
    print('      "question": "What is the refund policy?",')
    print('      "generate": true,')
    print('      "llm": "ollama"')
    print("    }'")

    # Cleanup
    shutil.rmtree(tmp_dir)
    print(f"\n{'─' * 70}")
    print("✓ Demo complete.")


if __name__ == "__main__":
    main()
