"""Tests for the chunking module."""

import pytest

from ragforge.core.models import Document
from ragforge.chunking import chunk_document
from ragforge.chunking.text_chunker import FixedChunker, StructureChunker


class TestFixedChunker:
    def test_basic(self):
        doc = Document(text="word " * 200, source="test.txt")
        chunks = chunk_document(doc, strategy="fixed", chunk_tokens=64)
        assert len(chunks) > 1
        for c in chunks:
            assert c.doc_id == doc.id
            assert c.text

    def test_overlap(self):
        doc = Document(text="word " * 100, source="test.txt")
        chunks = chunk_document(doc, strategy="fixed", chunk_tokens=32, overlap_tokens=8)
        # With overlap, we should get more chunks than without
        chunks_no_overlap = chunk_document(doc, strategy="fixed", chunk_tokens=32, overlap_tokens=0)
        assert len(chunks) >= len(chunks_no_overlap)

    def test_empty_document(self):
        doc = Document(text="", source="empty.txt")
        chunks = chunk_document(doc, strategy="fixed")
        assert chunks == []

    def test_small_document(self):
        doc = Document(text="Just a few words.", source="tiny.txt")
        chunks = chunk_document(doc, strategy="fixed", chunk_tokens=256)
        assert len(chunks) == 1

    def test_invalid_overlap(self):
        with pytest.raises(ValueError):
            FixedChunker(chunk_tokens=100, overlap_tokens=100)


class TestStructureChunker:
    def test_respects_headers(self):
        text = "# Section A\n\nContent A.\n\n# Section B\n\nContent B."
        doc = Document(text=text, source="test.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure")
        # Should have at least 2 chunks (one per section)
        assert len(chunks) >= 2
        sections = [c.metadata.get("section") for c in chunks]
        assert "Section A" in sections
        assert "Section B" in sections

    def test_keeps_code_blocks_intact(self):
        text = "# Code\n\n```python\ndef foo():\n    return 42\n```\n\n# End\n\nDone."
        doc = Document(text=text, source="test.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure")
        # Find the chunk with code
        code_chunks = [c for c in chunks if "def foo" in c.text]
        assert len(code_chunks) == 1
        # The whole code block should be together
        assert "return 42" in code_chunks[0].text

    def test_keeps_tables_intact(self):
        text = (
            "# Data\n\n"
            "| Name | Value |\n"
            "|------|-------|\n"
            "| A    | 1     |\n"
            "| B    | 2     |\n\n"
            "# End\n\nDone."
        )
        doc = Document(text=text, source="test.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure")
        table_chunks = [c for c in chunks if "| Name" in c.text]
        assert len(table_chunks) == 1
        assert "| B    | 2" in table_chunks[0].text

    def test_tags_oversized(self):
        # A very large code block that exceeds max_tokens
        code = "x = 1\n" * 500
        text = f"# Code\n\n```python\n{code}```"
        doc = Document(text=text, source="test.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure", max_tokens=64)
        oversized = [c for c in chunks if c.metadata.get("oversized")]
        assert len(oversized) >= 1

    def test_empty_document(self):
        doc = Document(text="", source="empty.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure")
        assert chunks == []

    def test_section_metadata(self):
        text = "# Intro\n\nHello world."
        doc = Document(text=text, source="test.md", doc_type="md")
        chunks = chunk_document(doc, strategy="structure")
        assert chunks[0].metadata.get("section") == "Intro"
