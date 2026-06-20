"""POST /query — retrieve chunks from a knowledge base."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["pipeline"])


class QueryRequest(BaseModel):
    """Request to query a knowledge base."""

    knowledge: str = Field(..., description="Name of the knowledge base to query")
    question: str = Field(..., description="The question to answer")
    top_k: int = Field(5, description="Number of chunks to retrieve", ge=1, le=100)
    mode: Literal["dense", "bm25", "hybrid"] = Field(
        "hybrid",
        description="Retrieval mode: 'dense' (vector only), 'bm25' (keyword only), or 'hybrid' (both fused via RRF)",
    )
    rerank: bool = Field(False, description="Apply cross-encoder reranking (requires sentence-transformers)")


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

    Supports three retrieval modes:
    - **dense**: pure vector similarity search
    - **bm25**: pure keyword matching (catches exact product codes, IDs, etc.)
    - **hybrid** (default): both fused via Reciprocal Rank Fusion — best overall quality

    Optionally applies cross-encoder reranking for maximum precision (requires
    sentence-transformers; degrades gracefully if not installed).
    """
    from ragforge.pipeline import query_knowledge_base

    try:
        result = query_knowledge_base(
            knowledge=req.knowledge,
            question=req.question,
            top_k=req.top_k,
            mode=req.mode,
            rerank=req.rerank,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    return QueryResponse(**result)
