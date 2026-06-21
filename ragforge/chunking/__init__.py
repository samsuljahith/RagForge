"""Chunking: split Documents into Chunks (fixed-size, structure-aware, or docling)."""

# importing registers the chunkers
from ragforge.chunking.text_chunker import (
    FixedChunker,
    StructureChunker,
    chunk_document,
)
from ragforge.chunking.docling_chunker import DoclingChunker

__all__ = ["FixedChunker", "StructureChunker", "DoclingChunker", "chunk_document"]
