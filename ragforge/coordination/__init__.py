"""
Coordination module: multi-agent blackboard-based coordination.

Instead of agents messaging each other directly (expensive: each handoff =
full context re-send to an LLM), agents read and write a shared Blackboard.
This is stigmergy — agents leave signals in the environment and react to
signals left by others, like ants leaving pheromone trails.

Why this is cheaper:
- No full-context re-sends between agents
- Agents read only the entries they need, not entire conversation histories
- Shared state survives crashes (SQLite persistence)
- Observable: every write is logged, traceable, replayable
"""

from ragforge.coordination.blackboard import Blackboard, InMemoryBlackboard, BlackboardEntry
from ragforge.coordination.agent import Agent, AgentResult, Orchestrator, OrchestratorResult
from ragforge.coordination.benchmark import (
    BenchmarkResult,
    BenchmarkTask,
    CostReport,
    CostTracker,
    run_benchmark,
)
from ragforge.coordination.tracing import traced_run

__all__ = [
    "Blackboard",
    "InMemoryBlackboard",
    "BlackboardEntry",
    "Agent",
    "AgentResult",
    "Orchestrator",
    "OrchestratorResult",
    "BenchmarkResult",
    "BenchmarkTask",
    "CostReport",
    "CostTracker",
    "run_benchmark",
    "traced_run",
]
