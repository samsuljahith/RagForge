"""
Evaluation module: measure RAG quality so you can prove changes help.

"No eval meant flying blind — half our improvements were regressions."
This module fixes that by giving you concrete numbers: retrieval metrics
(did we find the right chunks?) and generation metrics (is the answer
grounded and relevant?).

Two interfaces:
  - Library: Evaluator class for full control
  - Functional: evaluate_knowledge_base() for API/CLI

Quick start:
    from ragforge.evaluation import Evaluator, GoldenDataset
    from ragforge.pipeline import KnowledgeBase

    kb = KnowledgeBase.load("my-kb")
    golden = GoldenDataset.load("golden.json")

    evaluator = Evaluator(kb)
    report = evaluator.run(golden, metrics=["hit_rate", "mrr", "precision_at_k"])
    report.print_table()

A/B comparison:
    comparison = Evaluator.compare(kb_a, kb_b, golden)
    Evaluator.print_comparison(comparison)
"""

# Golden dataset
from ragforge.evaluation.golden import GoldenItem, GoldenDataset, generate_golden_draft

# Metrics
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

# Evaluator
from ragforge.evaluation.evaluator import (
    Evaluator,
    EvalReport,
    ItemResult,
    evaluate_knowledge_base,
)

__all__ = [
    # Golden dataset
    "GoldenItem",
    "GoldenDataset",
    "generate_golden_draft",
    # Retrieval metrics
    "hit_rate",
    "precision_at_k",
    "recall_at_k",
    "mrr",
    # Judge metrics
    "judge_faithfulness",
    "judge_answer_relevance",
    # Metric lists
    "RETRIEVAL_METRICS",
    "JUDGE_METRICS",
    "ALL_METRICS",
    # Evaluator
    "Evaluator",
    "EvalReport",
    "ItemResult",
    # Functional interface
    "evaluate_knowledge_base",
]
