"""UI evaluation routes: run evals and track history from the dashboard."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ui/eval", tags=["ui-evaluation"])

_EVAL_HISTORY_DIR = Path.home() / ".ragforge" / "eval_history"


class EvalRunRequest(BaseModel):
    """Request to run an evaluation from the UI."""

    knowledge: str
    golden_dataset: list[dict[str, Any]]
    metrics: list[str] = Field(default=["hit_rate", "precision_at_k", "recall_at_k", "mrr"])
    top_k: int = 5
    mode: Literal["dense", "bm25", "hybrid"] = "hybrid"
    rerank: bool = False
    generate: bool = False
    llm: Optional[str] = None


class EvalCompareRequest(BaseModel):
    """Request for A/B comparison."""

    knowledge_a: str
    knowledge_b: str
    golden_dataset: list[dict[str, Any]]
    metrics: list[str] = Field(default=["hit_rate", "mrr", "precision_at_k"])
    top_k: int = 5
    mode: Literal["dense", "bm25", "hybrid"] = "hybrid"
    rerank: bool = False


@router.post("/run")
def run_evaluation(req: EvalRunRequest) -> dict[str, Any]:
    """Run an evaluation and persist the result for history."""
    from ragforge.evaluation import evaluate_knowledge_base

    try:
        result = evaluate_knowledge_base(
            knowledge=req.knowledge,
            golden_dataset=req.golden_dataset,
            metrics=req.metrics,
            top_k=req.top_k,
            mode=req.mode,
            rerank=req.rerank,
            generate=req.generate,
            llm=req.llm,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

    # Persist to history
    _EVAL_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "result": result,
        "request": req.model_dump(),
    }
    history_file = _EVAL_HISTORY_DIR / f"{req.knowledge}_{int(time.time())}.json"
    history_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    return result


@router.post("/compare")
def run_comparison(req: EvalCompareRequest) -> dict[str, Any]:
    """Run A/B comparison between two KBs."""
    from ragforge.pipeline import KnowledgeBase
    from ragforge.evaluation import Evaluator, GoldenDataset

    try:
        kb_a = KnowledgeBase.load(req.knowledge_a)
        kb_b = KnowledgeBase.load(req.knowledge_b)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    golden = GoldenDataset.from_dicts(req.golden_dataset)

    comparison = Evaluator.compare(
        kb_a, kb_b, golden,
        metrics=req.metrics,
        top_k=req.top_k,
        mode=req.mode,
        rerank=req.rerank,
        label_a=req.knowledge_a,
        label_b=req.knowledge_b,
    )
    return comparison


@router.get("/history")
def get_eval_history(knowledge: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Get past evaluation runs."""
    if not _EVAL_HISTORY_DIR.exists():
        return []

    files = sorted(_EVAL_HISTORY_DIR.glob("*.json"), reverse=True)
    if knowledge:
        files = [f for f in files if f.name.startswith(knowledge)]

    results = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except Exception:
            continue
    return results
