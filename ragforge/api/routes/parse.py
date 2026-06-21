"""POST /parse — parse a file or raw text into a Document."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ragforge.parsing import parse_file
from ragforge.core.models import Document

router = APIRouter(tags=["parsing"])


class ParseRequest(BaseModel):
    """Request body for /parse. Provide either `path` (server-side file) or `text`."""

    path: Optional[str] = Field(None, description="Path to a file on the server to parse")
    text: Optional[str] = Field(None, description="Raw text content to wrap as a Document")
    doc_type: str = Field("txt", description="Document type hint when using raw text (txt, md, html)")
    source: str = Field("api-input", description="Source label when using raw text")
    parser: Optional[str] = Field(
        None,
        description="Parser backend to use: 'text', 'html', 'pdf', 'docling'. Default: auto-detect by extension.",
    )


class DocumentResponse(BaseModel):
    """A parsed Document returned by the API."""

    id: str
    text: str
    source: str
    doc_type: str
    metadata: dict
    token_count: int


@router.post("/parse", response_model=DocumentResponse)
def parse_document(req: ParseRequest) -> DocumentResponse:
    """
    Parse a file or text into a Document.

    Provide `path` to parse a server-side file (auto-detects format by extension),
    or `text` to wrap raw content as a Document directly.

    Optionally specify `parser` to choose a backend: 'text', 'html', 'pdf', 'docling'.
    Default auto-detects by file extension.
    """
    if not req.path and not req.text:
        raise HTTPException(status_code=400, detail="Provide either 'path' or 'text'")

    if req.path:
        p = Path(req.path)
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {req.path}")
        try:
            if req.parser:
                from ragforge.core.registry import get

                parser_cls = get("parser", req.parser)
                doc = parser_cls().parse(req.path)
            else:
                doc = parse_file(req.path)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ImportError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        # If text is provided with a doc_type hint, optionally use the right parser
        if req.doc_type == "html":
            # Write to temp file so the HTML parser can strip tags
            with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
                f.write(req.text)
                tmp_path = f.name
            try:
                doc = parse_file(tmp_path)
                doc.source = req.source
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            doc = Document(
                text=req.text,
                source=req.source,
                doc_type=req.doc_type,
            )

    # Strip non-serializable internal objects from metadata
    response_metadata = {k: v for k, v in doc.metadata.items() if not k.startswith("_")}

    return DocumentResponse(
        id=doc.id,
        text=doc.text,
        source=doc.source,
        doc_type=doc.doc_type,
        metadata=response_metadata,
        token_count=doc.token_count,
    )
