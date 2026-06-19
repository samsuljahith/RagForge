"""
Core data models for RAGForge.

These are the shared "language" that every module speaks. A parser produces a
Document. A chunker turns a Document into Chunks. The pipeline embeds Chunks.
The evaluator scores results. Because every module reads and writes these same
objects, the pieces fit together cleanly instead of each inventing its own format.

Keep this file small and stable. Everything depends on it, so changes here ripple
everywhere. Add fields carefully.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def _new_id() -> str:
    """Short unique id, e.g. 'a1b2c3d4'. Readable in logs, unique enough in practice."""
    return uuid.uuid4().hex[:8]


def estimate_tokens(text: str) -> int:
    """
    Rough token count without needing a tokenizer dependency.
    ~4 characters per token is the common rule of thumb for English text.
    Good enough for budgeting chunk sizes; swap for a real tokenizer later if needed.
    """
    return max(1, len(text) // 4)


@dataclass
class Document:
    """
    One source document after parsing: raw text plus where it came from.

    text:     the extracted plain text content
    source:   path or URL the document came from
    doc_type: 'txt', 'md', 'pdf', 'html', etc. (lets chunkers behave differently)
    metadata: anything extra (title, author, page count, ingest time...)
    id:       stable identifier used to link chunks back to their document
    """

    text: str
    source: str = "unknown"
    doc_type: str = "txt"
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=_new_id)

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.text)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-friendly)."""
        d = asdict(self)
        d["token_count"] = self.token_count
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Reconstruct a Document from a dict (ignores extra keys like token_count)."""
        fields = {"text", "source", "doc_type", "metadata", "id"}
        return cls(**{k: v for k, v in data.items() if k in fields})

    def __repr__(self) -> str:
        preview = self.text[:50].replace("\n", " ")
        return f"Document(id={self.id!r}, source={self.source!r}, ~{self.token_count} tok, '{preview}...')"


@dataclass
class Chunk:
    """
    A piece of a Document, ready to be embedded and retrieved.

    text:     the chunk's text
    doc_id:   id of the Document this came from (so we can trace answers back)
    index:    position of this chunk within its document (0, 1, 2, ...)
    metadata: section title, page number, char offsets, chunking strategy used...
    id:       stable identifier for this chunk
    """

    text: str
    doc_id: str
    index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=_new_id)

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.text)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-friendly)."""
        d = asdict(self)
        d["token_count"] = self.token_count
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        """Reconstruct a Chunk from a dict (ignores extra keys like token_count)."""
        fields = {"text", "doc_id", "index", "metadata", "id"}
        return cls(**{k: v for k, v in data.items() if k in fields})

    def __repr__(self) -> str:
        preview = self.text[:40].replace("\n", " ")
        section = self.metadata.get("section")
        sec = f", section={section!r}" if section else ""
        return f"Chunk(#{self.index}, ~{self.token_count} tok{sec}, '{preview}...')"
