"""
Lightweight tracing for the RAGForge pipeline.

Records structured traces of each pipeline run: the query, retrieval step (chunks,
scores, mode, k), rerank step, prompt sent to LLM, LLM response, char counts,
and timing per step + total. Stored locally in SQLite.

Design: one clean Tracer object that the pipeline writes to at key step boundaries.
No scattered logging — instrument once, observe everything.

Usage:
    from ragforge.tracing import Tracer

    tracer = Tracer()
    with tracer.trace("my-query") as t:
        t.step("retrieval", chunks=[...], scores=[...], mode="hybrid", k=5)
        t.step("rerank", chunks=[...])
        t.step("prompt", text=prompt, char_count=len(prompt))
        t.step("response", text=answer, char_count=len(answer))
    # Trace is automatically persisted to SQLite
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Generator


# Default local storage directory
_TRACES_DIR = Path.home() / ".ragforge"
_DB_PATH = _TRACES_DIR / "traces.db"


@dataclass
class TraceStep:
    """One step in a pipeline trace (retrieval, rerank, prompt, response, etc.)."""

    name: str
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Trace:
    """A full pipeline trace: one query → series of steps → result."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    knowledge: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    total_duration_ms: float = 0.0
    status: str = "running"  # running | completed | error
    steps: list[TraceStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def step(self, name: str, **data: Any) -> "TraceStep":
        """
        Record a pipeline step with timing.

        Call this at the START of a step. The step's duration is measured
        until the next step() call or until the trace ends.
        """
        now = time.time()
        # Close previous step if open
        if self.steps and self.steps[-1].ended_at == 0.0:
            prev = self.steps[-1]
            prev.ended_at = now
            prev.duration_ms = round((now - prev.started_at) * 1000, 2)

        s = TraceStep(name=name, started_at=now, data=data)
        self.steps.append(s)
        return s

    def finish(self, status: str = "completed") -> None:
        """Finish the trace and close any open step."""
        now = time.time()
        # Close last step
        if self.steps and self.steps[-1].ended_at == 0.0:
            last = self.steps[-1]
            last.ended_at = now
            last.duration_ms = round((now - last.started_at) * 1000, 2)

        self.ended_at = now
        self.total_duration_ms = round((now - self.started_at) * 1000, 2)
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "knowledge": self.knowledge,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }


class TraceStore:
    """SQLite-backed local storage for traces."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    run_id TEXT PRIMARY KEY,
                    query TEXT,
                    knowledge TEXT,
                    started_at REAL,
                    ended_at REAL,
                    total_duration_ms REAL,
                    status TEXT,
                    steps_json TEXT,
                    metadata_json TEXT
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def save(self, trace: Trace) -> None:
        """Persist a trace to the local SQLite database."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO traces
                   (run_id, query, knowledge, started_at, ended_at,
                    total_duration_ms, status, steps_json, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trace.run_id,
                    trace.query,
                    trace.knowledge,
                    trace.started_at,
                    trace.ended_at,
                    trace.total_duration_ms,
                    trace.status,
                    json.dumps([s.to_dict() for s in trace.steps]),
                    json.dumps(trace.metadata),
                ),
            )

    def list_traces(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List recent traces (summary, no step details)."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT run_id, query, knowledge, started_at, ended_at,
                          total_duration_ms, status
                   FROM traces ORDER BY started_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_trace(self, run_id: str) -> dict[str, Any] | None:
        """Get full trace detail including steps."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM traces WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["steps"] = json.loads(d.pop("steps_json"))
        d["metadata"] = json.loads(d.pop("metadata_json"))
        return d


# Global tracer (singleton-ish — created on first use)
_store: TraceStore | None = None


def get_store(db_path: str | Path | None = None) -> TraceStore:
    """Get or create the global TraceStore."""
    global _store
    if _store is None:
        _store = TraceStore(db_path=db_path)
    return _store


class Tracer:
    """
    The main tracing interface for the pipeline.

    Usage:
        tracer = Tracer()
        with tracer.trace(query="How?", knowledge="my-kb") as t:
            t.step("retrieval", chunks=[...], mode="hybrid")
            t.step("generation", prompt=prompt)
        # Trace auto-saved to SQLite
    """

    def __init__(self, store: TraceStore | None = None) -> None:
        self._store = store or get_store()

    @contextmanager
    def trace(self, query: str = "", knowledge: str = "", **metadata: Any) -> Generator[Trace, None, None]:
        """
        Context manager that creates, times, and persists a trace.

        Usage:
            with tracer.trace(query="...", knowledge="my-kb") as t:
                t.step("retrieval", ...)
                t.step("generation", ...)
            # Trace is saved automatically on exit
        """
        t = Trace(query=query, knowledge=knowledge, metadata=metadata)
        try:
            yield t
            t.finish("completed")
        except Exception as e:
            t.finish("error")
            t.metadata["error"] = str(e)
            raise
        finally:
            self._store.save(t)

    def record(self, trace: Trace) -> None:
        """Manually save a trace (if not using the context manager)."""
        self._store.save(trace)
