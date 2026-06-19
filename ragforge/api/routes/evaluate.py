"""POST /evaluate — evaluate RAG quality against a golden dataset."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["evaluation"])


class EvaluateRequest(BaseModel):
    """Request to evaluate a knowledge base."""

    knowledge: str = Field(..., description="Name of the knowledge base to evaluate")
    golden_dataset: list[dict[str, Any]] = Field(
        ...,
        description="List of {question, expected_chunks?, expected_answer?} dicts",
    )
    metrics: list[str] = Field(
        default=["precision", "recall", "faithfulness"],
        description="Metrics to compute",
    )


class MetricResult(BaseModel):
    """One metric's result."""

    name: str
    score: float
    details: Optional[dict[str, Any]] = None


class EvaluateResponse(BaseModel):
    """Response from /evaluate."""

    knowledge: str
    metrics: list[MetricResult]
    summary: dict[str, float]
    num_questions: int


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_knowledge(req: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate retrieval and answer quality against a golden dataset.

    Computes precision, recall, and faithfulness (LLM-as-judge) so you can
    measure improvements instead of guessing.
    Requires the eval module: pip install ragforge[eval]
    """
    try:
        from ragforge.evaluation import evaluate_knowledge_base
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Evaluation module not available. Install with: pip install ragforge[eval]",
        )

    try:
        result = evaluate_knowledge_base(
            knowledge=req.knowledge,
            golden_dataset=req.golden_dataset,
            metrics=req.metrics,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

    return EvaluateResponse(**result)
