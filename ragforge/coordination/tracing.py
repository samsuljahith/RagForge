"""
Tracing integration for the coordination module.

Hooks coordination runs into the existing RAGForge tracing system so they show
up in the UI trace view alongside pipeline queries. Each orchestration run
becomes a Trace with steps recording which agent fired, what it read/wrote,
token usage, and cost.

Usage:
    from ragforge.coordination.tracing import traced_run

    result = traced_run(board, agents, goal=goal_fn)
    # Run is automatically saved to the trace store
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ragforge.coordination.blackboard import Blackboard
from ragforge.coordination.agent import Agent, Orchestrator, OrchestratorResult


def traced_run(
    board: Blackboard,
    agents: list[Agent],
    goal: Optional[Callable[[Blackboard], bool]] = None,
    max_steps: int = 50,
    trace_name: str = "coordination",
) -> OrchestratorResult:
    """
    Run an orchestration with full tracing.

    The run is recorded as a Trace in RAGForge's trace store (SQLite), with
    each agent execution as a step. This makes coordination visible in the
    UI dashboard alongside pipeline traces.

    Args:
        board: The shared blackboard.
        agents: Agents to coordinate.
        goal: Optional goal condition.
        max_steps: Safety limit.
        trace_name: Label for the trace (shows in UI).

    Returns:
        OrchestratorResult (same as Orchestrator.run()).
    """
    from ragforge.tracing import Tracer

    tracer = Tracer()

    with tracer.trace(
        query=trace_name,
        knowledge=f"board:{board.name}",
        trace_type="coordination",
    ) as t:
        # Record setup
        t.step("setup", agents=[a.id for a in agents], board=board.name, max_steps=max_steps)

        # Run orchestration
        orch = Orchestrator(board, agents, goal=goal, max_steps=max_steps)
        result = orch.run()

        # Record each agent step
        for step in result.steps:
            t.step(
                f"agent:{step.agent_id}",
                entries_read=step.entries_read,
                entries_written=step.entries_written,
                tokens_used=step.tokens_used,
                cost_usd=step.cost_usd,
                duration_ms=step.duration_ms,
            )

        # Record summary
        t.step(
            "summary",
            termination_reason=result.termination_reason,
            total_steps=len(result.steps),
            total_tokens=result.total_tokens,
            total_cost_usd=result.total_cost_usd,
            board_keys=board.keys(),
        )

        # Add cost metadata to the trace
        t.metadata["coordination"] = {
            "total_tokens": result.total_tokens,
            "total_cost_usd": result.total_cost_usd,
            "num_steps": len(result.steps),
            "termination_reason": result.termination_reason,
            "agents_fired": [s.agent_id for s in result.steps],
        }

    return result
