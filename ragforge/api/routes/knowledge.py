"""POST /knowledge — build/index a knowledge base (requires pipeline module)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["pipeline"])


class KnowledgeRequest(BaseModel):
    """Request to build a knowledge base."""

    name: str = Field(..., description="Name for this knowledge base")
    sources: list[str] = Field(..., description="List of file paths or URLs to index")
    embedding_model: str = Field("default", description="Embedding model to use")
    chunk_strategy: str = Field("structure", description="Chunking strategy")
    chunk_options: dict[str, Any] = Field(default_factory=dict, description="Chunking options")


class KnowledgeResponse(BaseModel):
    """Result of building a knowledge base."""

    name: str
    status: str
    num_documents: int
    num_chunks: int
    embedding_model: str


@router.post("/knowledge", response_model=KnowledgeResponse)
def build_knowledge(req: KnowledgeRequest) -> KnowledgeResponse:
    """
    Build or index a knowledge base from source documents.

    Parses, chunks, embeds, and stores documents for later retrieval via /query.
    Requires the pipeline module: pip install ragforge[pipeline]
    """
    try:
        from ragforge.pipeline import build_knowledge_base
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Pipeline module not available. Install with: pip install ragforge[pipeline]",
        )

    try:
        result = build_knowledge_base(
            name=req.name,
            sources=req.sources,
            embedding_model=req.embedding_model,
            chunk_strategy=req.chunk_strategy,
            chunk_options=req.chunk_options,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge base build failed: {e}")

    return KnowledgeResponse(**result)
