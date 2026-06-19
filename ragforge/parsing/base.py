"""
Parsing module: turn a source file into a clean Document.

Reddit's loudest RAG complaint was "garbage in, garbage out" — messy PDFs and
documents producing broken text that wrecks everything downstream. So parsing is
treated as a first-class concern here, not an afterthought.

Every parser follows the same simple contract (the Parser base class), so the rest
of RAGForge doesn't care whether the input was a .txt, .md, .html, or .pdf — it just
gets back a Document.
"""

from __future__ import annotations

import abc
from pathlib import Path

from ragforge.core.models import Document


class Parser(abc.ABC):
    """Base class for all parsers. A parser reads one file and returns one Document."""

    #: file extensions this parser handles, lowercase, with the dot (e.g. {".txt"})
    extensions: set[str] = set()

    def supports(self, path: str | Path) -> bool:
        """True if this parser can handle the given file (based on extension)."""
        return Path(path).suffix.lower() in self.extensions

    @abc.abstractmethod
    def parse(self, path: str | Path) -> Document:
        """Read the file at `path` and return a Document. Subclasses implement this."""
        raise NotImplementedError
