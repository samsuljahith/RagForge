#!/usr/bin/env python3
"""
Example: Multi-Agent Coordination via Blackboard (with Cost Benchmark)

This demonstrates RAGForge's coordination module with a realistic 3-agent task:

  1. RESEARCHER — reads the question, "searches" for information, writes findings
     to the blackboard with a confidence score.
  2. CRITIC — reads findings, checks confidence. If low, marks "needs_review".
     If high, marks "approved".
  3. WRITER — reads approved findings and writes a final answer.

Agents NEVER call each other directly. They only read/write the shared blackboard.
The orchestrator runs them until the "final_answer" key appears (goal met).

Then we run the same task as a direct-messaging simulation (where each agent
re-sends the full conversation history) and PRINT THE TOKEN SAVINGS.

No API keys needed — uses a mock LLM that simulates token costs realistically.

Usage:
    python examples/multi_agent_coordination.py

    # Or via CLI (as a config file):
    ragforge agents benchmark examples/multi_agent_coordination.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, ".")

from ragforge.coordination.blackboard import InMemoryBlackboard
from ragforge.coordination.agent import Agent, AgentResult, Orchestrator
from ragforge.coordination.benchmark import (
    BenchmarkTask,
    CostTracker,
    run_benchmark,
    estimate_tokens_for_text,
    estimate_cost,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATED CONTEXT (what a real task would look like)
# ═══════════════════════════════════════════════════════════════════════════════

QUESTION = "What is RAGForge's approach to multi-agent coordination, and why is it cheaper than direct messaging?"

# Simulated "research findings" (what a real KB query + LLM would produce)
RESEARCH_FINDINGS = (
    "RAGForge uses a blackboard-based coordination pattern (stigmergy). Instead of agents "
    "sending messages directly to each other — which requires re-sending the full conversation "
    "context with each handoff — agents read and write a shared workspace. Each agent only reads "
    "the specific entries it needs. This reduces token usage because: (1) no full-context "
    "re-sends between agents, (2) targeted reads instead of full history, (3) the orchestrator "
    "itself uses zero tokens (it's a simple loop, not an LLM-powered router). The blackboard "
    "also persists to SQLite, providing crash recovery that direct messaging lacks."
)

REVIEW_NOTE = "Findings are factual and well-sourced. Confidence is high. Approved."

FINAL_ANSWER = (
    "RAGForge coordinates multiple agents through a shared blackboard rather than direct "
    "messaging. Agents leave signals (like confidence scores and status markers) on the "
    "board, and other agents react to those signals — this is called stigmergy. The key "
    "cost advantage: in direct messaging, every agent handoff re-sends the full conversation "
    "to the LLM (growing context = growing cost). With the blackboard, each agent reads only "
    "the specific entries it needs. The orchestrator is a simple deterministic loop that "
    "uses zero tokens. Typical savings: 40-70% fewer tokens on multi-step tasks."
)


# ═══════════════════════════════════════════════════════════════════════════════
# BLACKBOARD AGENTS (the cheap way)
# ═══════════════════════════════════════════════════════════════════════════════

def researcher_trigger(board) -> bool:
    """Fire when there's a question but no findings yet."""
    return board.has_key("question") and not board.has_key("findings")


def researcher_action(board, agent_id: str) -> AgentResult:
    """
    Read the question, 'search' for info (simulated KB query + LLM),
    write findings with confidence score.
    """
    question = board.read("question")

    # Simulate: KB retrieval + LLM summarization
    # In a real system, this would call KnowledgeBase.query() + LLMProvider.generate()
    # Token cost: ~question (input) + ~findings (output)
    input_tokens = estimate_tokens_for_text(question.value + " [system prompt + retrieved chunks]" * 3)
    output_tokens = estimate_tokens_for_text(RESEARCH_FINDINGS)

    board.write(
        "findings",
        RESEARCH_FINDINGS,
        author=agent_id,
        tags={"confidence": 0.85, "status": "pending_review", "source": "knowledge_base"},
    )

    return AgentResult(
        agent_id=agent_id,
        entries_read=["question"],
        entries_written=["findings"],
        tokens_used=input_tokens + output_tokens,
        cost_usd=estimate_cost(input_tokens, output_tokens),
        metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


def critic_trigger(board) -> bool:
    """Fire when findings exist with status=pending_review."""
    entries = board.read_by_tag("status", lambda v: v == "pending_review")
    return len(entries) > 0 and not board.has_key("review")


def critic_action(board, agent_id: str) -> AgentResult:
    """
    Read findings, assess quality. If confidence > 0.7, approve.
    Otherwise mark for revision.
    """
    findings = board.read("findings")

    # Simulate: LLM-as-judge call (shorter prompt — just the findings, not full history)
    input_tokens = estimate_tokens_for_text(findings.value + " [judge prompt]")
    output_tokens = estimate_tokens_for_text(REVIEW_NOTE)

    # Check confidence from tags
    confidence = findings.tags.get("confidence", 0.5)

    if confidence > 0.7:
        board.write(
            "review",
            REVIEW_NOTE,
            author=agent_id,
            tags={"status": "approved", "confidence": confidence},
        )
        # Update findings status
        board.write(
            "findings",
            findings.value,
            author=findings.author,
            tags={**findings.tags, "status": "approved"},
        )
    else:
        board.write(
            "review",
            "Confidence too low. Needs more research.",
            author=agent_id,
            tags={"status": "needs_revision"},
        )

    return AgentResult(
        agent_id=agent_id,
        entries_read=["findings"],
        entries_written=["review", "findings"],
        tokens_used=input_tokens + output_tokens,
        cost_usd=estimate_cost(input_tokens, output_tokens),
        metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


def writer_trigger(board) -> bool:
    """Fire when findings are approved and no final answer yet."""
    review = board.read("review")
    return (
        review is not None
        and review.tags.get("status") == "approved"
        and not board.has_key("final_answer")
    )


def writer_action(board, agent_id: str) -> AgentResult:
    """
    Read approved findings + review, synthesize final answer.
    Only reads what's needed — not the full conversation history.
    """
    findings = board.read("findings")
    review = board.read("review")
    question = board.read("question")

    # Simulate: LLM generation with targeted context (question + findings + review)
    context = f"{question.value}\n{findings.value}\n{review.value}"
    input_tokens = estimate_tokens_for_text(context + " [write a final answer]")
    output_tokens = estimate_tokens_for_text(FINAL_ANSWER)

    board.write(
        "final_answer",
        FINAL_ANSWER,
        author=agent_id,
        tags={"status": "complete", "confidence": 0.9},
    )

    return AgentResult(
        agent_id=agent_id,
        entries_read=["question", "findings", "review"],
        entries_written=["final_answer"],
        tokens_used=input_tokens + output_tokens,
        cost_usd=estimate_cost(input_tokens, output_tokens),
        metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECT MESSAGING SIMULATION (the expensive way)
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_direct_messaging(tracker: CostTracker) -> None:
    """
    Simulate the same 3-agent task using direct messaging.

    In direct messaging, each agent handoff re-sends the FULL conversation
    history to the next agent's LLM call. Context grows with each step.
    """
    system_prompt = "[system: you are a helpful research assistant]"

    # Step 1: Researcher gets the question
    # Input: system prompt + question
    researcher_input = f"{system_prompt}\n\nQuestion: {QUESTION}"
    researcher_output = RESEARCH_FINDINGS
    tracker.record_call(researcher_input, researcher_output, agent_id="researcher",
                        purpose="initial research (question → findings)")

    # Step 2: Critic gets the FULL conversation so far (question + findings)
    # This is where direct messaging gets expensive — full context re-send
    critic_input = (
        f"{system_prompt}\n\n"
        f"Question: {QUESTION}\n\n"
        f"Researcher's findings:\n{RESEARCH_FINDINGS}\n\n"
        f"Please review these findings for accuracy and completeness."
    )
    critic_output = REVIEW_NOTE
    tracker.record_call(critic_input, critic_output, agent_id="critic",
                        purpose="review (full context re-sent: question + findings)")

    # Step 3: Writer gets the FULL conversation (question + findings + review)
    # Even more context re-sent — this is the cost multiplier
    writer_input = (
        f"{system_prompt}\n\n"
        f"Question: {QUESTION}\n\n"
        f"Research findings:\n{RESEARCH_FINDINGS}\n\n"
        f"Critic's review:\n{REVIEW_NOTE}\n\n"
        f"Based on all of the above, write a clear, concise final answer."
    )
    writer_output = FINAL_ANSWER
    tracker.record_call(writer_input, writer_output, agent_id="writer",
                        purpose="final answer (full context re-sent: question + findings + review)")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK TASK (used by `ragforge agents benchmark`)
# ═══════════════════════════════════════════════════════════════════════════════

# These are exported so the CLI can pick them up
agents = [
    Agent(id="researcher", trigger=researcher_trigger, action=researcher_action, max_fires=1),
    Agent(id="critic", trigger=critic_trigger, action=critic_action, max_fires=1),
    Agent(id="writer", trigger=writer_trigger, action=writer_action, max_fires=1),
]

goal = lambda b: b.has_key("final_answer")
description = "Research → Review → Write (3-agent coordination)"
max_steps = 10

# For `ragforge agents run` — seed the board with the question
seed = [{"key": "question", "value": QUESTION, "author": "user"}]

# For `ragforge agents benchmark`
simulate_direct = simulate_direct_messaging

# Full BenchmarkTask object
benchmark_task = BenchmarkTask(
    description=description,
    agents=agents,
    goal=goal,
    simulate_direct=simulate_direct,
    max_steps=max_steps,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — run both approaches and print comparison
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 70)
    print("  RAGForge Multi-Agent Coordination: Cost Benchmark")
    print("=" * 70)
    print()
    print(f"  Task: {description}")
    print(f"  Question: {QUESTION[:60]}...")
    print(f"  Agents: researcher → critic → writer")
    print(f"  Goal: 'final_answer' key appears on the blackboard")
    print()

    # ─── Run the blackboard approach (to show the timeline) ─────────────────
    print("─" * 70)
    print("  BLACKBOARD APPROACH (agents read/write shared board)")
    print("─" * 70)

    board = InMemoryBlackboard("demo")
    board.write("question", QUESTION, author="user")

    # Reset agents for this run
    demo_agents = [
        Agent(id="researcher", trigger=researcher_trigger, action=researcher_action, max_fires=1),
        Agent(id="critic", trigger=critic_trigger, action=critic_action, max_fires=1),
        Agent(id="writer", trigger=writer_trigger, action=writer_action, max_fires=1),
    ]

    orch = Orchestrator(board, demo_agents, goal=goal, max_steps=10)
    result = orch.run()

    print(f"\n  Termination: {result.termination_reason}")
    print(f"  Steps: {len(result.steps)}")
    print()
    for i, step in enumerate(result.steps):
        print(f"    [{i+1}] {step.agent_id}")
        print(f"        Read:  {step.entries_read}")
        print(f"        Wrote: {step.entries_written}")
        print(f"        Tokens: {step.tokens_used}  |  Cost: ${step.cost_usd:.4f}")
        print()

    print(f"  Board state: {board.keys()}")
    print(f"  Total tokens: {result.total_tokens:,}")
    print(f"  Total cost:   ${result.total_cost_usd:.4f}")
    print()

    # ─── Final answer ───────────────────────────────────────────────────────
    answer = board.read("final_answer")
    print("─" * 70)
    print("  FINAL ANSWER (from blackboard)")
    print("─" * 70)
    print(f"\n  {answer.value[:200]}...")
    print()

    # ─── Run the benchmark ──────────────────────────────────────────────────
    # Need fresh agents for benchmark
    benchmark_task_fresh = BenchmarkTask(
        description=description,
        agents=[
            Agent(id="researcher", trigger=researcher_trigger, action=researcher_action, max_fires=1),
            Agent(id="critic", trigger=critic_trigger, action=critic_action, max_fires=1),
            Agent(id="writer", trigger=writer_trigger, action=writer_action, max_fires=1),
        ],
        goal=goal,
        simulate_direct=simulate_direct,
        max_steps=10,
    )

    # Patch: seed the board in the benchmark run
    original_run = run_benchmark.__wrapped__ if hasattr(run_benchmark, '__wrapped__') else None

    # We need to seed the benchmark board — let's monkey-patch the agents to self-seed
    def seeder_trigger(b):
        return not b.has_key("question")

    def seeder_action(b, aid):
        b.write("question", QUESTION, author="user")
        return AgentResult(agent_id=aid, entries_read=[], entries_written=["question"])

    benchmark_task_fresh.agents.insert(0, Agent(id="seeder", trigger=seeder_trigger, action=seeder_action, max_fires=1))

    bench_result = run_benchmark(benchmark_task_fresh)
    print(bench_result.summary())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
