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
    run_validation: bool = Field(True, description="Gate the cutover on a golden dataset, if one is given")
    golden_path: Optional[str] = Field(None, description="Path to a golden dataset (JSON/CSV) to gate against")
    hot_set_first: bool = Field(True, description="Re-embed+gate only the golden set's referenced chunks first")
    force: bool = Field(False, description="Swap even if the quality gate rejects the new model")
    top_k: int = Field(5, description="top_k used for gate retrieval metrics")
    options: dict[str, Any] = Field(default_factory=dict, description="Migration options")


class MigrateResponse(BaseModel):
    """Response from /migrate."""

    knowledge: str
    from_model: str
    to_model: str
    status: str
    gate: Optional[dict[str, Any]] = None
    num_chunks_migrated: int = 0


@router.post("/migrate", response_model=MigrateResponse)
def migrate_knowledge(req: MigrateRequest) -> MigrateResponse:
    """
    Migrate a knowledge base from one embedding model to another.

    With `golden_path` set, re-embeds the hot set first and gates the cutover
    on real recall@k/MRR/hit_rate (old model vs new model) before re-embedding
    the rest of the corpus. Without it, migrates unguarded.
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
            golden_path=req.golden_path,
            hot_set_first=req.hot_set_first,
            force=req.force,
            top_k=req.top_k,
            options=req.options,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")

    return MigrateResponse(**result)
