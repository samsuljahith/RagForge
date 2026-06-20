"""Tracing API routes: list and inspect pipeline traces."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["tracing"])


class TraceSummary(BaseModel):
    """Summary of one trace (for the list view)."""

    run_id: str
    query: str
    knowledge: str
    started_at: float
    ended_at: float
    total_duration_ms: float
    status: str


class TraceStepDetail(BaseModel):
    """One step within a trace."""

    name: str
    started_at: float
    ended_at: float
    duration_ms: float
    data: dict[str, Any]


class TraceDetail(BaseModel):
    """Full trace including all steps."""

    run_id: str
    query: str
    knowledge: str
    started_at: float
    ended_at: float
    total_duration_ms: float
    status: str
    steps: list[TraceStepDetail]
    metadata: dict[str, Any]


class TracesListResponse(BaseModel):
    """Response for GET /traces."""

    traces: list[TraceSummary]
    total: int


@router.get("/traces", response_model=TracesListResponse)
def list_traces(limit: int = 50, offset: int = 0) -> TracesListResponse:
    """
    List recent pipeline traces.

    Returns summaries (no step details) sorted by most recent first.
    Use GET /traces/{run_id} for full detail of a specific trace.
    """
    from ragforge.tracing import get_store

    store = get_store()
    traces = store.list_traces(limit=limit, offset=offset)
    return TracesListResponse(
        traces=[TraceSummary(**t) for t in traces],
        total=len(traces),
    )


@router.get("/traces/{run_id}", response_model=TraceDetail)
def get_trace(run_id: str) -> TraceDetail:
    """
    Get full trace detail including all steps with timing.

    Shows the step-by-step pipeline execution: retrieval → rerank → prompt → response,
    with latency per step, retrieved chunks + scores, and prompt/response text.
    """
    from ragforge.tracing import get_store

    store = get_store()
    trace = store.get_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{run_id}' not found")
    return TraceDetail(**trace)
