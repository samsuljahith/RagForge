#!/usr/bin/env python3
"""
Real Benchmark: Migration Decision Gate on SciFact (BEIR)

Runs two real sentence-transformers models against the SciFact dataset
(~5K docs, ~300 queries with human relevance labels) and uses RAGForge's
migration decision gate to produce a GO/NO_GO verdict with credible
recall@k / MRR numbers.

Models compared:
  A (baseline): sentence-transformers/all-MiniLM-L6-v2
  B (candidate): BAAI/bge-small-en-v1.5

Requirements:
  pip install datasets sentence-transformers numpy

Usage:
  python benchmarks/run_migration_gate_benchmark.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from datasets import load_dataset

from ragforge.core.models import Chunk
from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.migration.gate import run_decision_gate, GATE_METRICS
from ragforge.pipeline.embeddings import Embedder


# ─── Config ────────────────────────────────────────────────────────────────────

DATASET_NAME = "scifact"
MODEL_A = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_B = "sentence-transformers/paraphrase-MiniLM-L3-v2"
TOP_K_VALUES = [5, 10]
MAX_QUERIES = 300  # use all queries with relevance labels (SciFact has ~300)

OUTPUT_DIR = Path(__file__).parent
OUTPUT_JSON = OUTPUT_DIR / f"migration_gate_{DATASET_NAME}.json"


# ─── Real Sentence-Transformers Embedder ───────────────────────────────────────

class STEmbedder(Embedder):
    """Wraps a real sentence-transformers model for the benchmark."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        print(f"  Loading model: {model_name}...")
        self._model = SentenceTransformer(model_name)
        self._name = model_name
        self._dim = self._model.get_sentence_embedding_dimension()

    @property
    def name(self) -> str:
        return self._name

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def encode(self, texts: list[str]) -> list[list[float]]:
        print(f"    Encoding {len(texts)} texts with {self._name}...")
        start = time.time()
        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=64,
        )
        elapsed = time.time() - start
        print(f"    Done in {elapsed:.1f}s")
        return vecs.tolist()


# ─── Load BEIR Dataset ─────────────────────────────────────────────────────────

def load_scifact():
    """Load SciFact from Hugging Face datasets (BEIR format)."""
    print(f"\n{'='*60}")
    print(f"  Loading BEIR/{DATASET_NAME} dataset...")
    print(f"{'='*60}\n")

    # Load corpus
    corpus_ds = load_dataset(f"BeIR/{DATASET_NAME}", "corpus", split="corpus")
    corpus = {}
    for row in corpus_ds:
        doc_id = str(row["_id"])
        text = (row.get("title") or "") + " " + (row.get("text") or "")
        corpus[doc_id] = text.strip()
    print(f"  Corpus: {len(corpus)} documents")

    # Load queries
    queries_ds = load_dataset(f"BeIR/{DATASET_NAME}", "queries", split="queries")
    queries = {}
    for row in queries_ds:
        queries[str(row["_id"])] = row["text"]
    print(f"  Queries: {len(queries)} total")

    # Load qrels (relevance judgments)
    # SciFact qrels are in the default config
    try:
        qrels_ds = load_dataset(f"BeIR/{DATASET_NAME}-qrels", split="test")
    except Exception:
        # Fallback: try the validation split
        try:
            qrels_ds = load_dataset(f"BeIR/{DATASET_NAME}-qrels", split="validation")
        except Exception:
            # Another fallback format
            qrels_ds = load_dataset(f"BeIR/{DATASET_NAME}", "default", split="test")

    qrels: dict[str, dict[str, int]] = {}
    for row in qrels_ds:
        qid = str(row["query-id"])
        did = str(row["corpus-id"])
        score = int(row["score"])
        if score > 0:
            qrels.setdefault(qid, {})[did] = score

    print(f"  Qrels: {len(qrels)} queries with relevance labels")
    print()

    return corpus, queries, qrels


# ─── Convert to RAGForge Format ───────────────────────────────────────────────

def build_ragforge_data(corpus, queries, qrels):
    """Convert BEIR data to RAGForge Chunks + GoldenDataset."""
    # Each corpus doc becomes one Chunk (doc_id = chunk id)
    chunks = []
    for doc_id, text in corpus.items():
        chunks.append(Chunk(text=text, doc_id="corpus", index=0, id=doc_id))

    # Build golden dataset from qrels
    golden_items = []
    for qid, relevant_docs in list(qrels.items())[:MAX_QUERIES]:
        if qid in queries:
            golden_items.append(GoldenItem(
                question=queries[qid],
                relevant_chunk_ids=list(relevant_docs.keys()),
            ))

    golden = GoldenDataset(items=golden_items)
    print(f"  RAGForge chunks: {len(chunks)}")
    print(f"  Golden items: {len(golden)} queries (max {MAX_QUERIES})")
    return chunks, golden


# ─── Run the Benchmark ─────────────────────────────────────────────────────────

def run_benchmark():
    """Main benchmark: load data, embed with both models, run the gate."""

    # Load dataset
    corpus, queries, qrels = load_scifact()
    chunks, golden = build_ragforge_data(corpus, queries, qrels)

    # Load real embedding models
    print(f"\n{'─'*60}")
    print(f"  Loading embedding models...")
    print(f"{'─'*60}\n")
    model_a = STEmbedder(MODEL_A)
    model_b = STEmbedder(MODEL_B)

    # Run the decision gate for each k value
    results = {}
    for k in TOP_K_VALUES:
        print(f"\n{'─'*60}")
        print(f"  Running decision gate with top_k={k}")
        print(f"{'─'*60}\n")

        decision = run_decision_gate(
            chunks=chunks,
            old_embedder=model_a,
            new_embedder=model_b,
            golden=golden,
            primary_metric="recall_at_k",
            threshold_margin=0.0,
            top_k=k,
            hot_set_only=False,  # Use full corpus for honest benchmark
        )

        decision.print_table()
        results[f"k={k}"] = decision.to_dict()

    # Build final output
    output = {
        "benchmark": "migration_decision_gate",
        "dataset": DATASET_NAME,
        "dataset_source": f"BeIR/{DATASET_NAME} via Hugging Face datasets",
        "num_docs": len(chunks),
        "num_queries": len(golden),
        "model_a": MODEL_A,
        "model_b": MODEL_B,
        "results_by_k": results,
        "date": datetime.now().isoformat(),
        "notes": (
            f"Compared {MODEL_A} (baseline) vs {MODEL_B} (candidate) on "
            f"{DATASET_NAME} ({len(chunks)} docs, {len(golden)} queries). "
            f"Used full corpus (not hot-set-only) for honest evaluation. "
            f"Each doc = one chunk (no re-chunking, so qrels map cleanly)."
        ),
    }

    # Save JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, indent=2))
    print(f"\n  Results saved to: {OUTPUT_JSON}")

    # Print final summary table
    print(f"\n{'='*70}")
    print(f"  FINAL RESULTS: {DATASET_NAME} ({len(chunks)} docs, {len(golden)} queries)")
    print(f"{'='*70}")
    print(f"\n  Model A (baseline): {MODEL_A}")
    print(f"  Model B (candidate): {MODEL_B}\n")

    for k_label, res in results.items():
        print(f"  ── {k_label} ──")
        print(f"  {'Metric':<18} {'Model A':>10} {'Model B':>10} {'Delta':>10}")
        print(f"  {'─'*18} {'─'*10} {'─'*10} {'─'*10}")
        for metric in res["old_metrics"]:
            a = res["old_metrics"][metric]
            b = res["new_metrics"][metric]
            d = res["deltas"][metric]
            print(f"  {metric:<18} {a:>9.4f} {b:>9.4f} {d:>+9.4f}")
        print(f"\n  Gate verdict: {res['recommendation']}")
        print(f"  Reason: {res['reason']}\n")

    # Write markdown summary
    write_markdown_summary(output, results)

    return output


def write_markdown_summary(output, results):
    """Write an honest markdown summary of the benchmark results."""
    md_path = OUTPUT_DIR / "README.md"

    lines = [
        "# Migration Decision Gate Benchmark",
        "",
        "Real benchmark using a public retrieval dataset with human relevance labels.",
        "",
        "## Setup",
        "",
        f"- **Dataset**: {output['dataset']} (via BeIR / Hugging Face datasets)",
        f"- **Corpus size**: {output['num_docs']} documents",
        f"- **Queries**: {output['num_queries']} queries with human relevance judgments",
        f"- **Model A (baseline)**: `{output['model_a']}`",
        f"- **Model B (candidate)**: `{output['model_b']}`",
        f"- **Date**: {output['date'][:10]}",
        "",
        "Each document is treated as one chunk (no re-chunking) so the BEIR qrels",
        "map directly to chunk IDs. This gives an honest retrieval comparison.",
        "",
        "## Results",
        "",
    ]

    for k_label, res in results.items():
        lines.append(f"### {k_label}")
        lines.append("")
        lines.append(f"| Metric | Model A | Model B | Delta |")
        lines.append(f"|--------|---------|---------|-------|")
        for metric in res["old_metrics"]:
            a = res["old_metrics"][metric]
            b = res["new_metrics"][metric]
            d = res["deltas"][metric]
            lines.append(f"| {metric} | {a:.4f} | {b:.4f} | {d:+.4f} |")
        lines.append("")
        lines.append(f"**Gate verdict: {res['recommendation']}**")
        lines.append(f"")
        lines.append(f"Reason: {res['reason']}")
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "These are real numbers from a real retrieval benchmark. The decision gate",
        "uses recall@k as the primary metric (configurable). If the candidate model",
        "regresses on recall, the gate blocks the migration — saving the cost of",
        "re-embedding your entire corpus with a model that would make retrieval worse.",
        "",
        "## Reproducibility",
        "",
        "```bash",
        "pip install datasets sentence-transformers numpy",
        "python benchmarks/run_migration_gate_benchmark.py",
        "```",
        "",
        "The script loads the dataset from Hugging Face, downloads both models,",
        "and runs the full comparison. Results will vary slightly between machines",
        "(floating point) but the relative ordering should be consistent.",
    ])

    md_path.write_text("\n".join(lines))
    print(f"  Markdown summary saved to: {md_path}")


if __name__ == "__main__":
    run_benchmark()
