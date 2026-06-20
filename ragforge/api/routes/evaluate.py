"""POST /evaluate — evaluate RAG quality against a golden dataset."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["evaluation"])


# ===========================================================================
# Request / Response models
# ===========================================================================


class GoldenItemInput(BaseModel):
    """One item in the golden dataset."""

    question: str
    expected_answer: str = ""
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    relevant_sources: list[str] = Field(default_factory=list)
    notes: str = ""


class EvaluateRequest(BaseModel):
    """Request to evaluate a knowledge base."""

    knowledge: str = Field(..., description="Name of the knowledge base to evaluate")
    golden_dataset: list[GoldenItemInput] = Field(
        ...,
        description="List of golden items (question + expected outputs)",
    )
    metrics: list[str] = Field(
        default=["hit_rate", "precision_at_k", "recall_at_k", "mrr"],
        description="Metrics to compute. Retrieval: hit_rate, precision_at_k, recall_at_k, mrr. "
                    "Judge (need llm): faithfulness, answer_relevance",
    )
    top_k: int = Field(5, description="Number of chunks to retrieve per query", ge=1, le=100)
    mode: Literal["dense", "bm25", "hybrid"] = Field("hybrid", description="Retrieval mode")
    rerank: bool = Field(False, description="Apply cross-encoder reranking")
    generate: bool = Field(False, description="Generate answers (needed for judge metrics)")
    llm: Optional[str] = Field(None, description="LLM provider for generation + judge metrics")


class MetricScore(BaseModel):
    """One metric result."""

    name: str
    score: float


class EvaluateResponse(BaseModel):
    """Response from /evaluate."""

    knowledge: str
    summary: dict[str, float]
    metrics: list[MetricScore]
    num_questions: int
    config: dict[str, Any]


# ===========================================================================
# POST /evaluate
# ===========================================================================


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_knowledge(req: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate retrieval (and optionally generation) quality against a golden dataset.

    Retrieval metrics (always available, no LLM needed):
    - **hit_rate**: Did at least one relevant chunk appear in top-k?
    - **precision_at_k**: Of the k retrieved, how many were relevant?
    - **recall_at_k**: Of all relevant chunks, how many were retrieved?
    - **mrr**: How high up was the first relevant chunk?

    LLM-judge metrics (need `generate: true` + `llm` configured):
    - **faithfulness**: Is the answer grounded in context (not hallucinated)?
    - **answer_relevance**: Does the answer address the question?
    """
    from ragforge.evaluation import evaluate_knowledge_base

    try:
        golden_dicts = [item.model_dump() for item in req.golden_dataset]
        result = evaluate_knowledge_base(
            knowledge=req.knowledge,
            golden_dataset=golden_dicts,
            metrics=req.metrics,
            top_k=req.top_k,
            mode=req.mode,
            rerank=req.rerank,
            generate=req.generate,
            llm=req.llm,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ImportError, ValueError, ConnectionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

    return EvaluateResponse(
        knowledge=result["knowledge"],
        summary=result["summary"],
        metrics=[MetricScore(name=m["name"], score=m["score"]) for m in result["metrics"]],
        num_questions=result["num_questions"],
        config=result.get("config", {}),
    )
