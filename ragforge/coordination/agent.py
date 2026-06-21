"""
Agent + Orchestrator: lightweight multi-agent coordination via blackboard.

Key design constraint: agents NEVER call each other directly. They only read/write
the shared Blackboard. This is stigmergy — agents react to signals ("pheromones")
left by other agents in the environment.

Why this matters for cost:
- No full-context re-sends between agents (the #1 token cost driver in multi-agent systems)
- Each agent reads only the entries it needs from the board
- The orchestrator is a simple loop, not an LLM-powered router

Architecture:
    Agent: has an id, a trigger condition (what board state it reacts to), and an action
           (read entries → optionally call LLM/KB → write results back with markers).
    Orchestrator: loop that checks which agents can fire, runs them, and repeats until
                  a goal condition is met or no agent can act (quiescence).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ragforge.coordination.blackboard import Blackboard, BlackboardEntry


@dataclass
class AgentResult:
    """Result of one agent execution step."""

    agent_id: str
    entries_read: list[str]          # keys the agent read
    entries_written: list[str]       # keys the agent wrote
    tokens_used: int = 0            # tokens consumed (if LLM was called)
    cost_usd: float = 0.0          # estimated cost (if LLM was called)
    duration_ms: float = 0.0       # wall-clock time for this step
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "entries_read": self.entries_read,
            "entries_written": self.entries_written,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class Agent:
    """
    A blackboard-coordinated agent.

    An agent has:
      - id: unique identifier
      - trigger: a function that checks the blackboard and returns True if this agent
                 should run (e.g. "findings key exists AND status != reviewed")
      - action: a function that reads the board, does work (optionally calling an LLM
                or KnowledgeBase), and writes results back to the board with markers

    Agents are deliberately simple — the complexity lives in the trigger/action functions,
    not in a heavy framework. This keeps things testable and composable.

    Usage:
        def my_trigger(board: Blackboard) -> bool:
            return board.has_key("findings") and not board.has_key("review")

        def my_action(board: Blackboard, agent_id: str) -> AgentResult:
            findings = board.read("findings")
            # ... process ...
            board.write("review", "looks good", author=agent_id, tags={"status": "approved"})
            return AgentResult(agent_id=agent_id, entries_read=["findings"], entries_written=["review"])

        agent = Agent(id="reviewer", trigger=my_trigger, action=my_action)
    """

    def __init__(
        self,
        id: str,
        trigger: Callable[[Blackboard], bool],
        action: Callable[[Blackboard, str], AgentResult],
        description: str = "",
        max_fires: Optional[int] = None,
    ) -> None:
        """
        Args:
            id: Unique agent identifier.
            trigger: Function(board) -> bool. Returns True when this agent should run.
            action: Function(board, agent_id) -> AgentResult. Does the work.
            description: Human-readable description of what this agent does.
            max_fires: Maximum times this agent can fire per orchestration run.
                       None = unlimited. Prevents infinite loops from a single agent.
        """
        self.id = id
        self.trigger = trigger
        self.action = action
        self.description = description
        self.max_fires = max_fires
        self._fire_count = 0

    def can_fire(self, board: Blackboard) -> bool:
        """Check if this agent's trigger condition is satisfied AND it hasn't exceeded max_fires."""
        if self.max_fires is not None and self._fire_count >= self.max_fires:
            return False
        return self.trigger(board)

    def execute(self, board: Blackboard) -> AgentResult:
        """Run this agent's action against the board."""
        start = time.perf_counter()
        result = self.action(board, self.id)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.duration_ms = elapsed_ms
        self._fire_count += 1
        return result

    def reset(self) -> None:
        """Reset fire count (for reuse across runs)."""
        self._fire_count = 0

    @property
    def fire_count(self) -> int:
        return self._fire_count

    def __repr__(self) -> str:
        desc = f", {self.description!r}" if self.description else ""
        return f"Agent(id={self.id!r}{desc}, fires={self._fire_count})"


@dataclass
class OrchestratorResult:
    """Result of a full orchestration run."""

    steps: list[AgentResult]
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: float = 0.0
    termination_reason: str = ""    # "goal_met", "quiescence", "max_steps", "deadlock"
    board_state: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_duration_ms": self.total_duration_ms,
            "termination_reason": self.termination_reason,
            "num_steps": len(self.steps),
            "board_state": self.board_state,
        }


class Orchestrator:
    """
    Runs agents against a blackboard until a goal is met or no agent can act.

    The orchestrator is a simple, deterministic loop — NOT an LLM-powered router.
    This keeps coordination cost at zero tokens (only the agents themselves use tokens).

    Loop:
      1. Check which agents' trigger conditions are satisfied
      2. If none → quiescence (done)
      3. Run the first eligible agent (priority order = list order)
      4. Check the goal condition
      5. If goal met → done
      6. Repeat from 1

    Safety:
      - max_steps: hard limit on total agent executions (prevents infinite loops)
      - deadlock detection: if the same set of agents fires repeatedly without the
        board changing, it's a deadlock (agents writing the same thing over and over)
      - per-agent max_fires: set on the Agent itself
    """

    def __init__(
        self,
        board: Blackboard,
        agents: list[Agent],
        goal: Optional[Callable[[Blackboard], bool]] = None,
        max_steps: int = 50,
    ) -> None:
        """
        Args:
            board: The shared blackboard.
            agents: Agents to coordinate (checked in list order for priority).
            goal: Optional function(board) -> bool. If it returns True, the run is complete.
                  If None, runs until quiescence or max_steps.
            max_steps: Maximum total agent executions. Safety limit.
        """
        self.board = board
        self.agents = agents
        self.goal = goal
        self.max_steps = max_steps

    def run(self) -> OrchestratorResult:
        """
        Run the orchestration loop to completion.

        Returns an OrchestratorResult with all steps, total cost, and termination reason.
        """
        start_time = time.perf_counter()
        steps: list[AgentResult] = []
        total_tokens = 0
        total_cost = 0.0

        # Reset all agent fire counts
        for agent in self.agents:
            agent.reset()

        # Deadlock detection: track board state hash to detect no-progress
        last_board_hash: Optional[str] = None
        no_progress_count = 0
        max_no_progress = 3  # if board doesn't change 3 times in a row → deadlock

        for step_num in range(self.max_steps):
            # Check goal condition first
            if self.goal and self.goal(self.board):
                return self._finalize(steps, total_tokens, total_cost, start_time, "goal_met")

            # Find eligible agents
            eligible = [a for a in self.agents if a.can_fire(self.board)]
            if not eligible:
                return self._finalize(steps, total_tokens, total_cost, start_time, "quiescence")

            # Deadlock detection: snapshot board state
            current_hash = self._board_hash()

            # Run the first eligible agent (priority = list order)
            agent = eligible[0]
            result = agent.execute(self.board)
            steps.append(result)
            total_tokens += result.tokens_used
            total_cost += result.cost_usd

            # Check if board actually changed
            new_hash = self._board_hash()
            if new_hash == current_hash:
                no_progress_count += 1
                if no_progress_count >= max_no_progress:
                    return self._finalize(
                        steps, total_tokens, total_cost, start_time, "deadlock"
                    )
            else:
                no_progress_count = 0
            last_board_hash = new_hash

        # Exhausted max_steps
        return self._finalize(steps, total_tokens, total_cost, start_time, "max_steps")

    def _board_hash(self) -> str:
        """Quick hash of current board state for deadlock detection."""
        import hashlib
        import json

        entries = self.board.read_all()
        data = json.dumps(
            [(e.key, e.value, e.version) for e in entries], sort_keys=True
        )
        return hashlib.md5(data.encode()).hexdigest()

    def _finalize(
        self,
        steps: list[AgentResult],
        total_tokens: int,
        total_cost: float,
        start_time: float,
        reason: str,
    ) -> OrchestratorResult:
        """Build the final result."""
        elapsed = (time.perf_counter() - start_time) * 1000
        return OrchestratorResult(
            steps=steps,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            total_duration_ms=elapsed,
            termination_reason=reason,
            board_state=self.board.to_dict(),
        )
