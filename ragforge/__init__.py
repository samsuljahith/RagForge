"""
RAGForge — one workshop for building, evaluating, and optimizing RAG systems.

Vision: instead of juggling separate tools for parsing, chunking, retrieval,
evaluation, quantization, and migration, do it all in one place — with clean,
independent modules under a shared core so it never becomes a tangled mess.

Currently working:
    - core      : shared data models (Document, Chunk) + plugin registry
    - parsing   : txt / md / html / pdf  ->  Document
    - chunking  : fixed + structure-aware  ->  Chunks

Coming next (in order): pipeline -> evaluation -> quantization -> migration.

Quick start:
    import ragforge as rf
    doc = rf.parse_file("notes.md")
    chunks = rf.chunk_document(doc, strategy="structure")
"""

from ragforge.core import Chunk, Document, available
from ragforge.parsing import parse_file
from ragforge.chunking import chunk_document

__version__ = "0.1.0"

__all__ = ["Document", "Chunk", "parse_file", "chunk_document", "available", "__version__"]
