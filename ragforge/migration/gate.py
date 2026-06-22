"""
Migration Decision Gate: compare old vs new embedding model on YOUR queries
before committing to a full re-embed.

The gate answers one question: "Will the new model actually retrieve better
on my real queries?" If yes → GO (proceed with migration). If no → NO_GO
(abort, nothing is re-embedded, no money wasted).

Uses the existing Evaluator to compute recall@k, precision@k, and MRR for
both models against a golden dataset, then applies a threshold policy.

Usage:
    from ragforge.migration.gate import run_decision_gate

    decision = run_decision_gate(
        chunks=kb.chunks,
        old_embedder=old_emb,
        new_embedder=new_emb,
        golden=golden_dataset,
        primary_metric="recall_at_k",
        threshold_margin=0.0,
    )
    print(decision["recommendation"])  # "GO" or "NO_GO"
    print(decision["reason"])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ragforge.core.models import Chunk
from ragforge.evaluation.evaluator import Evaluator
from ragforge.evaluation.golden import GoldenDataset
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline.embeddings import Embedder
from ragforge.pipeline.knowledge import KnowledgeBase
from ragforge.pipeline.store import InMemoryStore


# Pure retrieval metrics — no LLM needed, fast and deterministic.
GATE_METRICS = ["recall_at_k", "precision_at_k", "mrr"]


@dataclass
class GateDecision:
    """
    Structured result from the decision gate.

    recommendation: "GO" (new model is acceptable) or "NO_GO" (regresses)
    old_metrics: metric scores for the old model
    new_metrics: metric scores for the new model
    deltas: new - old for each metric (positive = new is better)
    primary_metric: which metric was used for the GO/NO_GO decision
    threshold_margin: how much the new model is allowed to regress
    reason: human-readable explanation of the decision
    """

    recommendation: str  # "GO" or "NO_GO"
    old_metrics: dict[str, float]
    new_metrics: dict[str, float]
    deltas: dict[str, float]
    primary_metric: str
    threshold_margin: float
    reason: str
    hot_set_size: int = 0
    total_chunks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "old_metrics": self.old_metrics,
            "new_metrics": self.new_metrics,
            "deltas": self.deltas,
            "primary_metric": self.primary_metric,
            "threshold_margin": self.threshold_margin,
            "reason": self.reason,
            "hot_set_size": self.hot_set_size,
            "total_chunks": self.total_chunks,
        }

    def print_table(self) -> None:
        """Print a clean comparison table with the GO/NO_GO verdict."""
        print()
        print("=" * 60)
        print("  MIGRATION DECISION GATE")
        print("=" * 60)
        print()
        print(f"  {'Metric':<20} {'Old Model':>12} {'New Model':>12} {'Delta':>10}")
        print(f"  {'─' * 20} {'─' * 12} {'─' * 12} {'─' * 10}")
        for metric in self.old_metrics:
            old_val = self.old_metrics[metric]
            new_val = self.new_metrics.get(metric, 0.0)
            delta = self.deltas.get(metric, 0.0)
            marker = " ◀" if metric == self.primary_metric else ""
            print(f"  {metric:<20} {old_val:>11.4f} {new_val:>11.4f} {delta:>+9.4f}{marker}")
        print()
        print(f"  Primary metric: {self.primary_metric}")
        print(f"  Threshold margin: {self.threshold_margin}")
        print(f"  Hot set: {self.hot_set_size} chunks (of {self.total_chunks} total)")
        print()
        if self.recommendation == "GO":
            print(f"  ✓ RECOMMENDATION: GO — {self.reason}")
        else:
            print(f"  ✗ RECOMMENDATION: NO_GO — {self.reason}")
        print("=" * 60)
        print()


def _build_shadow_kb(
    name: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
    embedder: Embedder,
) -> KnowledgeBase:
    """Build an in-memory KnowledgeBase for gate evaluation (not persisted)."""
    store = InMemoryStore()
    if chunks and vectors:
        store.add(chunks, vectors)
    bm25 = BM25Index()
    return KnowledgeBase(name=name, embedder=embedder, store=store, bm25=bm25)


def identify_hot_set(
    chunks: list[Chunk],
    golden: GoldenDataset,
) -> tuple[list[Chunk], list[Chunk]]:
    """
    Split chunks into hot set (referenced by golden queries) and cold tail.

    The hot set is the subset of chunks that golden dataset items reference
    via relevant_chunk_ids. These are the chunks real queries actually need.

    Returns:
        (hot_chunks, cold_chunks)
    """
    hot_ids = set()
    for item in golden:
        hot_ids.update(item.relevant_chunk_ids)

    chunk_ids = {c.id for c in chunks}
    hot_ids &= chunk_ids  # only IDs that exist in this KB

    hot = [c for c in chunks if c.id in hot_ids]
    cold = [c for c in chunks if c.id not in hot_ids]
    return hot, cold


def run_decision_gate(
    chunks: list[Chunk],
    old_embedder: Embedder,
    new_embedder: Embedder,
    golden: GoldenDataset,
    primary_metric: str = "recall_at_k",
    threshold_margin: float = 0.0,
    top_k: int = 5,
    hot_set_only: bool = True,
) -> GateDecision:
    """
    Run the migration decision gate: compare old vs new embedding model
    on a golden dataset and return a GO/NO_GO recommendation.

    The gate embeds the corpus with both models, runs retrieval for each
    golden query, and computes recall@k, precision@k, and MRR. GO is
    recommended only if the new model's primary metric is >= old model's
    minus the threshold_margin.

    Args:
        chunks: The chunks to evaluate against (from the KB).
        old_embedder: The current embedding model.
        new_embedder: The candidate embedding model.
        golden: Golden dataset with questions + relevant_chunk_ids.
        primary_metric: Which metric decides GO/NO_GO (default: recall_at_k).
        threshold_margin: How much regression is allowed on the primary metric.
                          0.0 = new must be >= old. 0.05 = up to 5% regression OK.
        top_k: Number of results to retrieve for metric computation.
        hot_set_only: If True, only embed/evaluate the hot set (chunks referenced
                      by golden queries). Cheaper and more representative.

    Returns:
        GateDecision with recommendation, metrics, deltas, and reason.
    """
    if not golden or len(golden) == 0:
        return GateDecision(
            recommendation="GO",
            old_metrics={},
            new_metrics={},
            deltas={},
            primary_metric=primary_metric,
            threshold_margin=threshold_margin,
            reason="No golden dataset provided — gate skipped (nothing to compare against).",
            hot_set_size=0,
            total_chunks=len(chunks),
        )

    # Determine which chunks to evaluate
    if hot_set_only:
        eval_chunks, cold_chunks = identify_hot_set(chunks, golden)
        if not eval_chunks:
            eval_chunks = chunks  # fallback: no relevant_chunk_ids → use all
    else:
        eval_chunks = chunks
        cold_chunks = []

    # Embed with both models
    texts = [c.text for c in eval_chunks]
    old_vectors = old_embedder.encode(texts)
    new_vectors = new_embedder.encode(texts)

    # Build shadow KBs for evaluation
    old_kb = _build_shadow_kb("old_model", eval_chunks, old_vectors, old_embedder)
    new_kb = _build_shadow_kb("new_model", eval_chunks, new_vectors, new_embedder)

    # Run A/B comparison using existing Evaluator
    comparison = Evaluator.compare(
        old_kb,
        new_kb,
        golden,
        metrics=GATE_METRICS,
        top_k=top_k,
        mode="dense",  # Dense-only so we're measuring the embedder, not BM25
        label_a="old_model",
        label_b="new_model",
    )

    old_metrics = comparison["report_a"]["summary"]
    new_metrics = comparison["report_b"]["summary"]
    deltas = comparison["delta"]

    # Apply threshold policy on the primary metric
    old_primary = old_metrics.get(primary_metric, 0.0)
    new_primary = new_metrics.get(primary_metric, 0.0)
    allowed_minimum = old_primary - threshold_margin

    if new_primary >= allowed_minimum:
        if new_primary > old_primary:
            reason = f"New model improves {primary_metric}: {old_primary:.4f} → {new_primary:.4f} (+{new_primary - old_primary:.4f})"
        elif new_primary == old_primary:
            reason = f"New model ties on {primary_metric} ({new_primary:.4f}). Within margin."
        else:
            reason = f"New model regresses {primary_metric} by {old_primary - new_primary:.4f}, but within allowed margin ({threshold_margin})."
        recommendation = "GO"
    else:
        reason = (
            f"New model regresses {primary_metric}: {old_primary:.4f} → {new_primary:.4f} "
            f"(delta: {new_primary - old_primary:+.4f}, exceeds margin {threshold_margin})"
        )
        recommendation = "NO_GO"

    return GateDecision(
        recommendation=recommendation,
        old_metrics=old_metrics,
        new_metrics=new_metrics,
        deltas=deltas,
        primary_metric=primary_metric,
        threshold_margin=threshold_margin,
        reason=reason,
        hot_set_size=len(eval_chunks),
        total_chunks=len(chunks),
    )


# ─── POST-MIGRATION SMOKE TEST ────────────────────────────────────────────────


@dataclass
class SmokeTestResult:
    """
    Result of a post-migration smoke test.

    passed: True if all checks pass.
    checks: list of individual check results.
    summary: human-readable summary.
    """

    passed: bool
    checks: list[dict[str, Any]]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "summary": self.summary,
        }

    def print_summary(self) -> None:
        print()
        print("=" * 50)
        print("  POST-MIGRATION SMOKE TEST")
        print("=" * 50)
        for check in self.checks:
            status = "✓" if check["passed"] else "✗"
            print(f"  {status} {check['name']}: {check['detail']}")
        print()
        if self.passed:
            print(f"  ✓ PASSED — {self.summary}")
        else:
            print(f"  ✗ FAILED — {self.summary}")
        print("=" * 50)
        print()


def smoke_test(
    knowledge: str,
    golden: GoldenDataset,
    top_k: int = 5,
    min_results: int = 1,
    min_hit_rate: float = 0.5,
) -> SmokeTestResult:
    """
    Post-migration smoke test: verify the migrated KB actually works.

    "Command returned OK" is not enough — this confirms retrieval actually
    returns sensible results on real queries after the cutover.

    Checks:
      1. KB loads successfully
      2. Each golden query returns at least `min_results` chunks (non-empty)
      3. Expected chunks (from relevant_chunk_ids) appear in results above threshold
      4. Overall hit rate >= min_hit_rate

    Args:
        knowledge: Name of the knowledge base to test.
        golden: Golden dataset with real queries.
        top_k: How many results to retrieve per query.
        min_results: Minimum chunks expected per query (default: 1).
        min_hit_rate: Minimum fraction of queries that find a relevant chunk.

    Returns:
        SmokeTestResult with pass/fail and per-check details.
    """
    from ragforge.pipeline.knowledge import KnowledgeBase

    checks: list[dict[str, Any]] = []

    # Check 1: KB loads
    try:
        kb = KnowledgeBase.load(knowledge)
        checks.append({"name": "KB loads", "passed": True, "detail": f"Loaded '{knowledge}' successfully"})
    except Exception as e:
        checks.append({"name": "KB loads", "passed": False, "detail": f"Failed to load: {e}"})
        return SmokeTestResult(
            passed=False,
            checks=checks,
            summary=f"Knowledge base '{knowledge}' failed to load after migration.",
        )

    # Check 2 & 3: Run golden queries and verify results
    empty_count = 0
    hit_count = 0
    total = len(golden)

    if total == 0:
        checks.append({"name": "Queries run", "passed": True, "detail": "No golden queries to test (skipped)"})
        return SmokeTestResult(passed=True, checks=checks, summary="No queries to verify (golden set empty).")

    for item in golden:
        results = kb.query(item.question, mode="dense", top_k=top_k)
        retrieved_ids = [chunk.id for chunk, _ in results]

        if len(results) < min_results:
            empty_count += 1
        else:
            # Check if any expected chunk appears in results
            if item.relevant_chunk_ids:
                hit = any(cid in retrieved_ids for cid in item.relevant_chunk_ids)
                if hit:
                    hit_count += 1
            else:
                # No expected chunks specified — just count non-empty as a hit
                hit_count += 1

    # Non-empty results check
    non_empty_rate = (total - empty_count) / total
    check2_passed = empty_count == 0
    checks.append({
        "name": "Non-empty results",
        "passed": check2_passed,
        "detail": f"{total - empty_count}/{total} queries returned >= {min_results} results",
    })

    # Hit rate check
    actual_hit_rate = hit_count / total
    check3_passed = actual_hit_rate >= min_hit_rate
    checks.append({
        "name": "Hit rate",
        "passed": check3_passed,
        "detail": f"{actual_hit_rate:.0%} of queries hit expected chunks (threshold: {min_hit_rate:.0%})",
    })

    all_passed = all(c["passed"] for c in checks)

    if all_passed:
        summary = f"All {total} queries return results and hit rate is {actual_hit_rate:.0%}. Migration verified."
    else:
        failures = [c["name"] for c in checks if not c["passed"]]
        summary = f"Failed checks: {', '.join(failures)}. Review the migrated index."

    return SmokeTestResult(passed=all_passed, checks=checks, summary=summary)
