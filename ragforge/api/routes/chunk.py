"""POST /chunk — chunk a Document into pieces."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ragforge.core.models import Document
from ragforge.chunking import chunk_document

router = APIRouter(tags=["chunking"])


class ChunkRequest(BaseModel):
    """Request body for /chunk."""

    doc: dict = Field(..., description="A Document dict (from /parse response or constructed manually)")
    strategy: str = Field("structure", description="Chunking strategy: 'fixed' or 'structure'")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy options, e.g. {'max_tokens': 256} for structure, {'chunk_tokens': 256, 'overlap_tokens': 32} for fixed",
    )


class ChunkResponse(BaseModel):
    """One chunk in the response."""

    id: str
    text: str
    doc_id: str
    index: int
    metadata: dict
    token_count: int


class ChunkListResponse(BaseModel):
    """Response from /chunk."""

    chunks: list[ChunkResponse]
    count: int
    strategy: str


@router.post("/chunk", response_model=ChunkListResponse)
def chunk_doc(req: ChunkRequest) -> ChunkListResponse:
    """
    Split a Document into Chunks using the specified strategy.

    Pass the Document dict (as returned by /parse) and choose a strategy:
    - 'structure': respects markdown headers, keeps code/tables intact
    - 'fixed': sliding window with configurable size and overlap
    """
    try:
        doc = Document.from_dict(req.doc)
    except (TypeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid document: {e}")

    try:
        chunks = chunk_document(doc, strategy=req.strategy, **req.options)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid options: {e}")

    return ChunkListResponse(
        chunks=[
            ChunkResponse(
                id=c.id,
                text=c.text,
                doc_id=c.doc_id,
                index=c.index,
                metadata=c.metadata,
                token_count=c.token_count,
            )
            for c in chunks
        ],
        count=len(chunks),
        strategy=req.strategy,
    )
