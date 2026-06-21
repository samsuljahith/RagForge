"""
Tests for the coordination module: blackboard, agent, orchestrator, benchmark, API, CLI.

Covers:
  - Blackboard read/write/markers/history/versioning
  - InMemoryBlackboard operations
  - Persistence (write → reload → state intact)
  - Concurrency-safe writes
  - Orchestrator running agents to completion
  - Deadlock/max-steps handling
  - Quiescence detection
  - Benchmark producing a comparison
  - CLI arg parsing
  - API endpoints (via TestClient)
"""

from __future__ import annotations

import threading
import tempfile
from pathlib import Path

import pytest

from ragforge.coordination.blackboard import Blackboard, InMemoryBlackboard, BlackboardEntry
from ragforge.coordination.agent import Agent, AgentResult, Orchestrator, OrchestratorResult
from ragforge.coordination.benchmark import (
    BenchmarkResult,
    BenchmarkTask,
    CostReport,
    CostTracker,
    run_benchmark,
    estimate_tokens_for_text,
)


# ═══════════════════════════════════════════════════════════════════════════════
# BLACKBOARD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBlackboardBasic:
    """Basic read/write operations on InMemoryBlackboard."""

    def test_write_and_read(self):
        board = InMemoryBlackboard()
        entry = board.write("greeting", "hello", author="agent-1")
        assert entry.key == "greeting"
        assert entry.value == "hello"
        assert entry.author == "agent-1"
        assert entry.version == 1

        read = board.read("greeting")
        assert read is not None
        assert read.value == "hello"

    def test_read_nonexistent_returns_none(self):
        board = InMemoryBlackboard()
        assert board.read("nope") is None

    def test_overwrite_increments_version(self):
        board = InMemoryBlackboard()
        board.write("x", 1, author="a")
        board.write("x", 2, author="b")
        entry = board.read("x")
        assert entry.value == 2
        assert entry.version == 2
        assert entry.author == "b"

    def test_write_with_tags(self):
        board = InMemoryBlackboard()
        board.write("item", "data", author="a", tags={"status": "ready", "confidence": 0.9})
        entry = board.read("item")
        assert entry.tags == {"status": "ready", "confidence": 0.9}

    def test_read_all(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x")
        board.write("b", 2, author="y")
        entries = board.read_all()
        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert keys == {"a", "b"}

    def test_keys_and_has_key(self):
        board = InMemoryBlackboard()
        board.write("alpha", "val", author="a")
        assert board.has_key("alpha")
        assert not board.has_key("beta")
        assert board.keys() == ["alpha"]

    def test_delete(self):
        board = InMemoryBlackboard()
        board.write("x", 1, author="a")
        assert board.delete("x")
        assert board.read("x") is None
        assert not board.delete("x")  # already gone

    def test_clear(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x")
        board.write("b", 2, author="y")
        board.clear()
        assert board.read_all() == []


class TestBlackboardTags:
    """Tag-based queries (the stigmergy mechanism)."""

    def test_read_by_tag_exists(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x", tags={"status": "ready"})
        board.write("b", 2, author="y", tags={"status": "pending"})
        board.write("c", 3, author="z", tags={})  # no status tag

        results = board.read_by_tag("status")
        assert len(results) == 2
        keys = {e.key for e in results}
        assert keys == {"a", "b"}

    def test_read_by_tag_with_predicate(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x", tags={"confidence": 0.9})
        board.write("b", 2, author="y", tags={"confidence": 0.3})
        board.write("c", 3, author="z", tags={"confidence": 0.7})

        high_conf = board.read_by_tag("confidence", lambda v: v > 0.5)
        assert len(high_conf) == 2
        keys = {e.key for e in high_conf}
        assert keys == {"a", "c"}

    def test_read_by_author(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="alice")
        board.write("b", 2, author="bob")
        board.write("c", 3, author="alice")

        alice_entries = board.read_by_author("alice")
        assert len(alice_entries) == 2

    def test_watch_predicate(self):
        board = InMemoryBlackboard()
        board.write("x", "ready", author="a", tags={"status": "done"})
        board.write("y", "pending", author="b", tags={"status": "wip"})

        done = board.watch(lambda e: e.tags.get("status") == "done")
        assert len(done) == 1
        assert done[0].key == "x"


class TestBlackboardHistory:
    """History/audit log."""

    def test_history_records_all_writes(self):
        board = InMemoryBlackboard()
        board.write("x", 1, author="a")
        board.write("x", 2, author="b")
        board.write("x", 3, author="c")

        hist = board.history(key="x")
        assert len(hist) == 3
        assert hist[0].version == 1
        assert hist[2].version == 3

    def test_history_count(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x")
        board.write("b", 2, author="y")
        board.write("a", 3, author="z")
        assert board.history_count() == 3

    def test_history_preserved_after_clear(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x")
        board.clear()
        # History is preserved even after clear
        assert board.history_count() == 1

    def test_history_preserved_after_delete(self):
        board = InMemoryBlackboard()
        board.write("a", 1, author="x")
        board.delete("a")
        assert board.history_count() == 1


class TestBlackboardPersistence:
    """SQLite persistence (write → close → reopen → state intact)."""

    def test_persist_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write some data
            board = Blackboard("test-persist", persist_dir=tmpdir)
            board.write("key1", {"data": 42}, author="agent-a", tags={"status": "done"})
            board.write("key2", "hello", author="agent-b")
            board.close()

            # Reopen and verify
            board2 = Blackboard("test-persist", persist_dir=tmpdir)
            entry = board2.read("key1")
            assert entry is not None
            assert entry.value == {"data": 42}
            assert entry.author == "agent-a"
            assert entry.tags == {"status": "done"}
            assert entry.version == 1

            entry2 = board2.read("key2")
            assert entry2.value == "hello"

            # History persists too
            assert board2.history_count() == 2
            board2.close()

    def test_version_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            board = Blackboard("ver-test", persist_dir=tmpdir)
            board.write("k", 1, author="a")
            board.write("k", 2, author="a")
            board.close()

            board2 = Blackboard("ver-test", persist_dir=tmpdir)
            board2.write("k", 3, author="a")
            entry = board2.read("k")
            assert entry.version == 3
            board2.close()


class TestBlackboardConcurrency:
    """Thread-safety of writes."""

    def test_concurrent_writes_no_corruption(self):
        board = InMemoryBlackboard()
        errors = []

        def writer(agent_id: str, n: int):
            try:
                for i in range(n):
                    board.write(f"key-{agent_id}-{i}", i, author=agent_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(f"agent-{j}", 20))
            for j in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # 5 agents × 20 writes = 100 unique keys
        assert len(board.keys()) == 100
        assert board.history_count() == 100


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrchestrator:
    """Orchestrator running agents to completion."""

    def _simple_agents(self):
        """Two agents: writer writes 'data', reader reads 'data' and writes 'result'."""

        def writer_trigger(b):
            return not b.has_key("data")

        def writer_action(b, aid):
            b.write("data", "hello", author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=["data"])

        def reader_trigger(b):
            return b.has_key("data") and not b.has_key("result")

        def reader_action(b, aid):
            b.write("result", "done", author=aid)
            return AgentResult(agent_id=aid, entries_read=["data"], entries_written=["result"])

        return [
            Agent(id="writer", trigger=writer_trigger, action=writer_action),
            Agent(id="reader", trigger=reader_trigger, action=reader_action),
        ]

    def test_runs_to_goal(self):
        board = InMemoryBlackboard()
        agents = self._simple_agents()
        goal = lambda b: b.has_key("result")

        orch = Orchestrator(board, agents, goal=goal, max_steps=10)
        result = orch.run()

        assert result.termination_reason == "goal_met"
        assert len(result.steps) == 2
        assert result.steps[0].agent_id == "writer"
        assert result.steps[1].agent_id == "reader"

    def test_quiescence(self):
        """No agent can fire → quiescence."""
        board = InMemoryBlackboard()
        board.write("data", "exists", author="seed")
        board.write("result", "exists", author="seed")

        agents = self._simple_agents()
        orch = Orchestrator(board, agents, max_steps=10)
        result = orch.run()

        assert result.termination_reason == "quiescence"
        assert len(result.steps) == 0

    def test_max_steps_limit(self):
        """Agent keeps firing → hits max_steps."""
        board = InMemoryBlackboard()
        counter = [0]

        def always_trigger(b):
            return True

        def increment_action(b, aid):
            counter[0] += 1
            b.write(f"step-{counter[0]}", counter[0], author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=[f"step-{counter[0]}"])

        agents = [Agent(id="looper", trigger=always_trigger, action=increment_action)]
        orch = Orchestrator(board, agents, max_steps=5)
        result = orch.run()

        assert result.termination_reason == "max_steps"
        assert len(result.steps) == 5

    def test_deadlock_detection(self):
        """Agent fires but board doesn't change → deadlock."""
        board = InMemoryBlackboard()
        board.write("x", "stuck", author="seed")

        def always_trigger(b):
            return True

        def noop_action(b, aid):
            # Reads but writes nothing new — board state unchanged
            return AgentResult(agent_id=aid, entries_read=["x"], entries_written=[])

        agents = [Agent(id="stuck", trigger=always_trigger, action=noop_action)]
        orch = Orchestrator(board, agents, max_steps=20)
        result = orch.run()

        assert result.termination_reason == "deadlock"
        assert len(result.steps) == 3  # fires 3 times then deadlock detected

    def test_agent_max_fires(self):
        """Per-agent fire limit prevents infinite loops from one agent."""
        board = InMemoryBlackboard()
        counter = [0]

        def always_trigger(b):
            return True

        def count_action(b, aid):
            counter[0] += 1
            b.write(f"c{counter[0]}", counter[0], author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=[f"c{counter[0]}"])

        agents = [Agent(id="limited", trigger=always_trigger, action=count_action, max_fires=3)]
        orch = Orchestrator(board, agents, max_steps=100)
        result = orch.run()

        # Agent fires 3 times then can't fire → quiescence
        assert result.termination_reason == "quiescence"
        assert len(result.steps) == 3

    def test_multi_agent_priority(self):
        """Agents are checked in list order (priority)."""
        board = InMemoryBlackboard()
        fired = []

        def t(b):
            return not b.has_key("done")

        def action_a(b, aid):
            fired.append("a")
            b.write("done", True, author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=["done"])

        def action_b(b, aid):
            fired.append("b")
            b.write("done", True, author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=["done"])

        agents = [
            Agent(id="first", trigger=t, action=action_a),
            Agent(id="second", trigger=t, action=action_b),
        ]
        orch = Orchestrator(board, agents, goal=lambda b: b.has_key("done"), max_steps=5)
        result = orch.run()

        assert fired == ["a"]  # first agent has priority

    def test_result_tracks_tokens_and_cost(self):
        """OrchestratorResult tallies tokens/cost from agent results."""
        board = InMemoryBlackboard()

        def t(b):
            return not b.has_key("out")

        def action(b, aid):
            b.write("out", "done", author=aid)
            return AgentResult(
                agent_id=aid,
                entries_read=[],
                entries_written=["out"],
                tokens_used=150,
                cost_usd=0.002,
            )

        agents = [Agent(id="llm-agent", trigger=t, action=action)]
        orch = Orchestrator(board, agents, goal=lambda b: b.has_key("out"), max_steps=5)
        result = orch.run()

        assert result.total_tokens == 150
        assert result.total_cost_usd == 0.002


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmark:
    """Cost benchmark utility."""

    def test_cost_tracker(self):
        tracker = CostTracker()
        tracker.record_tokens(100, 50, agent_id="a", purpose="test")
        tracker.record_tokens(200, 100, agent_id="b", purpose="test2")

        assert tracker.total_tokens == 450
        assert tracker.total_input_tokens == 300
        assert tracker.total_output_tokens == 150
        assert tracker.num_calls == 2
        assert tracker.total_cost > 0

    def test_cost_tracker_from_text(self):
        tracker = CostTracker()
        # ~100 chars → ~25 tokens
        tracker.record_call("a" * 100, "b" * 40, agent_id="x")
        assert tracker.total_input_tokens == 25
        assert tracker.total_output_tokens == 10

    def test_benchmark_result_savings(self):
        direct = CostReport(mode="direct", total_tokens=1000, input_tokens=800,
                            output_tokens=200, estimated_cost_usd=0.01)
        bb = CostReport(mode="blackboard", total_tokens=400, input_tokens=300,
                        output_tokens=100, estimated_cost_usd=0.004)
        result = BenchmarkResult(direct=direct, blackboard=bb, task_description="test")

        assert result.token_savings == 600
        assert result.token_savings_pct == 60.0
        assert result.cost_savings_usd == 0.006
        assert result.cost_savings_pct == 60.0

    def test_run_benchmark(self):
        """Run a full benchmark and get a valid comparison."""

        # Blackboard agents
        def t(b):
            return b.has_key("input") and not b.has_key("output")

        def action(b, aid):
            b.write("output", "processed", author=aid)
            return AgentResult(
                agent_id=aid,
                entries_read=["input"],
                entries_written=["output"],
                tokens_used=50,
                cost_usd=0.001,
                metadata={"input_tokens": 40, "output_tokens": 10},
            )

        bb_agents = [Agent(id="processor", trigger=t, action=action)]

        # Need to seed the board — add a trigger-setting agent first
        def seed_trigger(b):
            return not b.has_key("input")

        def seed_action(b, aid):
            b.write("input", "raw data", author=aid)
            return AgentResult(agent_id=aid, entries_read=[], entries_written=["input"])

        bb_agents = [
            Agent(id="seeder", trigger=seed_trigger, action=seed_action),
            Agent(id="processor", trigger=t, action=action),
        ]

        # Direct messaging simulation (more expensive: full context re-send)
        def simulate_direct(tracker: CostTracker):
            tracker.record_tokens(200, 50, agent_id="agent-1", purpose="process with full context")
            tracker.record_tokens(300, 80, agent_id="agent-2", purpose="re-process with full history")

        task = BenchmarkTask(
            description="Test task",
            agents=bb_agents,
            goal=lambda b: b.has_key("output"),
            simulate_direct=simulate_direct,
            max_steps=10,
        )

        result = run_benchmark(task)

        assert isinstance(result, BenchmarkResult)
        assert result.direct.total_tokens == 630  # 200+50+300+80
        assert result.blackboard.total_tokens == 50  # only processor used tokens
        assert result.token_savings > 0
        assert result.token_savings_pct > 0
        assert len(result.summary()) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCoordinationCLI:
    """CLI argument parsing for agents subcommands."""

    def test_agents_run_args(self):
        from ragforge.cli import build_parser

        p = build_parser()
        args = p.parse_args(["agents", "run", "config.py", "--max-steps", "20", "--persist"])
        assert args.config == "config.py"
        assert args.max_steps == 20
        assert args.persist is True

    def test_agents_benchmark_args(self):
        from ragforge.cli import build_parser

        p = build_parser()
        args = p.parse_args(["agents", "benchmark", "bench.py", "--json"])
        assert args.config == "bench.py"
        assert args.json is True

    def test_agents_board_args(self):
        from ragforge.cli import build_parser

        p = build_parser()
        args = p.parse_args(["agents", "board", "my-board", "--json"])
        assert args.name == "my-board"
        assert args.json is True


# ═══════════════════════════════════════════════════════════════════════════════
# API TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCoordinationAPI:
    """API endpoints for coordination."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api.app import app
        return TestClient(app)

    def test_create_board(self, client):
        resp = client.post("/coordination/boards", json={"name": "test-api", "persist": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-api"
        assert data["entries"] == []

    def test_write_and_read(self, client):
        # Create board
        client.post("/coordination/boards", json={"name": "rw-test"})

        # Write
        resp = client.post("/coordination/boards/rw-test/write", json={
            "key": "greeting",
            "value": "hello world",
            "author": "test-agent",
            "tags": {"status": "ready"},
        })
        assert resp.status_code == 200
        entry = resp.json()
        assert entry["key"] == "greeting"
        assert entry["value"] == "hello world"
        assert entry["tags"]["status"] == "ready"
        assert entry["version"] == 1

        # Read board state
        resp = client.get("/coordination/boards/rw-test")
        assert resp.status_code == 200
        state = resp.json()
        assert len(state["entries"]) == 1

    def test_board_not_found(self, client):
        resp = client.get("/coordination/boards/nonexistent")
        assert resp.status_code == 404

    def test_history(self, client):
        client.post("/coordination/boards", json={"name": "hist-test"})
        client.post("/coordination/boards/hist-test/write", json={
            "key": "x", "value": 1, "author": "a", "tags": {},
        })
        client.post("/coordination/boards/hist-test/write", json={
            "key": "x", "value": 2, "author": "b", "tags": {},
        })

        resp = client.get("/coordination/boards/hist-test/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_run_coordination(self, client):
        resp = client.post("/coordination/run", json={
            "board_name": "run-test",
            "agents": [
                {
                    "id": "processor",
                    "trigger_key": "data",
                    "trigger_condition": "missing:result",
                    "output_key": "result",
                    "output_value": "processed",
                    "max_fires": 1,
                },
            ],
            "seed": [{"key": "data", "value": "raw input", "author": "api"}],
            "goal_key": "result",
            "max_steps": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["termination_reason"] == "goal_met"
        assert data["num_steps"] == 1
        assert data["run_id"].startswith("run-")

    def test_get_run(self, client):
        # First run a task
        resp = client.post("/coordination/run", json={
            "board_name": "get-run-test",
            "agents": [{
                "id": "a",
                "trigger_key": "x",
                "trigger_condition": "exists",
                "output_key": "y",
                "output_value": 42,
            }],
            "seed": [{"key": "x", "value": 1, "author": "seed"}],
            "goal_key": "y",
            "max_steps": 5,
        })
        run_id = resp.json()["run_id"]

        # Then retrieve it
        resp = client.get(f"/coordination/run/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["termination_reason"] == "goal_met"

    def test_get_run_not_found(self, client):
        resp = client.get("/coordination/run/nonexistent")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Entry and result serialization."""

    def test_entry_to_dict(self):
        entry = BlackboardEntry(
            key="k", value={"nested": True}, author="a",
            timestamp="2025-01-01T00:00:00Z", tags={"x": 1}, version=3,
        )
        d = entry.to_dict()
        assert d["key"] == "k"
        assert d["value"] == {"nested": True}
        assert d["version"] == 3

    def test_entry_from_dict(self):
        d = {"key": "k", "value": [1, 2], "author": "a",
             "timestamp": "t", "tags": {}, "version": 2}
        entry = BlackboardEntry.from_dict(d)
        assert entry.key == "k"
        assert entry.value == [1, 2]
        assert entry.version == 2

    def test_orchestrator_result_to_dict(self):
        result = OrchestratorResult(
            steps=[AgentResult(agent_id="a", entries_read=["x"], entries_written=["y"],
                               tokens_used=100, cost_usd=0.01)],
            total_tokens=100,
            total_cost_usd=0.01,
            total_duration_ms=50.0,
            termination_reason="goal_met",
        )
        d = result.to_dict()
        assert d["num_steps"] == 1
        assert d["total_tokens"] == 100
        assert d["termination_reason"] == "goal_met"

    def test_board_to_dict(self):
        board = InMemoryBlackboard("test")
        board.write("a", 1, author="x")
        d = board.to_dict()
        assert d["name"] == "test"
        assert len(d["entries"]) == 1
        assert d["history_count"] == 1
