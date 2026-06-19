"""POST /migrate — migrate a knowledge base from one embedding model to another."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["migration"])


class MigrateRequest(BaseModel):
    """Request to migrate a knowledge base between embedding models."""

    knowledge: str = Field(..., description="Name of the knowledge base to migrate")
    from_model: str = Field(..., description="Current embedding model")
    to_model: str = Field(..., description="Target embedding model")
    run_validation: bool = Field(True, description="Run evaluation before/after to validate quality")
    options: dict[str, Any] = Field(default_factory=dict, description="Migration options")


class MigrateResponse(BaseModel):
    """Response from /migrate."""

    knowledge: str
    from_model: str
    to_model: str
    status: str
    quality_before: Optional[float] = None
    quality_after: Optional[float] = None
    num_chunks_migrated: int = 0


@router.post("/migrate", response_model=MigrateResponse)
def migrate_knowledge(req: MigrateRequest) -> MigrateResponse:
    """
    Migrate a knowledge base from one embedding model to another.

    Re-embeds all chunks with the new model, validates quality using evaluation,
    and performs a safe cutover (shadow index approach).
    Requires: pip install ragforge[migration]
    """
    try:
        from ragforge.migration import migrate_knowledge_base
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Migration module not available. Install with: pip install ragforge[migration]",
        )

    try:
        result = migrate_knowledge_base(
            knowledge=req.knowledge,
            from_model=req.from_model,
            to_model=req.to_model,
            validate=req.run_validation,
            options=req.options,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")

    return MigrateResponse(**result)
