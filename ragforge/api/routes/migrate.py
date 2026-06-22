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


# ─── Decision Gate Endpoint ────────────────────────────────────────────────────

class GateRequest(BaseModel):
    """Request to run the migration decision gate (compare old vs new model)."""

    knowledge: str = Field(..., description="Knowledge base name")
    golden_path: str = Field(..., description="Path to golden dataset (JSON)")
    old_model: str = Field(..., description="Current embedding model name")
    new_model: str = Field(..., description="Candidate embedding model name")
    primary_metric: str = Field("recall_at_k", description="Metric for GO/NO_GO decision")
    threshold_margin: float = Field(0.0, description="Allowed regression margin (0.0 = must not regress)")
    top_k: int = Field(5, description="top_k for retrieval metrics")
    hot_set_only: bool = Field(True, description="Only evaluate hot set (chunks referenced by golden queries)")


class GateResponse(BaseModel):
    """Response from the decision gate."""

    recommendation: str
    old_metrics: dict[str, float]
    new_metrics: dict[str, float]
    deltas: dict[str, float]
    primary_metric: str
    threshold_margin: float
    reason: str
    hot_set_size: int
    total_chunks: int


@router.post("/migrate/gate", response_model=GateResponse)
def run_gate(req: GateRequest) -> GateResponse:
    """
    Run the migration decision gate: compare old vs new embedding model
    on a golden dataset. Returns GO or NO_GO with metrics and reason.

    Does NOT perform any migration — just evaluates whether the new model
    is better on your queries.
    """
    try:
        from ragforge.migration.gate import run_decision_gate
        from ragforge.migration.migrator import _get_embedder
        from ragforge.pipeline.knowledge import KnowledgeBase
        from ragforge.evaluation.golden import GoldenDataset
    except ImportError:
        raise HTTPException(status_code=501, detail="Migration module not available.")

    try:
        kb = KnowledgeBase.load(req.knowledge)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    golden = GoldenDataset.load(req.golden_path)
    old_embedder = _get_embedder(req.old_model)
    new_embedder = _get_embedder(req.new_model)

    chunks = kb.store.chunks if hasattr(kb, 'store') else []

    decision = run_decision_gate(
        chunks=chunks,
        old_embedder=old_embedder,
        new_embedder=new_embedder,
        golden=golden,
        primary_metric=req.primary_metric,
        threshold_margin=req.threshold_margin,
        top_k=req.top_k,
        hot_set_only=req.hot_set_only,
    )

    return GateResponse(**decision.to_dict())


# ─── Smoke Test Endpoint ───────────────────────────────────────────────────────

class SmokeTestRequest(BaseModel):
    """Request to run post-migration smoke test."""

    knowledge: str = Field(..., description="Knowledge base name")
    golden_path: str = Field(..., description="Path to golden dataset (JSON)")
    top_k: int = Field(5, description="top_k for retrieval")


class SmokeTestResponse(BaseModel):
    """Response from smoke test."""

    passed: bool
    checks: list[dict[str, Any]]
    summary: str


@router.post("/migrate/smoke-test", response_model=SmokeTestResponse)
def run_smoke_test(req: SmokeTestRequest) -> SmokeTestResponse:
    """
    Post-migration smoke test: verify the migrated KB actually works.
    Runs golden queries and checks that results are non-empty and hit
    expected chunks.
    """
    try:
        from ragforge.migration.gate import smoke_test
        from ragforge.evaluation.golden import GoldenDataset
    except ImportError:
        raise HTTPException(status_code=501, detail="Migration module not available.")

    golden = GoldenDataset.load(req.golden_path)

    result = smoke_test(
        knowledge=req.knowledge,
        golden=golden,
        top_k=req.top_k,
    )

    return SmokeTestResponse(**result.to_dict())
