"""POST /query — retrieve chunks from a knowledge base."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["pipeline"])


class QueryRequest(BaseModel):
    """Request to query a knowledge base."""

    knowledge: str = Field(..., description="Name of the knowledge base to query")
    question: str = Field(..., description="The question to answer")
    top_k: int = Field(5, description="Number of chunks to retrieve", ge=1, le=100)
    rerank: bool = Field(True, description="Whether to apply reranking")


class RetrievedChunk(BaseModel):
    """A chunk retrieved by the query."""

    id: str
    text: str
    doc_id: str
    index: int
    metadata: dict
    score: float


class QueryResponse(BaseModel):
    """Response from /query."""

    question: str
    knowledge: str
    chunks: list[RetrievedChunk]
    answer: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def query_knowledge(req: QueryRequest) -> QueryResponse:
    """
    Query a knowledge base and retrieve the most relevant chunks.

    Returns top-k chunks ranked by relevance (hybrid dense + BM25 search
    with optional reranking). Optionally generates an answer.
    Requires the pipeline module: pip install ragforge[pipeline]
    """
    try:
        from ragforge.pipeline import query_knowledge_base
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Pipeline module not available. Install with: pip install ragforge[pipeline]",
        )

    try:
        result = query_knowledge_base(
            knowledge=req.knowledge,
            question=req.question,
            top_k=req.top_k,
            rerank=req.rerank,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    return QueryResponse(**result)
