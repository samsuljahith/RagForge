"""POST /query — retrieve chunks (and optionally generate an answer) from a knowledge base."""

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
    generate: bool = Field(
        False,
        description="Generate a grounded answer using an LLM (requires an llm provider configured)",
    )
    llm: Optional[str] = Field(
        None,
        description="LLM provider to use for answer generation: 'openai', 'anthropic', or 'ollama'",
    )
    model: Optional[str] = Field(
        None,
        description="Override the default model for the chosen LLM provider",
    )


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
    llm: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def query_knowledge(req: QueryRequest) -> QueryResponse:
    """
    Query a knowledge base and retrieve the most relevant chunks.

    Supports three retrieval modes:
    - **dense**: pure vector similarity search
    - **bm25**: pure keyword matching (catches exact product codes, IDs, etc.)
    - **hybrid** (default): both fused via Reciprocal Rank Fusion — best overall quality

    Optionally generates a grounded answer (set `generate: true` and provide `llm`).
    The LLM is instructed to answer ONLY from retrieved context and cite sources.
    If the answer isn't in the context, it will say so rather than inventing.
    """
    from ragforge.pipeline import query_knowledge_base

    # Build llm_opts if a model override was given
    llm_opts = {}
    if req.model:
        llm_opts["model"] = req.model

    try:
        result = query_knowledge_base(
            knowledge=req.knowledge,
            question=req.question,
            top_k=req.top_k,
            mode=req.mode,
            rerank=req.rerank,
            generate=req.generate,
            llm=req.llm,
            llm_opts=llm_opts if llm_opts else None,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except (ValueError, ConnectionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    return QueryResponse(**result)
