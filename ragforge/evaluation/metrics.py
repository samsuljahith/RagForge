"""
Evaluation metrics for RAGForge.

Two categories:

RETRIEVAL METRICS (pure math, zero deps, always available):
  - hit_rate (Recall@k): Did ANY relevant chunk appear in the top k?
  - precision_at_k: Of the k retrieved chunks, what fraction were relevant?
  - mrr (Mean Reciprocal Rank): How high up was the FIRST relevant chunk?

LLM-JUDGE METRICS (need a configured LLM, mockable in tests):
  - faithfulness: Is the generated answer grounded in the context (not hallucinated)?
  - answer_relevance: Does the answer actually address the question asked?

The retrieval metrics take lists of IDs and return floats [0, 1].
The judge metrics take text and return floats [0, 1] via an LLM prompt.
"""

from __future__ import annotations

from typing import Any

from ragforge.core.registry import register


# ===========================================================================
# RETRIEVAL METRICS — pure math, no LLM needed
# ===========================================================================


@register("metric", "hit_rate")
def hit_rate(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Hit Rate (Recall@k): did at least one relevant chunk appear in the results?

    Returns 1.0 if ANY relevant chunk was retrieved, 0.0 otherwise.
    This is the most forgiving retrieval metric — it only asks "did you find
    at least one right answer?" not "did you find all of them?"

    Use when: you just need the system to surface at least one relevant piece.
    """
    if not relevant_ids:
        return 1.0  # Vacuously true if nothing is relevant
    return 1.0 if set(retrieved_ids) & set(relevant_ids) else 0.0


@register("metric", "precision_at_k")
def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Precision@k: of the k retrieved chunks, what fraction were relevant?

    precision = |retrieved ∩ relevant| / |retrieved|

    High precision means "most of what I showed the user was useful."
    Low precision means "I'm drowning the user in irrelevant results."
    """
    if not retrieved_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    hits = sum(1 for rid in retrieved_ids if rid in relevant_set)
    return hits / len(retrieved_ids)


@register("metric", "recall_at_k")
def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Recall@k: of all the relevant chunks, what fraction did we retrieve?

    recall = |retrieved ∩ relevant| / |relevant|

    High recall means "I found most of the relevant information."
    Low recall means "I'm missing important chunks."
    """
    if not relevant_ids:
        return 1.0
    retrieved_set = set(retrieved_ids)
    hits = sum(1 for rid in relevant_ids if rid in retrieved_set)
    return hits / len(relevant_ids)


@register("metric", "mrr")
def mrr(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Mean Reciprocal Rank (MRR): how high up was the FIRST relevant chunk?

    MRR = 1 / rank_of_first_relevant_result

    MRR = 1.0 means the first result was relevant (best possible).
    MRR = 0.5 means the second result was the first relevant one.
    MRR = 0.0 means no relevant result was found at all.

    Use when: ranking quality matters — you want the best answer on TOP.
    """
    if not relevant_ids:
        return 1.0
    relevant_set = set(relevant_ids)
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_set:
            return 1.0 / rank
    return 0.0


# ===========================================================================
# LLM-JUDGE METRICS — need a configured LLM provider
# ===========================================================================

# These are clearly MODEL-BASED judgments, not perfectly objective.
# They're useful for catching obvious failures (hallucinations, off-topic answers)
# but should not be treated as absolute truth.

FAITHFULNESS_PROMPT = """You are an impartial judge evaluating whether an answer is faithful to the provided context.

CONTEXT (the retrieved chunks the answer should be based on):
{context}

ANSWER being evaluated:
{answer}

TASK: Rate the faithfulness of the answer on a scale of 0 to 1:
- 1.0 = Every claim in the answer is supported by the context
- 0.5 = Some claims are supported, some are not
- 0.0 = The answer makes claims not found in the context (hallucination)

Respond with ONLY a single number between 0 and 1 (e.g. "0.8"). Nothing else."""

RELEVANCE_PROMPT = """You are an impartial judge evaluating whether an answer is relevant to the question.

QUESTION: {question}

ANSWER: {answer}

TASK: Rate how well the answer addresses the question on a scale of 0 to 1:
- 1.0 = The answer directly and completely addresses the question
- 0.5 = The answer partially addresses the question
- 0.0 = The answer is completely off-topic or doesn't address the question

Respond with ONLY a single number between 0 and 1 (e.g. "0.8"). Nothing else."""


def _parse_score(response: str) -> float:
    """Parse a float score from an LLM response. Robust to extra text."""
    response = response.strip()
    # Try to find a float in the response
    for token in response.split():
        try:
            score = float(token.strip(".,;:()"))
            if 0.0 <= score <= 1.0:
                return score
        except ValueError:
            continue
    # If parsing fails, default to 0.5 (uncertain)
    return 0.5


def judge_faithfulness(
    answer: str,
    context_chunks: list[str],
    llm_provider: Any,
) -> float:
    """
    LLM-as-judge: is the answer faithful to (grounded in) the retrieved context?

    Detects hallucination — claims the model made that aren't in the source chunks.
    This is the most important generation metric: a hallucinated answer is worse
    than no answer at all.

    Args:
        answer: The generated answer text.
        context_chunks: List of chunk texts that were used as context.
        llm_provider: An LLMProvider instance (from pipeline.generation).

    Returns:
        Float 0-1 (1 = fully faithful, 0 = hallucinated).
    """
    if not answer or not context_chunks:
        return 0.0

    context = "\n---\n".join(context_chunks)
    prompt = FAITHFULNESS_PROMPT.format(context=context, answer=answer)
    response = llm_provider.generate(prompt, temperature=0.0)
    return _parse_score(response)


def judge_answer_relevance(
    question: str,
    answer: str,
    llm_provider: Any,
) -> float:
    """
    LLM-as-judge: does the answer actually address the question?

    Detects off-topic or evasive answers. A faithful answer that doesn't
    address the question is still useless.

    Args:
        question: The original question.
        answer: The generated answer text.
        llm_provider: An LLMProvider instance.

    Returns:
        Float 0-1 (1 = fully relevant, 0 = off-topic).
    """
    if not answer or not question:
        return 0.0

    prompt = RELEVANCE_PROMPT.format(question=question, answer=answer)
    response = llm_provider.generate(prompt, temperature=0.0)
    return _parse_score(response)


# ===========================================================================
# Registry of available metrics (for /capabilities and CLI --metrics)
# ===========================================================================

RETRIEVAL_METRICS = ["hit_rate", "precision_at_k", "recall_at_k", "mrr"]
JUDGE_METRICS = ["faithfulness", "answer_relevance"]
ALL_METRICS = RETRIEVAL_METRICS + JUDGE_METRICS
