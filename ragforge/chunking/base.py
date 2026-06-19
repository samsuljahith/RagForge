"""
Chunking module: split a Document into Chunks for embedding and retrieval.

Reddit's second-loudest lesson: chunking matters more than model choice. Fixed-size
splitting breaks tables and code and buries answers ("embedding dilution"). So
RAGForge ships a structure-aware chunker alongside the simple fixed one.

Every chunker follows the same contract (the Chunker base class): take a Document,
return a list of Chunks. That uniformity lets you swap chunking strategies with one
word and measure which works best (once the evaluation module lands).
"""

from __future__ import annotations

import abc

from ragforge.core.models import Chunk, Document


class Chunker(abc.ABC):
    """Base class for all chunkers. Turns one Document into a list of Chunks."""

    @abc.abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Split `document` into Chunks. Subclasses implement the strategy."""
        raise NotImplementedError

    def _make_chunk(self, text: str, document: Document, index: int, **meta) -> Chunk:
        """Helper so subclasses build Chunks consistently (carrying doc id + strategy)."""
        metadata = {"strategy": type(self).__name__, **meta}
        return Chunk(text=text.strip(), doc_id=document.id, index=index, metadata=metadata)
