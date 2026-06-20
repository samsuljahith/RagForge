"""
The Evaluator: run metrics against a golden dataset and produce a structured report.

This is the main orchestrator for evaluation. It ties together:
  - A KnowledgeBase (to retrieve/generate answers)
  - A GoldenDataset (the ground truth)
  - Metrics (retrieval + optional LLM-judge)

And produces an EvalReport with per-item scores, aggregate averages, and the
config that was used — so results are reproducible.

The killer feature: compare() runs the SAME golden dataset against TWO configs
and reports the metric deltas side by side. This is how you prove which setting
is better on YOUR data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ragforge.evaluation.golden import GoldenDataset, GoldenItem
from ragforge.evaluation.metrics import (
    hit_rate,
    precision_at_k,
    recall_at_k,
    mrr,
    judge_faithfulness,
    judge_answer_relevance,
    RETRIEVAL_METRICS,
    JUDGE_METRICS,
    ALL_METRICS,
)


# ===========================================================================
# EvalReport — structured output from an evaluation run
# ===========================================================================


@dataclass
class ItemResult:
    """Result for one golden item."""

    question: str
    scores: dict[str, float] = field(default_factory=dict)
    retrieved_ids: list[str] = field(default_factory=list)
    answer: str = ""


@dataclass
class EvalReport:
    """
    Structured output from an evaluation run.

    Contains per-item scores, aggregate averages, and the config used —
    everything needed to reproduce and compare results.
    """

    knowledge: str
    config: dict[str, Any] = field(default_factory=dict)
    items: list[ItemResult] = field(default_factory=list)
    summary: dict[str, float] = field(default_factory=dict)
    num_items: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON/API output."""
        return {
            "knowledge": self.knowledge,
            "config": self.config,
            "summary": self.summary,
            "num_items": self.num_items,
            "items": [asdict(item) for item in self.items],
        }

    def to_json(self, path: str | Path) -> None:
        """Export the report to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def print_table(self) -> str:
        """
        Pretty-print as a readable table.

        Returns the formatted string (also prints it).
        """
        lines = []
        lines.append(f"{'─' * 60}")
        lines.append(f"  Evaluation Report: {self.knowledge}")
        lines.append(f"  Config: mode={self.config.get('mode', '?')}, "
                     f"k={self.config.get('top_k', '?')}, "
                     f"rerank={self.config.get('rerank', False)}, "
                     f"generate={self.config.get('generate', False)}")
        lines.append(f"  Items evaluated: {self.num_items}")
        lines.append(f"{'─' * 60}")
        lines.append(f"  {'Metric':<20} {'Score':>8}")
        lines.append(f"  {'─' * 30}")
        for metric, score in self.summary.items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            lines.append(f"  {metric:<20} {score:>6.3f}  {bar}")
        lines.append(f"{'─' * 60}")
        output = "\n".join(lines)
        print(output)
        return output


# ===========================================================================
# Evaluator — the main class
# ===========================================================================


class Evaluator:
    """
    Run metrics against a golden dataset using a KnowledgeBase.

    Usage:
        from ragforge.evaluation import Evaluator, GoldenDataset
        from ragforge.pipeline import KnowledgeBase

        kb = KnowledgeBase.load("my-kb")
        golden = GoldenDataset.load("golden.json")

        evaluator = Evaluator(kb)
        report = evaluator.run(golden, metrics=["hit_rate", "mrr", "precision_at_k"])
        report.print_table()
    """

    def __init__(self, knowledge_base: Any) -> None:
        """
        Args:
            knowledge_base: A KnowledgeBase instance (from ragforge.pipeline).
        """
        self.kb = knowledge_base

    def run(
        self,
        golden: GoldenDataset,
        metrics: list[str] | None = None,
        top_k: int = 5,
        mode: str = "hybrid",
        rerank: bool = False,
        generate: bool = False,
        llm: str | None = None,
        llm_opts: dict[str, Any] | None = None,
    ) -> EvalReport:
        """
        Run evaluation: query the KB for each golden item and compute metrics.

        Args:
            golden: The golden dataset (ground truth).
            metrics: Which metrics to compute (default: all retrieval metrics).
                     LLM-judge metrics ("faithfulness", "answer_relevance") need
                     generate=True and a configured LLM.
            top_k: Number of chunks to retrieve per query.
            mode: Retrieval mode ("dense", "bm25", "hybrid").
            rerank: Whether to apply cross-encoder reranking.
            generate: Whether to generate answers (needed for judge metrics).
            llm: LLM provider name (for generation + judge metrics).
            llm_opts: Options for the LLM provider.

        Returns:
            An EvalReport with per-item and aggregate scores.
        """
        if metrics is None:
            metrics = list(RETRIEVAL_METRICS)
            if generate and llm:
                metrics.extend(JUDGE_METRICS)

        # Check if judge metrics are requested but LLM isn't configured
        judge_requested = [m for m in metrics if m in JUDGE_METRICS]
        llm_provider = None
        if judge_requested:
            if not llm:
                import warnings
                warnings.warn(
                    f"LLM-judge metrics {judge_requested} requested but no LLM configured. "
                    "These metrics will be skipped. Use llm='ollama' (or 'openai'/'anthropic') "
                    "to enable them.",
                    stacklevel=2,
                )
                metrics = [m for m in metrics if m not in JUDGE_METRICS]
            else:
                from ragforge.pipeline.generation import get_llm
                llm_provider = get_llm(llm, **(llm_opts or {}))

        config = {
            "top_k": top_k,
            "mode": mode,
            "rerank": rerank,
            "generate": generate,
            "llm": llm,
            "metrics": metrics,
        }

        items: list[ItemResult] = []
        metric_totals: dict[str, list[float]] = {m: [] for m in metrics}

        for golden_item in golden:
            item_result = self._evaluate_item(
                golden_item=golden_item,
                metrics=metrics,
                top_k=top_k,
                mode=mode,
                rerank=rerank,
                generate=generate,
                llm=llm,
                llm_opts=llm_opts,
                llm_provider=llm_provider,
            )
            items.append(item_result)

            for metric_name, score in item_result.scores.items():
                if metric_name in metric_totals:
                    metric_totals[metric_name].append(score)

        # Compute averages
        summary = {}
        for metric_name, scores in metric_totals.items():
            if scores:
                summary[metric_name] = round(sum(scores) / len(scores), 4)

        return EvalReport(
            knowledge=self.kb.name,
            config=config,
            items=items,
            summary=summary,
            num_items=len(items),
        )

    def _evaluate_item(
        self,
        golden_item: GoldenItem,
        metrics: list[str],
        top_k: int,
        mode: str,
        rerank: bool,
        generate: bool,
        llm: str | None,
        llm_opts: dict[str, Any] | None,
        llm_provider: Any,
    ) -> ItemResult:
        """Evaluate a single golden item."""
        # Retrieve
        results = self.kb.query(
            question=golden_item.question,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
        )
        retrieved_ids = [chunk.id for chunk, _score in results]
        retrieved_texts = [chunk.text for chunk, _score in results]

        # Generate answer if needed
        answer_text = ""
        if generate and llm:
            try:
                answer_result = self.kb.answer(
                    question=golden_item.question,
                    top_k=top_k,
                    mode=mode,
                    rerank=rerank,
                    llm=llm,
                    llm_opts=llm_opts or {},
                )
                answer_text = answer_result.get("answer", "")
            except Exception:
                answer_text = ""

        # Compute scores
        scores: dict[str, float] = {}
        relevant_ids = golden_item.relevant_chunk_ids

        for metric_name in metrics:
            if metric_name == "hit_rate":
                scores[metric_name] = hit_rate(retrieved_ids, relevant_ids)
            elif metric_name == "precision_at_k":
                scores[metric_name] = precision_at_k(retrieved_ids, relevant_ids)
            elif metric_name == "recall_at_k":
                scores[metric_name] = recall_at_k(retrieved_ids, relevant_ids)
            elif metric_name == "mrr":
                scores[metric_name] = mrr(retrieved_ids, relevant_ids)
            elif metric_name == "faithfulness" and llm_provider and answer_text:
                scores[metric_name] = judge_faithfulness(
                    answer=answer_text,
                    context_chunks=retrieved_texts,
                    llm_provider=llm_provider,
                )
            elif metric_name == "answer_relevance" and llm_provider and answer_text:
                scores[metric_name] = judge_answer_relevance(
                    question=golden_item.question,
                    answer=answer_text,
                    llm_provider=llm_provider,
                )

        return ItemResult(
            question=golden_item.question,
            scores=scores,
            retrieved_ids=retrieved_ids,
            answer=answer_text,
        )

    # ------------------------------------------------------------------
    # A/B Compare — the killer feature
    # ------------------------------------------------------------------

    @classmethod
    def compare(
        cls,
        knowledge_base_a: Any,
        knowledge_base_b: Any,
        golden: GoldenDataset,
        metrics: list[str] | None = None,
        top_k: int = 5,
        mode: str = "hybrid",
        rerank: bool = False,
        generate: bool = False,
        llm: str | None = None,
        llm_opts: dict[str, Any] | None = None,
        label_a: str = "Config A",
        label_b: str = "Config B",
    ) -> dict[str, Any]:
        """
        A/B comparison: run the SAME golden dataset against two KBs and report deltas.

        This is how you prove which setting is better on YOUR data — not on
        someone else's benchmark, not on vibes, but on your actual questions.

        Args:
            knowledge_base_a: First KB (or first config).
            knowledge_base_b: Second KB (or second config).
            golden: The golden dataset (same for both).
            metrics: Which metrics to compare.
            top_k, mode, rerank, generate, llm: Settings for both runs.
            label_a, label_b: Human-readable labels for the two configs.

        Returns:
            dict with report_a, report_b, delta (B - A), and winner.
        """
        eval_a = cls(knowledge_base_a)
        eval_b = cls(knowledge_base_b)

        report_a = eval_a.run(
            golden, metrics=metrics, top_k=top_k, mode=mode,
            rerank=rerank, generate=generate, llm=llm, llm_opts=llm_opts,
        )
        report_b = eval_b.run(
            golden, metrics=metrics, top_k=top_k, mode=mode,
            rerank=rerank, generate=generate, llm=llm, llm_opts=llm_opts,
        )

        # Compute deltas (B - A: positive means B is better)
        delta = {}
        for metric_name in report_a.summary:
            a_val = report_a.summary.get(metric_name, 0.0)
            b_val = report_b.summary.get(metric_name, 0.0)
            delta[metric_name] = round(b_val - a_val, 4)

        # Determine winner by sum of deltas
        total_delta = sum(delta.values())
        if total_delta > 0.001:
            winner = label_b
        elif total_delta < -0.001:
            winner = label_a
        else:
            winner = "tie"

        return {
            "label_a": label_a,
            "label_b": label_b,
            "report_a": report_a.to_dict(),
            "report_b": report_b.to_dict(),
            "delta": delta,
            "winner": winner,
        }

    @staticmethod
    def print_comparison(comparison: dict[str, Any]) -> str:
        """Pretty-print an A/B comparison result."""
        lines = []
        lines.append(f"{'═' * 60}")
        lines.append(f"  A/B Comparison")
        lines.append(f"  {comparison['label_a']} vs {comparison['label_b']}")
        lines.append(f"{'═' * 60}")
        lines.append(f"  {'Metric':<20} {'A':>8} {'B':>8} {'Δ (B-A)':>10}")
        lines.append(f"  {'─' * 50}")

        summary_a = comparison["report_a"]["summary"]
        summary_b = comparison["report_b"]["summary"]
        delta = comparison["delta"]

        for metric_name in delta:
            a_val = summary_a.get(metric_name, 0.0)
            b_val = summary_b.get(metric_name, 0.0)
            d_val = delta[metric_name]
            indicator = "↑" if d_val > 0 else "↓" if d_val < 0 else "="
            lines.append(
                f"  {metric_name:<20} {a_val:>7.3f} {b_val:>7.3f} "
                f"{d_val:>+7.3f} {indicator}"
            )

        lines.append(f"  {'─' * 50}")
        lines.append(f"  Winner: {comparison['winner']}")
        lines.append(f"{'═' * 60}")
        output = "\n".join(lines)
        print(output)
        return output


# ===========================================================================
# Module-level convenience function (backward compat with existing API route)
# ===========================================================================


def evaluate_knowledge_base(
    knowledge: str,
    golden_dataset: list[dict[str, Any]],
    metrics: list[str] | None = None,
    top_k: int = 5,
    mode: str = "hybrid",
    rerank: bool = False,
    generate: bool = False,
    llm: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate a knowledge base (functional interface for API/CLI).

    Loads the KB and golden dataset, runs metrics, returns a plain dict.
    """
    from ragforge.pipeline import KnowledgeBase

    kb = KnowledgeBase.load(knowledge)
    golden = GoldenDataset.from_dicts(golden_dataset)

    evaluator = Evaluator(kb)
    report = evaluator.run(
        golden, metrics=metrics, top_k=top_k, mode=mode,
        rerank=rerank, generate=generate, llm=llm,
    )

    return {
        "knowledge": report.knowledge,
        "metrics": [
            {"name": name, "score": score}
            for name, score in report.summary.items()
        ],
        "summary": report.summary,
        "num_questions": report.num_items,
        "config": report.config,
    }
