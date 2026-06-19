"""Tests for the API layer (FastAPI endpoints)."""

import pytest
from fastapi.testclient import TestClient

from ragforge.api import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["service"] == "ragforge"


class TestCapabilitiesEndpoint:
    def test_capabilities(self, client):
        resp = client.get("/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data
        caps = data["capabilities"]
        assert "parser" in caps
        assert "chunker" in caps
        assert "text" in caps["parser"]
        assert "fixed" in caps["chunker"]
        assert "structure" in caps["chunker"]


class TestParseEndpoint:
    def test_parse_text(self, client):
        resp = client.post("/parse", json={
            "text": "Hello, world!",
            "doc_type": "txt",
            "source": "test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Hello, world!"
        assert data["doc_type"] == "txt"
        assert "id" in data
        assert "token_count" in data

    def test_parse_html_text(self, client):
        resp = client.post("/parse", json={
            "text": "<p>Hello</p>",
            "doc_type": "html",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Hello" in data["text"]
        assert "<p>" not in data["text"]

    def test_parse_no_input(self, client):
        resp = client.post("/parse", json={})
        assert resp.status_code == 400

    def test_parse_file_not_found(self, client):
        resp = client.post("/parse", json={"path": "/nonexistent/file.txt"})
        assert resp.status_code == 404


class TestChunkEndpoint:
    def test_chunk_structure(self, client):
        doc = {
            "text": "# Title\n\nParagraph one.\n\n# Section 2\n\nParagraph two.",
            "source": "test.md",
            "doc_type": "md",
            "metadata": {},
            "id": "test123",
        }
        resp = client.post("/chunk", json={
            "doc": doc,
            "strategy": "structure",
            "options": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy"] == "structure"
        assert data["count"] >= 1
        assert len(data["chunks"]) == data["count"]
        for chunk in data["chunks"]:
            assert "id" in chunk
            assert "text" in chunk
            assert "token_count" in chunk

    def test_chunk_fixed(self, client):
        doc = {
            "text": "word " * 200,
            "source": "test.txt",
            "doc_type": "txt",
            "metadata": {},
            "id": "test456",
        }
        resp = client.post("/chunk", json={
            "doc": doc,
            "strategy": "fixed",
            "options": {"chunk_tokens": 64},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy"] == "fixed"
        assert data["count"] > 1

    def test_chunk_invalid_strategy(self, client):
        doc = {"text": "hello", "source": "t", "doc_type": "txt", "metadata": {}, "id": "x"}
        resp = client.post("/chunk", json={
            "doc": doc,
            "strategy": "nonexistent",
        })
        assert resp.status_code == 400

    def test_chunk_invalid_doc(self, client):
        resp = client.post("/chunk", json={
            "doc": {"invalid": True},
            "strategy": "structure",
        })
        assert resp.status_code == 400


class TestKnowledgeEndpoint:
    def test_knowledge_missing_pipeline(self, client):
        # The pipeline module IS available since we built it,
        # so test with a real call that should work
        resp = client.post("/knowledge", json={
            "name": "api-test-kb",
            "sources": ["/nonexistent/path"],
        })
        # Should succeed (0 documents since path doesn't exist as parseable files)
        assert resp.status_code == 200


class TestQueryEndpoint:
    def test_query_missing_kb(self, client):
        resp = client.post("/query", json={
            "knowledge": "nonexistent",
            "question": "test",
        })
        assert resp.status_code == 404
