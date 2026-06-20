"""
Tests for the answer generation layer.

All LLM calls are MOCKED — no real API keys or running Ollama required.
Tests cover:
  - Prompt construction (grounded prompt with sources)
  - Provider import/key error handling
  - KnowledgeBase.answer() end-to-end (mocked LLM)
  - Refusal behavior when context is insufficient
  - Source attribution in results
  - API endpoint with generate=True
  - CLI --generate flag
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ragforge.pipeline.generation import (
    LLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    get_llm,
    build_grounded_prompt,
    GROUNDED_PROMPT_TEMPLATE,
)
from ragforge.pipeline.knowledge import KnowledgeBase, query_knowledge_base


# ===========================================================================
# Prompt Construction
# ===========================================================================


class TestBuildGroundedPrompt:
    def test_includes_question(self):
        chunks = [{"text": "Refunds within 30 days.", "metadata": {}, "doc_id": "d1"}]
        prompt = build_grounded_prompt("What is the refund policy?", chunks)
        assert "What is the refund policy?" in prompt

    def test_includes_chunk_text(self):
        chunks = [
            {"text": "Shipping takes 5 days.", "metadata": {"section": "Shipping"}, "doc_id": "d1"},
            {"text": "Returns accepted within 14 days.", "metadata": {}, "doc_id": "d2"},
        ]
        prompt = build_grounded_prompt("How long is shipping?", chunks)
        assert "Shipping takes 5 days." in prompt
        assert "Returns accepted within 14 days." in prompt

    def test_source_numbering(self):
        chunks = [
            {"text": "First chunk.", "metadata": {}, "doc_id": "d1"},
            {"text": "Second chunk.", "metadata": {}, "doc_id": "d2"},
        ]
        prompt = build_grounded_prompt("question", chunks)
        assert "[Source 1]" in prompt
        assert "[Source 2]" in prompt

    def test_includes_section_metadata(self):
        chunks = [{"text": "Content.", "metadata": {"section": "FAQ"}, "doc_id": "d1"}]
        prompt = build_grounded_prompt("q", chunks)
        assert "section: FAQ" in prompt

    def test_includes_refusal_instruction(self):
        prompt = build_grounded_prompt("q", [{"text": "x", "metadata": {}, "doc_id": "d"}])
        assert "I don't have enough information" in prompt

    def test_includes_only_from_context_instruction(self):
        prompt = build_grounded_prompt("q", [{"text": "x", "metadata": {}, "doc_id": "d"}])
        assert "ONLY" in prompt

    def test_empty_chunks(self):
        prompt = build_grounded_prompt("What?", [])
        assert "What?" in prompt
        # Should still work, just empty context


# ===========================================================================
# Provider Error Handling
# ===========================================================================


class TestProviderErrors:
    def test_openai_missing_package(self):
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai"):
                OpenAIProvider()

    def test_openai_missing_key(self):
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            with patch.dict("os.environ", {}, clear=True):
                import os
                with patch.object(os.environ, "get", return_value=None):
                    with pytest.raises((ValueError, ImportError)):
                        OpenAIProvider()

    def test_anthropic_missing_package(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic"):
                AnthropicProvider()

    def test_get_llm_unknown_provider(self):
        with pytest.raises(KeyError, match="No llm named"):
            get_llm("nonexistent_provider")


# ===========================================================================
# Mock LLM for testing
# ===========================================================================


class MockLLM(LLMProvider):
    """A mock LLM that returns a predictable answer for testing."""

    def __init__(self, response: str = "The refund window is 30 days. [Source 1]"):
        self._response = response

    @property
    def name(self) -> str:
        return "mock-llm"

    def generate(self, prompt: str, **opts) -> str:
        # If the context is empty/minimal, simulate refusal
        if "CONTEXT:\n\n" in prompt or "CONTEXT:\n---" not in prompt:
            pass  # let it return normal response for most tests
        return self._response


class MockLLMRefusal(LLMProvider):
    """A mock LLM that always refuses (simulating insufficient context)."""

    @property
    def name(self) -> str:
        return "mock-refusal"

    def generate(self, prompt: str, **opts) -> str:
        return "I don't have enough information to answer that."


# ===========================================================================
# KnowledgeBase.answer() — end-to-end with mocked LLM
# ===========================================================================


class TestKnowledgeBaseAnswer:
    def _build_kb(self, tmp_path):
        (tmp_path / "doc.md").write_text(
            "# Refunds\n\nRefunds are processed within 30 days of purchase.\n\n"
            "# Shipping\n\nShipping takes 5-7 business days."
        )
        return KnowledgeBase.build(
            name="test-answer-kb",
            sources=[str(tmp_path)],
            persist=False,
        )

    def test_answer_returns_structured_result(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock = MockLLM("Refunds take 30 days. [Source 1]")

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = kb.answer("What is the refund window?", llm="mock")

        assert "answer" in result
        assert "sources" in result
        assert "question" in result
        assert "mode" in result
        assert "llm_name" in result

    def test_answer_text_present(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock = MockLLM("The refund window is 30 days based on the policy.")

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = kb.answer("refund window?", llm="mock")

        assert result["answer"] == "The refund window is 30 days based on the policy."

    def test_sources_included(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock = MockLLM("Answer here.")

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = kb.answer("refund?", top_k=3, llm="mock")

        assert len(result["sources"]) <= 3
        for src in result["sources"]:
            assert "id" in src
            assert "text" in src
            assert "score" in src
            assert "metadata" in src

    def test_llm_name_in_result(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock = MockLLM("Answer.")

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = kb.answer("q?", llm="mock")

        assert result["llm_name"] == "mock-llm"

    def test_mode_passed_through(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock = MockLLM("Answer.")

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = kb.answer("q?", mode="bm25", llm="mock")

        assert result["mode"] == "bm25"

    def test_refusal_when_context_insufficient(self, tmp_path):
        kb = self._build_kb(tmp_path)
        mock_refusal = MockLLMRefusal()

        with patch("ragforge.pipeline.generation.get_llm", return_value=mock_refusal):
            result = kb.answer("What is quantum physics?", llm="mock")

        assert "don't have enough information" in result["answer"]


# ===========================================================================
# Functional interface with generation
# ===========================================================================


class TestQueryKnowledgeBaseWithGeneration:
    def test_generate_false_returns_no_answer(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nContent here.")

        from ragforge.pipeline import build_knowledge_base
        build_knowledge_base(name="test-gen-false", sources=[str(tmp_path)])

        result = query_knowledge_base(
            knowledge="test-gen-false",
            question="test?",
            generate=False,
        )
        assert result["answer"] is None

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-gen-false"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_generate_true_calls_llm(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Info\n\nThe answer is 42.")

        from ragforge.pipeline import build_knowledge_base
        build_knowledge_base(name="test-gen-true", sources=[str(tmp_path)])

        mock = MockLLM("The answer is 42. [Source 1]")
        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            result = query_knowledge_base(
                knowledge="test-gen-true",
                question="What is the answer?",
                generate=True,
                llm="mock",
            )

        assert result["answer"] == "The answer is 42. [Source 1]"
        assert result["llm"] == "mock-llm"
        assert len(result["chunks"]) >= 1

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-gen-true"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_generate_without_llm_stays_retrieval_only(self, tmp_path):
        (tmp_path / "doc.md").write_text("# X\n\nData.")

        from ragforge.pipeline import build_knowledge_base
        build_knowledge_base(name="test-gen-nollm", sources=[str(tmp_path)])

        # generate=True but llm=None → should NOT call LLM, return retrieval-only
        result = query_knowledge_base(
            knowledge="test-gen-nollm",
            question="test?",
            generate=True,
            llm=None,
        )
        assert result["answer"] is None

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "test-gen-nollm"
        if kb_path.exists():
            shutil.rmtree(kb_path)


# ===========================================================================
# API endpoint tests
# ===========================================================================


class TestAPIGeneration:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app
        return TestClient(app)

    def test_query_without_generate(self, client, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nAPI test content.")
        client.post("/knowledge", json={
            "name": "api-gen-test",
            "sources": [str(tmp_path)],
        })

        resp = client.post("/query", json={
            "knowledge": "api-gen-test",
            "question": "test?",
            "generate": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] is None

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-gen-test"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_with_generate_missing_llm_key(self, client, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nContent.")
        client.post("/knowledge", json={
            "name": "api-gen-test2",
            "sources": [str(tmp_path)],
        })

        # Requesting openai without the key set should return 400
        resp = client.post("/query", json={
            "knowledge": "api-gen-test2",
            "question": "test?",
            "generate": True,
            "llm": "openai",
        })
        # Should fail gracefully (400 for missing key, or 501 for missing package)
        assert resp.status_code in (400, 501)

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-gen-test2"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_query_generate_field_in_response(self, client, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nContent for gen.")
        client.post("/knowledge", json={
            "name": "api-gen-test3",
            "sources": [str(tmp_path)],
        })

        mock = MockLLM("Generated answer here.")
        with patch("ragforge.pipeline.generation.get_llm", return_value=mock):
            resp = client.post("/query", json={
                "knowledge": "api-gen-test3",
                "question": "test?",
                "generate": True,
                "llm": "mock",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Generated answer here."
        assert data["llm"] == "mock-llm"

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-gen-test3"
        if kb_path.exists():
            shutil.rmtree(kb_path)


# ===========================================================================
# Ollama provider (connection error)
# ===========================================================================


class TestOllamaProvider:
    def test_connection_error_when_not_running(self):
        # Use a port that's almost certainly not running Ollama
        provider = OllamaProvider(model="llama3", base_url="http://localhost:99999")
        with pytest.raises(ConnectionError, match="Could not connect to Ollama"):
            provider.generate("Hello")

    def test_name_format(self):
        provider = OllamaProvider(model="qwen2.5")
        assert provider.name == "ollama/qwen2.5"
