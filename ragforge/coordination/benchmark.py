"""
Benchmark utility: measure token/cost savings of blackboard coordination vs direct messaging.

The selling point of blackboard coordination is measurable cost savings. This module
provides a head-to-head comparison:

  (a) DIRECT MESSAGING baseline: agents pass full context to each other via simulated
      messages. Each handoff re-sends the entire conversation history to the LLM —
      this is what most multi-agent frameworks do, and it's expensive.

  (b) BLACKBOARD coordination: agents share via the blackboard. Each agent reads only
      the specific entries it needs, not the full history. Context is targeted.

The benchmark runs the SAME logical task both ways and reports:
  - Total tokens used (input + output) for each approach
  - Estimated cost (USD) for each
  - Token savings (absolute and percentage)
  - Latency comparison

Honesty note: savings depend heavily on the task. Short tasks with little shared context
may show minimal savings. Long tasks with many handoffs and growing context windows
show dramatic savings. The benchmark measures YOUR actual task, not a cherry-picked demo.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ragforge.coordination.blackboard import InMemoryBlackboard
from ragforge.coordination.agent import Agent, AgentResult, Orchestrator, OrchestratorResult


@dataclass
class CostReport:
    """Cost metrics for one run (either direct or blackboard)."""

    mode: str                       # "direct" or "blackboard"
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    num_llm_calls: int = 0
    num_steps: int = 0
    duration_ms: float = 0.0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "num_llm_calls": self.num_llm_calls,
            "num_steps": self.num_steps,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class BenchmarkResult:
    """Head-to-head comparison of direct messaging vs blackboard coordination."""

    direct: CostReport
    blackboard: CostReport
    task_description: str = ""

    @property
    def token_savings(self) -> int:
        """Absolute token savings (positive = blackboard is cheaper)."""
        return self.direct.total_tokens - self.blackboard.total_tokens

    @property
    def token_savings_pct(self) -> float:
        """Percentage token savings (0-100). Higher = blackboard is cheaper."""
        if self.direct.total_tokens == 0:
            return 0.0
        return (self.token_savings / self.direct.total_tokens) * 100

    @property
    def cost_savings_usd(self) -> float:
        """Absolute cost savings in USD."""
        return self.direct.estimated_cost_usd - self.blackboard.estimated_cost_usd

    @property
    def cost_savings_pct(self) -> float:
        """Percentage cost savings."""
        if self.direct.estimated_cost_usd == 0:
            return 0.0
        return (self.cost_savings_usd / self.direct.estimated_cost_usd) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_description": self.task_description,
            "direct": self.direct.to_dict(),
            "blackboard": self.blackboard.to_dict(),
            "savings": {
                "tokens_saved": self.token_savings,
                "tokens_saved_pct": round(self.token_savings_pct, 1),
                "cost_saved_usd": round(self.cost_savings_usd, 6),
                "cost_saved_pct": round(self.cost_savings_pct, 1),
            },
        }

    def summary(self) -> str:
        """Human-readable summary of the benchmark results."""
        lines = [
            f"{'═' * 60}",
            f"  BENCHMARK: {self.task_description or 'Multi-Agent Coordination'}",
            f"{'═' * 60}",
            f"",
            f"  {'Metric':<25} {'Direct':>12} {'Blackboard':>12} {'Savings':>12}",
            f"  {'─' * 25} {'─' * 12} {'─' * 12} {'─' * 12}",
            f"  {'Total tokens':<25} {self.direct.total_tokens:>12,} {self.blackboard.total_tokens:>12,} {self.token_savings:>+12,}",
            f"  {'  Input tokens':<25} {self.direct.input_tokens:>12,} {self.blackboard.input_tokens:>12,} {self.direct.input_tokens - self.blackboard.input_tokens:>+12,}",
            f"  {'  Output tokens':<25} {self.direct.output_tokens:>12,} {self.blackboard.output_tokens:>12,} {self.direct.output_tokens - self.blackboard.output_tokens:>+12,}",
            f"  {'LLM calls':<25} {self.direct.num_llm_calls:>12} {self.blackboard.num_llm_calls:>12} {self.direct.num_llm_calls - self.blackboard.num_llm_calls:>+12}",
            f"  {'Est. cost (USD)':<25} {'$' + f'{self.direct.estimated_cost_usd:.4f}':>11} {'$' + f'{self.blackboard.estimated_cost_usd:.4f}':>11} {'$' + f'{self.cost_savings_usd:.4f}':>11}",
            f"  {'Duration (ms)':<25} {self.direct.duration_ms:>12.0f} {self.blackboard.duration_ms:>12.0f} {self.direct.duration_ms - self.blackboard.duration_ms:>+12.0f}",
            f"",
            f"  Token savings: {self.token_savings_pct:.1f}% fewer tokens with blackboard",
            f"  Cost savings:  {self.cost_savings_pct:.1f}% cheaper with blackboard",
            f"{'═' * 60}",
        ]
        return "\n".join(lines)


# ─── Token Counting Helpers ────────────────────────────────────────────────────

def estimate_tokens_for_text(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return max(1, len(text) // 4)


# Default pricing (GPT-4o level, as of 2025)
DEFAULT_PRICING = {
    "input_per_1k": 0.005,    # $5 per 1M input tokens
    "output_per_1k": 0.015,   # $15 per 1M output tokens
}


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: Optional[dict[str, float]] = None,
) -> float:
    """Estimate cost in USD given token counts and pricing."""
    p = pricing or DEFAULT_PRICING
    return (input_tokens / 1000 * p["input_per_1k"]) + (output_tokens / 1000 * p["output_per_1k"])


# ─── LLM Call Simulator ────────────────────────────────────────────────────────

@dataclass
class LLMCallRecord:
    """Record of a simulated or real LLM call for cost tracking."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    agent_id: str
    purpose: str = ""


class CostTracker:
    """
    Tracks token usage and cost across multiple LLM calls.

    Used by both the direct-messaging simulator and the blackboard agents
    to measure and compare total resource consumption.
    """

    def __init__(self, pricing: Optional[dict[str, float]] = None) -> None:
        self.pricing = pricing or DEFAULT_PRICING
        self.calls: list[LLMCallRecord] = []

    def record_call(
        self,
        input_text: str,
        output_text: str,
        agent_id: str,
        purpose: str = "",
    ) -> LLMCallRecord:
        """Record an LLM call by input/output text (estimates tokens)."""
        input_tok = estimate_tokens_for_text(input_text)
        output_tok = estimate_tokens_for_text(output_text)
        return self.record_tokens(input_tok, output_tok, agent_id, purpose)

    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        agent_id: str,
        purpose: str = "",
    ) -> LLMCallRecord:
        """Record an LLM call by token counts."""
        total = input_tokens + output_tokens
        cost = estimate_cost(input_tokens, output_tokens, self.pricing)
        record = LLMCallRecord(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost,
            agent_id=agent_id,
            purpose=purpose,
        )
        self.calls.append(record)
        return record

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def num_calls(self) -> int:
        return len(self.calls)

    def to_cost_report(self, mode: str, duration_ms: float = 0.0) -> CostReport:
        """Convert tracked calls into a CostReport."""
        return CostReport(
            mode=mode,
            total_tokens=self.total_tokens,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            estimated_cost_usd=self.total_cost,
            num_llm_calls=self.num_calls,
            num_steps=self.num_calls,
            duration_ms=duration_ms,
            details=[
                {
                    "agent": c.agent_id,
                    "purpose": c.purpose,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost_usd": c.cost_usd,
                }
                for c in self.calls
            ],
        )

    def reset(self) -> None:
        self.calls = []


# ─── Benchmark Runner ──────────────────────────────────────────────────────────

@dataclass
class BenchmarkTask:
    """
    Defines a task to benchmark: same logical work done two ways.

    The task provides:
      - agents_blackboard: Agent definitions for the blackboard approach
      - simulate_direct: A function that simulates direct messaging and records costs
      - goal: When the blackboard run is done
      - description: Human-readable task description
    """

    description: str
    agents: list[Agent]
    goal: Callable[[Any], bool]
    simulate_direct: Callable[[CostTracker], None]
    max_steps: int = 50


def run_benchmark(task: BenchmarkTask) -> BenchmarkResult:
    """
    Run a task both ways (direct messaging vs blackboard) and compare costs.

    Args:
        task: BenchmarkTask defining agents, goal, and direct-messaging simulation.

    Returns:
        BenchmarkResult with side-by-side cost comparison.
    """
    # ─── Run (a): Direct messaging simulation ───────────────────────────────
    direct_tracker = CostTracker()
    start_direct = time.perf_counter()
    task.simulate_direct(direct_tracker)
    direct_ms = (time.perf_counter() - start_direct) * 1000
    direct_report = direct_tracker.to_cost_report("direct", direct_ms)

    # ─── Run (b): Blackboard coordination ───────────────────────────────────
    board = InMemoryBlackboard(name="benchmark")
    # Reset agents for clean run
    for agent in task.agents:
        agent.reset()

    start_bb = time.perf_counter()
    orch = Orchestrator(board, task.agents, goal=task.goal, max_steps=task.max_steps)
    orch_result = orch.run()
    bb_ms = (time.perf_counter() - start_bb) * 1000

    # Tally blackboard costs from agent results
    bb_report = CostReport(
        mode="blackboard",
        total_tokens=orch_result.total_tokens,
        input_tokens=sum(
            s.metadata.get("input_tokens", 0) for s in orch_result.steps
        ),
        output_tokens=sum(
            s.metadata.get("output_tokens", 0) for s in orch_result.steps
        ),
        estimated_cost_usd=orch_result.total_cost_usd,
        num_llm_calls=sum(1 for s in orch_result.steps if s.tokens_used > 0),
        num_steps=len(orch_result.steps),
        duration_ms=bb_ms,
        details=[s.to_dict() for s in orch_result.steps],
    )

    # If input/output weren't tracked separately, derive from total
    if bb_report.input_tokens == 0 and bb_report.total_tokens > 0:
        # Assume 80% input, 20% output (typical ratio)
        bb_report.input_tokens = int(bb_report.total_tokens * 0.8)
        bb_report.output_tokens = bb_report.total_tokens - bb_report.input_tokens

    return BenchmarkResult(
        direct=direct_report,
        blackboard=bb_report,
        task_description=task.description,
    )
