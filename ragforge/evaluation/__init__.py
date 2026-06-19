"""
Evaluation module: measure retrieval and answer quality.

Computes precision, recall, and faithfulness against a golden dataset so you can
prove improvements instead of guessing. Also serves as the engine for benchmarking
(compare config A vs B) and for validating quantization/migration results.

Quick start:
    from ragforge.evaluation import evaluate_knowledge_base

    result = evaluate_knowledge_base(
        knowledge="my-kb",
        golden_dataset=[
            {"question": "What is the refund window?", "expected_answer": "30 days"},
        ],
    )
"""

from ragforge.evaluation.evaluator import (
    evaluate_knowledge_base,
    compute_precision,
    compute_recall,
    compare_configs,
)

__all__ = [
    "evaluate_knowledge_base",
    "compute_precision",
    "compute_recall",
    "compare_configs",
]
