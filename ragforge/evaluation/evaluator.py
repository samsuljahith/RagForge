"""
Evaluation engine: precision, recall, and faithfulness metrics.

This module answers "is my RAG getting better or worse?" by comparing retrieval
results against a golden dataset. It powers:
  - Direct evaluation (/evaluate endpoint)
  - A/B comparison between configs
  - Before/after validation for quantization and migration
"""

from __future__ import annotations

from typing import Any


def compute_precision(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Precision: what fraction of retrieved chunks are actually relevant?

    precision = |retrieved ∩ relevant| / |retrieved|
    """
    if not retrieved_ids:
        return 0.0
    retrieved_set = set(retrieved_ids)
    relevant_set = set(relevant_ids)
    return len(retrieved_set & relevant_set) / len(retrieved_set)


def compute_recall(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Recall: what fraction of relevant chunks were retrieved?

    recall = |retrieved ∩ relevant| / |relevant|
    """
    if not relevant_ids:
        return 1.0  # If nothing is relevant, we've "found" everything
    retrieved_set = set(retrieved_ids)
    relevant_set = set(relevant_ids)
    return len(retrieved_set & relevant_set) / len(relevant_set)


def _text_overlap_score(answer: str, expected: str) -> float:
    """
    Simple text overlap faithfulness score.

    In production, this would use an LLM-as-judge. For now, we use word overlap
    as a proxy that works without external API calls.
    """
    if not answer or not expected:
        return 0.0
    answer_words = set(answer.lower().split())
    expected_words = set(expected.lower().split())
    if not expected_words:
        return 0.0
    overlap = len(answer_words & expected_words)
    return min(1.0, overlap / len(expected_words))


def _chunks_contain_answer(chunks: list[dict], expected_answer: str) -> float:
    """Check if retrieved chunks contain the expected answer (text overlap)."""
    if not expected_answer:
        return 1.0
    combined_text = " ".join(c.get("text", "") for c in chunks).lower()
    expected_words = expected_answer.lower().split()
    if not expected_words:
        return 1.0
    found = sum(1 for w in expected_words if w in combined_text)
    return found / len(expected_words)


def evaluate_knowledge_base(
    knowledge: str,
    golden_dataset: list[dict[str, Any]],
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """
    Evaluate a knowledge base against a golden dataset.

    Args:
        knowledge: Name of the knowledge base to evaluate
        golden_dataset: List of dicts with 'question' and optionally
                       'expected_chunks' (list of chunk IDs) and/or
                       'expected_answer' (string)
        metrics: Which metrics to compute (default: all available)

    Returns:
        dict with metrics, summary scores, and question count
    """
    from ragforge.pipeline import query_knowledge_base

    metrics = metrics or ["precision", "recall", "faithfulness"]

    precisions: list[float] = []
    recalls: list[float] = []
    faithfulness_scores: list[float] = []

    for item in golden_dataset:
        question = item.get("question", "")
        expected_chunks = item.get("expected_chunks", [])
        expected_answer = item.get("expected_answer", "")

        if not question:
            continue

        # Query the knowledge base
        result = query_knowledge_base(
            knowledge=knowledge,
            question=question,
            top_k=5,
            rerank=True,
        )

        retrieved_chunks = result.get("chunks", [])
        retrieved_ids = [c["id"] for c in retrieved_chunks]

        # Precision and recall (if expected chunk IDs provided)
        if expected_chunks:
            precisions.append(compute_precision(retrieved_ids, expected_chunks))
            recalls.append(compute_recall(retrieved_ids, expected_chunks))
        else:
            # If no expected chunk IDs, use answer-in-chunks as proxy
            if expected_answer:
                score = _chunks_contain_answer(retrieved_chunks, expected_answer)
                precisions.append(score)
                recalls.append(score)

        # Faithfulness (do retrieved chunks contain the expected answer?)
        if expected_answer:
            faith = _chunks_contain_answer(retrieved_chunks, expected_answer)
            faithfulness_scores.append(faith)

    # Aggregate results
    metric_results = []
    summary = {}

    if "precision" in metrics and precisions:
        avg_precision = sum(precisions) / len(precisions)
        metric_results.append({
            "name": "precision",
            "score": round(avg_precision, 4),
            "details": {"per_question": [round(p, 4) for p in precisions]},
        })
        summary["precision"] = round(avg_precision, 4)

    if "recall" in metrics and recalls:
        avg_recall = sum(recalls) / len(recalls)
        metric_results.append({
            "name": "recall",
            "score": round(avg_recall, 4),
            "details": {"per_question": [round(r, 4) for r in recalls]},
        })
        summary["recall"] = round(avg_recall, 4)

    if "faithfulness" in metrics and faithfulness_scores:
        avg_faith = sum(faithfulness_scores) / len(faithfulness_scores)
        metric_results.append({
            "name": "faithfulness",
            "score": round(avg_faith, 4),
            "details": {"per_question": [round(f, 4) for f in faithfulness_scores]},
        })
        summary["faithfulness"] = round(avg_faith, 4)

    return {
        "knowledge": knowledge,
        "metrics": metric_results,
        "summary": summary,
        "num_questions": len(golden_dataset),
    }


def compare_configs(
    knowledge: str,
    golden_dataset: list[dict[str, Any]],
    config_a: dict[str, Any],
    config_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare two configurations (e.g., different chunking strategies) on the same data.

    Both configs are evaluated and the difference is reported. This is the engine
    behind benchmarking and A/B comparison.

    Args:
        knowledge: Base knowledge name
        golden_dataset: Golden dataset for evaluation
        config_a: First config (e.g. {'chunk_strategy': 'fixed'})
        config_b: Second config (e.g. {'chunk_strategy': 'structure'})

    Returns:
        dict with results_a, results_b, and delta
    """
    from ragforge.pipeline import build_knowledge_base

    # Build KB with config A
    name_a = f"{knowledge}_compare_a"
    build_knowledge_base(name=name_a, sources=config_a.get("sources", []), **config_a)
    results_a = evaluate_knowledge_base(name_a, golden_dataset)

    # Build KB with config B
    name_b = f"{knowledge}_compare_b"
    build_knowledge_base(name=name_b, sources=config_b.get("sources", []), **config_b)
    results_b = evaluate_knowledge_base(name_b, golden_dataset)

    # Compute deltas
    delta = {}
    for key in results_a.get("summary", {}):
        a_val = results_a["summary"].get(key, 0)
        b_val = results_b["summary"].get(key, 0)
        delta[key] = round(b_val - a_val, 4)

    return {
        "config_a": config_a,
        "config_b": config_b,
        "results_a": results_a,
        "results_b": results_b,
        "delta": delta,
        "winner": "b" if sum(delta.values()) > 0 else "a" if sum(delta.values()) < 0 else "tie",
    }
