"""
Tests for the Docling integration (parser + chunker).

These tests verify:
1. DoclingParser and DoclingChunker register correctly in the registry.
2. Requesting docling without the package installed gives a friendly error.
3. (Guarded) If docling IS installed, a real file can be parsed and chunked.

The guarded tests skip gracefully in CI or any environment where docling
isn't installed — they never make the whole suite depend on it.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from ragforge.core.models import Chunk, Document
from ragforge.core.registry import available, get


# ─── Registration Tests ────────────────────────────────────────────────────────


class TestDoclingRegistration:
    """Verify the docling parser and chunker register in the global registry."""

    def test_docling_parser_registered(self):
        """DoclingParser should appear in the parser registry."""
        parsers = available("parser")
        assert "docling" in parsers, f"'docling' not in parsers: {parsers}"

    def test_docling_chunker_registered(self):
        """DoclingChunker should appear in the chunker registry."""
        chunkers = available("chunker")
        assert "docling" in chunkers, f"'docling' not in chunkers: {chunkers}"

    def test_docling_parser_retrievable(self):
        """get('parser', 'docling') should return DoclingParser class."""
        cls = get("parser", "docling")
        assert cls.__name__ == "DoclingParser"

    def test_docling_chunker_retrievable(self):
        """get('chunker', 'docling') should return DoclingChunker class."""
        cls = get("chunker", "docling")
        assert cls.__name__ == "DoclingChunker"

    def test_docling_parser_extensions(self):
        """DoclingParser should list the expected file types in its extensions set."""
        cls = get("parser", "docling")
        expected = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".png", ".jpg"}
        assert expected.issubset(cls.extensions)

    def test_docling_parser_not_autodetected(self):
        """DoclingParser.supports() returns False — it's explicit-choice only."""
        cls = get("parser", "docling")
        parser = cls()
        assert parser.supports("test.pdf") is False
        assert parser.supports("test.html") is False

    def test_capabilities_includes_docling(self):
        """registered_info() should include docling in both parser and chunker."""
        from ragforge.core.registry import registered_info

        info = registered_info()
        assert "docling" in info.get("parser", [])
        assert "docling" in info.get("chunker", [])


# ─── Friendly Error Tests (docling NOT installed) ──────────────────────────────


class TestDoclingFriendlyErrors:
    """Verify clear error messages when docling package is missing."""

    def test_parser_import_error_message(self):
        """DoclingParser.parse() should give a helpful ImportError when docling is missing."""
        with patch.dict("sys.modules", {"docling": None}):
            parser_cls = get("parser", "docling")
            parser = parser_cls()
            with pytest.raises(ImportError, match=r"pip install ragforge\[docling\]"):
                parser.parse("/tmp/fake.pdf")

    def test_chunker_import_error_message(self):
        """DoclingChunker.chunk() should give a helpful ImportError when docling is missing
        (only triggered when _docling_doc is present in metadata)."""
        with patch.dict("sys.modules", {"docling": None}):
            chunker_cls = get("chunker", "docling")
            chunker = chunker_cls()
            # Create a document that looks like it came from DoclingParser
            doc = Document(
                text="test content",
                source="test.pdf",
                doc_type="pdf",
                metadata={"_docling_doc": "fake_docling_doc_object"},
            )
            with pytest.raises(ImportError, match=r"pip install ragforge\[docling\]"):
                chunker.chunk(doc)

    def test_chunker_fallback_without_docling_doc(self):
        """DoclingChunker should fall back to StructureChunker when no _docling_doc."""
        chunker_cls = get("chunker", "docling")
        chunker = chunker_cls(max_tokens=256)
        doc = Document(
            text="# Hello\n\nThis is a paragraph.\n\n## Section 2\n\nMore text here.",
            source="test.md",
            doc_type="md",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            chunks = chunker.chunk(doc)
            # Should have issued a warning about fallback
            assert len(w) == 1
            assert "DoclingParser" in str(w[0].message)

        # Should still produce chunks via fallback
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)


# ─── Guarded Real-File Tests (only run if docling is installed) ────────────────


def _docling_available() -> bool:
    """Check if docling is actually installed."""
    try:
        import docling  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _docling_available(), reason="docling not installed")
class TestDoclingRealParsing:
    """Integration tests that actually use docling. Skipped if not installed."""

    def test_parse_simple_html(self, tmp_path: Path):
        """Parse a simple HTML file with docling."""
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body><h1>Title</h1><p>Paragraph one.</p>"
            "<table><tr><td>A</td><td>B</td></tr></table></body></html>"
        )

        parser = get("parser", "docling")()
        doc = parser.parse(html_file)

        assert isinstance(doc, Document)
        assert doc.doc_type == "html"
        assert doc.source == str(html_file.resolve())
        assert doc.metadata.get("parser") == "docling"
        assert doc.metadata.get("_docling_doc") is not None
        assert len(doc.text) > 0

    def test_parse_then_chunk_html(self, tmp_path: Path):
        """Parse + chunk an HTML file using docling for both steps."""
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body>"
            "<h1>Introduction</h1><p>First section content.</p>"
            "<h2>Details</h2><p>Some detailed information here.</p>"
            "<table><tr><th>Col A</th><th>Col B</th></tr>"
            "<tr><td>1</td><td>2</td></tr></table>"
            "</body></html>"
        )

        parser = get("parser", "docling")()
        doc = parser.parse(html_file)

        chunker = get("chunker", "docling")(max_tokens=256)
        chunks = chunker.chunk(doc)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
        assert all(c.doc_id == doc.id for c in chunks)
        # Chunks should have sequential indices
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_parse_markdown_file(self, tmp_path: Path):
        """Parse a markdown file with docling (tests extension support)."""
        md_file = tmp_path / "readme.html"
        md_file.write_text(
            "<html><body><h1>API Docs</h1>"
            "<p>This is the API documentation.</p>"
            "<pre><code>def hello(): pass</code></pre>"
            "</body></html>"
        )

        parser = get("parser", "docling")()
        doc = parser.parse(md_file)

        assert isinstance(doc, Document)
        assert len(doc.text) > 0


# ─── CLI Integration Test ──────────────────────────────────────────────────────


class TestDoclingCLI:
    """Test CLI flags related to docling."""

    def test_parse_parser_flag_exists(self):
        """The parse subcommand should accept --parser."""
        from ragforge.cli import build_parser

        parser = build_parser()
        # Should not raise
        args = parser.parse_args(["parse", "test.pdf", "--parser", "docling"])
        assert args.parser == "docling"

    def test_chunk_strategy_docling_accepted(self):
        """The chunk subcommand should accept --strategy docling."""
        from ragforge.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["chunk", "test.pdf", "--strategy", "docling"])
        assert args.strategy == "docling"

    def test_chunk_parser_flag_exists(self):
        """The chunk subcommand should accept --parser."""
        from ragforge.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["chunk", "test.pdf", "--parser", "docling", "--strategy", "docling"])
        assert args.parser == "docling"
        assert args.strategy == "docling"
