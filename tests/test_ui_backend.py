"""
Tests for the UI backend: tracing, eval routes, chat route.

Covers:
  - Tracing utility (Tracer creates well-formed traces with step timings)
  - TraceStore (save/list/get from SQLite)
  - API: GET /traces, GET /traces/{run_id}
  - API: POST /ui/eval/run, GET /ui/eval/history
  - API: POST /ui/chat/message (mocked LLM)
  - KnowledgeBase.query_traced / answer_traced produce traces
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ragforge.tracing import Tracer, Trace, TraceStore, TraceStep


# ===========================================================================
# Tracing utility
# ===========================================================================


class TestTraceStep:
    def test_to_dict(self):
        s = TraceStep(name="retrieval", started_at=1.0, ended_at=1.5, duration_ms=500.0, data={"k": 5})
        d = s.to_dict()
        assert d["name"] == "retrieval"
        assert d["duration_ms"] == 500.0
        assert d["data"]["k"] == 5


class TestTrace:
    def test_step_records_timing(self):
        t = Trace(query="test")
        t.step("first")
        time.sleep(0.01)
        t.step("second")
        t.finish()

        assert len(t.steps) == 2
        assert t.steps[0].name == "first"
        assert t.steps[0].duration_ms > 0
        assert t.steps[1].name == "second"
        assert t.total_duration_ms > 0
        assert t.status == "completed"

    def test_finish_closes_last_step(self):
        t = Trace(query="q")
        t.step("only_step")
        t.finish()
        assert t.steps[0].ended_at > 0
        assert t.steps[0].duration_ms >= 0

    def test_to_dict(self):
        t = Trace(query="q", knowledge="kb")
        t.step("s1", foo="bar")
        t.finish()
        d = t.to_dict()
        assert d["query"] == "q"
        assert d["knowledge"] == "kb"
        assert d["status"] == "completed"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["data"]["foo"] == "bar"


class TestTraceStore:
    def test_save_and_list(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        t = Trace(query="hello", knowledge="kb1")
        t.step("retrieval")
        t.finish()
        store.save(t)

        traces = store.list_traces()
        assert len(traces) == 1
        assert traces[0]["query"] == "hello"
        assert traces[0]["run_id"] == t.run_id

    def test_get_trace_with_steps(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        t = Trace(query="q", knowledge="kb")
        t.step("s1", data_field="value")
        t.step("s2")
        t.finish()
        store.save(t)

        detail = store.get_trace(t.run_id)
        assert detail is not None
        assert detail["run_id"] == t.run_id
        assert len(detail["steps"]) == 2
        assert detail["steps"][0]["name"] == "s1"

    def test_get_missing_returns_none(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        assert store.get_trace("nonexistent") is None

    def test_list_ordering(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        t1 = Trace(query="first", started_at=100.0)
        t1.finish()
        store.save(t1)

        t2 = Trace(query="second", started_at=200.0)
        t2.finish()
        store.save(t2)

        traces = store.list_traces()
        assert traces[0]["query"] == "second"  # Most recent first


class TestTracerContextManager:
    def test_context_manager_saves_trace(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        tracer = Tracer(store=store)

        with tracer.trace(query="test q", knowledge="test-kb") as t:
            t.step("step1")
            time.sleep(0.01)
            t.step("step2")

        # Trace should be saved
        traces = store.list_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "completed"

    def test_context_manager_handles_errors(self, tmp_path):
        store = TraceStore(db_path=tmp_path / "test.db")
        tracer = Tracer(store=store)

        with pytest.raises(ValueError):
            with tracer.trace(query="fail") as t:
                t.step("before_error")
                raise ValueError("boom")

        # Trace should still be saved with error status
        traces = store.list_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "error"


# ===========================================================================
# Pipeline tracing integration
# ===========================================================================


class TestKnowledgeBaseTracing:
    def _build_kb(self, tmp_path):
        from ragforge.pipeline import KnowledgeBase
        (tmp_path / "doc.md").write_text("# Test\n\nRefunds within 30 days.")
        return KnowledgeBase.build(name="trace-test-kb", sources=[str(tmp_path)], persist=False)

    def test_query_traced_returns_run_id(self, tmp_path):
        kb = self._build_kb(tmp_path)
        results, run_id = kb.query_traced("refund?", top_k=3)
        assert run_id is not None
        assert len(run_id) == 12  # hex UUID prefix
        assert len(results) >= 1

    def test_query_traced_creates_trace(self, tmp_path):
        from ragforge.tracing import get_store
        kb = self._build_kb(tmp_path)
        _, run_id = kb.query_traced("test question")

        store = get_store()
        trace = store.get_trace(run_id)
        assert trace is not None
        assert trace["query"] == "test question"
        assert trace["status"] == "completed"
        assert len(trace["steps"]) >= 2  # retrieval + retrieval_done


# ===========================================================================
# API: Traces endpoints
# ===========================================================================


class TestTracesAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app
        return TestClient(app)

    def test_list_traces(self, client):
        resp = client.get("/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert "traces" in data
        assert isinstance(data["traces"], list)

    def test_get_trace_not_found(self, client):
        resp = client.get("/traces/nonexistent123")
        assert resp.status_code == 404


# ===========================================================================
# API: UI Eval endpoints
# ===========================================================================


class TestUIEvalAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app
        return TestClient(app)

    def test_eval_run_missing_kb(self, client):
        resp = client.post("/ui/eval/run", json={
            "knowledge": "nonexistent-kb",
            "golden_dataset": [{"question": "test?"}],
        })
        assert resp.status_code == 404

    def test_eval_run_success(self, client, tmp_path):
        # Build a KB first
        (tmp_path / "doc.md").write_text("# Test\n\nThe answer is 42.")
        client.post("/knowledge", json={
            "name": "ui-eval-test-kb",
            "sources": [str(tmp_path)],
        })

        resp = client.post("/ui/eval/run", json={
            "knowledge": "ui-eval-test-kb",
            "golden_dataset": [{"question": "What is the answer?"}],
            "metrics": ["hit_rate", "mrr"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "hit_rate" in data["summary"]

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "ui-eval-test-kb"
        if kb_path.exists():
            shutil.rmtree(kb_path)

    def test_eval_history(self, client):
        resp = client.get("/ui/eval/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# API: UI Chat endpoint
# ===========================================================================


class TestUIChatAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app
        return TestClient(app)

    def test_chat_missing_kb(self, client):
        resp = client.post("/ui/chat/message", json={
            "knowledge": "nonexistent-chat-kb",
            "question": "hello?",
        })
        assert resp.status_code == 404

    def test_chat_retrieval_only(self, client, tmp_path):
        (tmp_path / "doc.md").write_text("# FAQ\n\nRefunds take 30 days.")
        client.post("/knowledge", json={
            "name": "ui-chat-test-kb",
            "sources": [str(tmp_path)],
        })

        resp = client.post("/ui/chat/message", json={
            "knowledge": "ui-chat-test-kb",
            "question": "refund time?",
            "generate": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] is None  # No generation
        assert len(data["sources"]) >= 1
        assert data["run_id"] is not None  # Trace was created
        assert data["knowledge"] == "ui-chat-test-kb"

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "ui-chat-test-kb"
        if kb_path.exists():
            shutil.rmtree(kb_path)
