"""
API endpoints for multi-agent coordination.

Endpoints:
  POST /coordination/boards           -> create a blackboard
  GET  /coordination/boards/{name}    -> get board state
  POST /coordination/boards/{name}/write -> write an entry
  GET  /coordination/boards/{name}/history -> get write history
  DELETE /coordination/boards/{name}  -> clear a board
  POST /coordination/run              -> run an orchestration task (inline agents)
  GET  /coordination/run/{run_id}     -> get a run's trace + cost summary
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/coordination", tags=["coordination"])

# ─── In-memory board store for API sessions ────────────────────────────────────
# (Persistent boards use the SQLite-backed Blackboard; this dict maps names to instances)
_boards: dict[str, Any] = {}
_runs: dict[str, Any] = {}
_run_counter = 0


def _get_or_create_board(name: str, persist: bool = False):
    """Get existing board or create a new one."""
    from ragforge.coordination import Blackboard, InMemoryBlackboard

    if name not in _boards:
        if persist:
            _boards[name] = Blackboard(name)
        else:
            _boards[name] = InMemoryBlackboard(name)
    return _boards[name]


# ─── Models ────────────────────────────────────────────────────────────────────

class CreateBoardRequest(BaseModel):
    name: str = Field(..., description="Blackboard name")
    persist: bool = Field(False, description="Persist to disk (SQLite) for crash recovery")


class WriteEntryRequest(BaseModel):
    key: str = Field(..., description="Entry key")
    value: Any = Field(..., description="Entry value (any JSON)")
    author: str = Field(..., description="Agent/author ID")
    tags: dict[str, Any] = Field(default_factory=dict, description="Markers/pheromones")


class EntryResponse(BaseModel):
    key: str
    value: Any
    author: str
    timestamp: str
    tags: dict[str, Any]
    version: int


class BoardStateResponse(BaseModel):
    name: str
    entries: list[EntryResponse]
    history_count: int


class RunAgentDef(BaseModel):
    """Inline agent definition for API-driven orchestration."""
    id: str = Field(..., description="Agent identifier")
    trigger_key: str = Field(..., description="Key this agent watches for")
    trigger_condition: str = Field(
        "exists",
        description="Condition: 'exists', 'tag:<key>=<value>', 'missing:<key>'",
    )
    output_key: str = Field(..., description="Key this agent writes to")
    output_value: Any = Field(None, description="Static value to write (for simple agents)")
    output_tags: dict[str, Any] = Field(default_factory=dict, description="Tags to apply to output")
    prompt: Optional[str] = Field(None, description="LLM prompt template (uses {input} placeholder)")
    max_fires: Optional[int] = Field(None, description="Max times this agent can fire")


class RunRequest(BaseModel):
    """Run a coordination task via the API."""
    board_name: str = Field("api-run", description="Board name for this run")
    agents: list[RunAgentDef] = Field(..., description="Agent definitions")
    seed: list[WriteEntryRequest] = Field(default_factory=list, description="Initial board entries")
    max_steps: int = Field(50, description="Maximum orchestration steps")
    goal_key: Optional[str] = Field(None, description="Key whose existence signals goal completion")


class RunResponse(BaseModel):
    run_id: str
    termination_reason: str
    num_steps: int
    total_tokens: int
    total_cost_usd: float
    duration_ms: float
    steps: list[dict[str, Any]]
    board_state: dict[str, Any]


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/boards", response_model=BoardStateResponse)
def create_board(req: CreateBoardRequest) -> BoardStateResponse:
    """Create a new blackboard (or return existing one)."""
    board = _get_or_create_board(req.name, persist=req.persist)
    return BoardStateResponse(
        name=board.name,
        entries=[],
        history_count=board.history_count(),
    )


@router.get("/boards/{name}", response_model=BoardStateResponse)
def get_board(name: str) -> BoardStateResponse:
    """Get current state of a blackboard."""
    if name not in _boards:
        raise HTTPException(status_code=404, detail=f"Board '{name}' not found")
    board = _boards[name]
    entries = [
        EntryResponse(
            key=e.key, value=e.value, author=e.author,
            timestamp=e.timestamp, tags=e.tags, version=e.version,
        )
        for e in board.read_all()
    ]
    return BoardStateResponse(
        name=board.name,
        entries=entries,
        history_count=board.history_count(),
    )


@router.post("/boards/{name}/write", response_model=EntryResponse)
def write_entry(name: str, req: WriteEntryRequest) -> EntryResponse:
    """Write an entry to a blackboard."""
    board = _get_or_create_board(name)
    entry = board.write(req.key, req.value, author=req.author, tags=req.tags)
    return EntryResponse(
        key=entry.key, value=entry.value, author=entry.author,
        timestamp=entry.timestamp, tags=entry.tags, version=entry.version,
    )


@router.get("/boards/{name}/history")
def get_history(name: str, key: Optional[str] = None, limit: int = 100) -> dict:
    """Get write history for a blackboard."""
    if name not in _boards:
        raise HTTPException(status_code=404, detail=f"Board '{name}' not found")
    board = _boards[name]
    history = board.history(key=key, limit=limit)
    return {
        "board": name,
        "history": [
            {
                "key": e.key, "value": e.value, "author": e.author,
                "timestamp": e.timestamp, "tags": e.tags, "version": e.version,
            }
            for e in history
        ],
        "count": len(history),
    }


@router.delete("/boards/{name}")
def clear_board(name: str) -> dict:
    """Clear all entries from a blackboard (history is preserved)."""
    if name not in _boards:
        raise HTTPException(status_code=404, detail=f"Board '{name}' not found")
    _boards[name].clear()
    return {"status": "cleared", "board": name}


@router.post("/run", response_model=RunResponse)
def run_coordination(req: RunRequest) -> RunResponse:
    """
    Run a multi-agent coordination task.

    Agents are defined inline in the request. Each agent watches for a trigger
    condition on the board and writes output when triggered. For simple tasks,
    use static output_value. For LLM-powered tasks, provide a prompt template.
    """
    from ragforge.coordination import InMemoryBlackboard
    from ragforge.coordination.agent import Agent, AgentResult, Orchestrator

    global _run_counter
    _run_counter += 1
    run_id = f"run-{_run_counter:04d}"

    board = InMemoryBlackboard(req.board_name)

    # Seed the board
    for entry in req.seed:
        board.write(entry.key, entry.value, author=entry.author, tags=entry.tags)

    # Build agents from definitions
    agents = []
    for agent_def in req.agents:
        agents.append(_build_api_agent(agent_def))

    # Goal condition
    goal = None
    if req.goal_key:
        goal_key = req.goal_key
        goal = lambda b, _k=goal_key: b.has_key(_k)

    # Run orchestration
    orch = Orchestrator(board, agents, goal=goal, max_steps=req.max_steps)
    result = orch.run()

    # Store run for later retrieval
    _runs[run_id] = result.to_dict()

    return RunResponse(
        run_id=run_id,
        termination_reason=result.termination_reason,
        num_steps=len(result.steps),
        total_tokens=result.total_tokens,
        total_cost_usd=result.total_cost_usd,
        duration_ms=result.total_duration_ms,
        steps=[s.to_dict() for s in result.steps],
        board_state=result.board_state or {},
    )


@router.get("/run/{run_id}")
def get_run(run_id: str) -> dict:
    """Get the trace and cost summary of a previous run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return _runs[run_id]


# ─── Agent Builder (from API definitions) ─────────────────────────────────────

def _build_api_agent(defn: RunAgentDef):
    """Convert an API agent definition to a real Agent instance."""
    from ragforge.coordination.agent import Agent, AgentResult

    def make_trigger(d: RunAgentDef):
        """Build trigger function from the definition."""
        def trigger(board) -> bool:
            if d.trigger_condition == "exists":
                return board.has_key(d.trigger_key)
            elif d.trigger_condition.startswith("missing:"):
                missing_key = d.trigger_condition.split(":", 1)[1]
                return board.has_key(d.trigger_key) and not board.has_key(missing_key)
            elif d.trigger_condition.startswith("tag:"):
                # tag:status=ready
                tag_expr = d.trigger_condition.split(":", 1)[1]
                tag_key, tag_val = tag_expr.split("=", 1)
                entries = board.read_by_tag(tag_key, lambda v: str(v) == tag_val)
                return len(entries) > 0
            return board.has_key(d.trigger_key)
        return trigger

    def make_action(d: RunAgentDef):
        """Build action function from the definition."""
        def action(board, agent_id: str) -> AgentResult:
            # Read the trigger entry
            entry = board.read(d.trigger_key)
            input_value = entry.value if entry else None

            # Determine output
            if d.output_value is not None:
                output = d.output_value
            elif d.prompt and input_value is not None:
                # Simple string interpolation (no real LLM call in API mode)
                output = d.prompt.replace("{input}", str(input_value))
            else:
                output = f"processed by {agent_id}"

            board.write(d.output_key, output, author=agent_id, tags=d.output_tags)
            return AgentResult(
                agent_id=agent_id,
                entries_read=[d.trigger_key],
                entries_written=[d.output_key],
            )
        return action

    return Agent(
        id=defn.id,
        trigger=make_trigger(defn),
        action=make_action(defn),
        max_fires=defn.max_fires,
    )
