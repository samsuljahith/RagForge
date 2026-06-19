"""POST /quantize — quantize models and report cost/quality tradeoff."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["quantization"])


class QuantizeRequest(BaseModel):
    """Request to quantize a model/embedding and compare."""

    target: str = Field(..., description="Model or embedding target to quantize")
    knowledge: Optional[str] = Field(None, description="Knowledge base for quality comparison")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Quantization options (e.g. bits, method)",
    )


class CostQualityReport(BaseModel):
    """Before/after comparison."""

    before: dict[str, Any]
    after: dict[str, Any]
    quality_delta: Optional[float] = None
    cost_reduction: Optional[float] = None


class QuantizeResponse(BaseModel):
    """Response from /quantize."""

    target: str
    status: str
    report: CostQualityReport


@router.post("/quantize", response_model=QuantizeResponse)
def quantize_model(req: QuantizeRequest) -> QuantizeResponse:
    """
    Quantize a model/embedding and report cost vs quality tradeoff.

    Uses the evaluation module to compare before/after on your own data,
    so you see the real impact, not a guess.
    Requires: pip install ragforge[quantization]
    """
    try:
        from ragforge.quantization import quantize_and_compare
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Quantization module not available. Install with: pip install ragforge[quantization]",
        )

    try:
        result = quantize_and_compare(
            target=req.target,
            knowledge=req.knowledge,
            options=req.options,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quantization failed: {e}")

    return QuantizeResponse(**result)
