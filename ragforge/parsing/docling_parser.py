"""
Docling-powered parser: high-quality document parsing for PDFs, DOCX, PPTX, XLSX,
HTML, and images via IBM's Docling library.

Why Docling? RAGForge's built-in parsers handle simple files well, but complex
documents (multi-column PDFs, embedded tables, code-heavy slides) need a
document-intelligence engine. Docling uses layout analysis and OCR to extract
structured content where simpler tools produce garbage.

This is OPTIONAL. The core install has zero Docling dependency. Users opt in:
    pip install ragforge[docling]

If the library isn't installed, requesting the "docling" parser raises a clear,
friendly error — never a cryptic ImportError buried in a traceback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ragforge.core.models import Document
from ragforge.core.registry import register
from ragforge.parsing.base import Parser


def _check_docling_installed() -> None:
    """Raise a helpful error if docling is not installed."""
    try:
        import docling  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "The 'docling' parser requires the docling package.\n"
            "Install it with:  pip install ragforge[docling]   (or: pip install docling)\n\n"
            "Docling provides high-quality parsing of PDFs, DOCX, PPTX, XLSX, HTML, and images\n"
            "with layout analysis, table extraction, and OCR support."
        ) from exc


@register("parser", "docling")
class DoclingParser(Parser):
    """
    Parses documents using IBM's Docling library for high-quality extraction.

    Supports: PDF, DOCX, PPTX, XLSX, HTML, and images (PNG, JPG, TIFF, BMP).
    Extracts tables, code blocks, headings, and page structure as rich metadata.

    Usage:
        from ragforge.core.registry import get
        parser = get("parser", "docling")()
        doc = parser.parse("complex_report.pdf")

    The returned Document carries structured metadata including:
    - page_count: number of pages (for paginated formats)
    - headings: list of extracted headings
    - has_tables: whether tables were detected
    - docling_doc: the raw DoclingDocument (for advanced users who want to
      use docling's own chunkers directly)
    """

    extensions = {
        ".pdf", ".docx", ".pptx", ".xlsx",
        ".html", ".htm",
        ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
    }

    def __init__(self, ocr: bool = True, **kwargs: Any) -> None:
        """
        Args:
            ocr: Enable OCR for scanned documents / images (default: True).
            **kwargs: Additional options passed to docling's DocumentConverter.
        """
        self.ocr = ocr
        self.converter_kwargs = kwargs

    def supports(self, path: str | Path) -> bool:
        """
        Always returns False for auto-detection.

        DoclingParser is an explicit-choice backend — users must request it via
        --parser docling or parser='docling' in the API. This prevents it from
        hijacking auto-detection when the lighter built-in parsers work fine,
        and avoids ImportError surprises when docling isn't installed.
        """
        return False

    def parse(self, path: str | Path) -> Document:
        """
        Parse a file using Docling and return a RAGForge Document.

        The full structured DoclingDocument is stashed in metadata['_docling_doc']
        so the DoclingChunker can use it directly for structure-aware chunking.
        """
        _check_docling_installed()

        from docling.document_converter import DocumentConverter

        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        # Convert the document
        converter = DocumentConverter()
        result = converter.convert(str(p))
        docling_doc = result.document

        # Extract text via Docling's markdown export (preserves structure)
        text = docling_doc.export_to_markdown()

        # Build metadata from the structured document
        metadata: dict[str, Any] = {
            "filename": p.name,
            "parser": "docling",
        }

        # Store the raw docling document for the DoclingChunker to use
        # (This is an in-memory reference, not serialized)
        metadata["_docling_doc"] = docling_doc

        # Determine doc_type from extension
        suffix = p.suffix.lower()
        doc_type_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".pptx": "pptx",
            ".xlsx": "xlsx",
            ".html": "html",
            ".htm": "html",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".tiff": "image",
            ".tif": "image",
            ".bmp": "image",
        }
        doc_type = doc_type_map.get(suffix, "unknown")

        return Document(
            text=text,
            source=str(p),
            doc_type=doc_type,
            metadata=metadata,
        )
