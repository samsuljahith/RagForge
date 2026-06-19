"""Tests for core models and registry."""

import pytest

from ragforge.core.models import Document, Chunk, estimate_tokens, _new_id
from ragforge.core.registry import register, get, available, all_kinds, registered_info


class TestEstimateTokens:
    def test_basic(self):
        assert estimate_tokens("hello world") == max(1, len("hello world") // 4)

    def test_empty(self):
        assert estimate_tokens("") == 1

    def test_long_text(self):
        text = "a" * 1000
        assert estimate_tokens(text) == 250


class TestDocument:
    def test_create(self):
        doc = Document(text="hello", source="test.txt")
        assert doc.text == "hello"
        assert doc.source == "test.txt"
        assert doc.doc_type == "txt"
        assert doc.id  # auto-generated

    def test_token_count(self):
        doc = Document(text="a" * 100)
        assert doc.token_count == 25

    def test_to_dict(self):
        doc = Document(text="test", source="s.md", doc_type="md", id="abc123")
        d = doc.to_dict()
        assert d["text"] == "test"
        assert d["source"] == "s.md"
        assert d["doc_type"] == "md"
        assert d["id"] == "abc123"
        assert d["token_count"] == doc.token_count

    def test_from_dict(self):
        d = {"text": "hello", "source": "f.txt", "doc_type": "txt", "metadata": {}, "id": "x1"}
        doc = Document.from_dict(d)
        assert doc.text == "hello"
        assert doc.id == "x1"

    def test_from_dict_ignores_extras(self):
        d = {"text": "hi", "source": "x", "doc_type": "txt", "metadata": {}, "id": "y", "token_count": 999}
        doc = Document.from_dict(d)
        assert doc.text == "hi"


class TestChunk:
    def test_create(self):
        c = Chunk(text="chunk text", doc_id="doc1", index=0)
        assert c.text == "chunk text"
        assert c.doc_id == "doc1"
        assert c.index == 0
        assert c.id

    def test_to_dict(self):
        c = Chunk(text="test", doc_id="d1", index=2, id="c1")
        d = c.to_dict()
        assert d["text"] == "test"
        assert d["doc_id"] == "d1"
        assert d["index"] == 2

    def test_from_dict(self):
        d = {"text": "x", "doc_id": "d1", "index": 1, "metadata": {}, "id": "c2"}
        c = Chunk.from_dict(d)
        assert c.text == "x"
        assert c.doc_id == "d1"


class TestRegistry:
    def test_available_chunker(self):
        # chunkers are registered via import
        names = available("chunker")
        assert "fixed" in names
        assert "structure" in names

    def test_available_parser(self):
        names = available("parser")
        assert "text" in names
        assert "html" in names
        assert "pdf" in names

    def test_get_existing(self):
        cls = get("chunker", "fixed")
        assert cls is not None

    def test_get_missing(self):
        with pytest.raises(KeyError):
            get("chunker", "nonexistent")

    def test_all_kinds(self):
        kinds = all_kinds()
        assert "parser" in kinds
        assert "chunker" in kinds

    def test_registered_info(self):
        info = registered_info()
        assert "parser" in info
        assert "chunker" in info
        assert isinstance(info["parser"], list)
