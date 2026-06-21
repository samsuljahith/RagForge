"""
Docling-powered chunker: structure + token-aware chunking via IBM's Docling library.

Why use this over RAGForge's built-in StructureChunker?
- Docling's HybridChunker understands the actual document layout (tables, headers,
  list items, code blocks) from the DoclingDocument, not from guessing via markdown.
- It produces chunks that respect page boundaries, preserve table integrity, and
  carry rich metadata (page numbers, section hierarchy, content type).
- Best results when paired with DoclingParser, which gives it the full structured doc.

This is OPTIONAL. Install with:  pip install ragforge[docling]

If given a Document that wasn't parsed by DoclingParser (no _docling_doc in metadata),
it falls back to RAGForge's built-in structure chunker with a warning — rather than
crashing or producing garbage.
"""

from __future__ import annotations

import warnings
from typing import Any

from ragforge.core.models import Chunk, Document
from ragforge.core.registry import register
from ragforge.chunking.base import Chunker


def _check_docling_installed() -> None:
    """Raise a helpful error if docling is not installed."""
    try:
        import docling  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "The 'docling' chunker requires the docling package.\n"
            "Install it with:  pip install ragforge[docling]   (or: pip install docling)\n\n"
            "Docling provides structure-aware chunking that preserves tables, code blocks,\n"
            "and page boundaries with rich metadata."
        ) from exc


@register("chunker", "docling")
class DoclingChunker(Chunker):
    """
    Structure + token-aware chunker powered by Docling's HybridChunker.

    Best used with documents parsed by DoclingParser, which stores the structured
    DoclingDocument in metadata['_docling_doc']. When that's available, this chunker
    uses Docling's full layout understanding.

    If the document lacks a _docling_doc (e.g., it was parsed by the default parser),
    falls back to RAGForge's built-in structure chunker with a warning.

    Args:
        max_tokens: Maximum tokens per chunk (default: 512).
        merge_peers: Whether to merge small adjacent chunks from the same section
                     (default: True). Reduces chunk count without losing context.

    Usage:
        from ragforge.core.registry import get
        chunker = get("chunker", "docling")(max_tokens=384)
        chunks = chunker.chunk(doc)
    """

    def __init__(self, max_tokens: int = 512, merge_peers: bool = True) -> None:
        self.max_tokens = max_tokens
        self.merge_peers = merge_peers

    def chunk(self, document: Document) -> list[Chunk]:
        """
        Chunk a Document using Docling's HybridChunker.

        If the document has a _docling_doc in metadata (from DoclingParser),
        uses Docling's native chunking. Otherwise falls back to RAGForge's
        structure chunker.
        """
        docling_doc = document.metadata.get("_docling_doc")

        if docling_doc is None:
            # No structured doc available — fall back gracefully
            warnings.warn(
                "DoclingChunker works best with documents parsed by DoclingParser "
                "(which provides the structured DoclingDocument). This document was "
                "parsed by a different parser, so falling back to RAGForge's built-in "
                "structure chunker. For best results, use --parser docling.",
                UserWarning,
                stacklevel=2,
            )
            from ragforge.chunking.text_chunker import StructureChunker

            fallback = StructureChunker(max_tokens=self.max_tokens)
            return fallback.chunk(document)

        # We have the structured docling document — use HybridChunker
        _check_docling_installed()

        from docling_core.transforms.chunker import HierarchicalChunker

        # Use HierarchicalChunker which is the recommended chunker for
        # structured documents. It respects the document hierarchy.
        chunker = HierarchicalChunker(
            max_tokens=self.max_tokens,
            merge_peers=self.merge_peers,
        )

        docling_chunks = list(chunker.chunk(docling_doc))

        # Convert docling chunks to RAGForge Chunk objects
        chunks: list[Chunk] = []
        for i, dc in enumerate(docling_chunks):
            # Extract metadata from the docling chunk
            meta: dict[str, Any] = {
                "strategy": "DoclingChunker",
                "parser": "docling",
            }

            # Get text from the chunk
            chunk_text = dc.text if hasattr(dc, "text") else str(dc)

            # Extract heading/section info if available
            if hasattr(dc, "meta") and dc.meta:
                if hasattr(dc.meta, "headings") and dc.meta.headings:
                    meta["section"] = " > ".join(dc.meta.headings)
                if hasattr(dc.meta, "page") and dc.meta.page is not None:
                    meta["page"] = dc.meta.page

            chunks.append(
                Chunk(
                    text=chunk_text.strip(),
                    doc_id=document.id,
                    index=i,
                    metadata=meta,
                )
            )

        return chunks
