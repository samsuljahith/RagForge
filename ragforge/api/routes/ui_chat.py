"""UI chat route: chat with a knowledge base (with tracing)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ui/chat", tags=["ui-chat"])


class ChatRequest(BaseModel):
    """Request to chat with a knowledge base."""

    knowledge: str = Field(..., description="Knowledge base name")
    question: str = Field(..., description="The question to ask")
    top_k: int = Field(5, ge=1, le=50)
    mode: Literal["dense", "bm25", "hybrid"] = "hybrid"
    rerank: bool = False
    generate: bool = True
    llm: Optional[str] = Field(None, description="LLM provider (ollama/openai/anthropic)")


class ChatSource(BaseModel):
    """A source chunk in the chat response."""

    id: str
    text: str
    score: float
    section: str = ""
    source: str = ""


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    answer: Optional[str] = None
    sources: list[ChatSource]
    run_id: Optional[str] = None
    llm: Optional[str] = None
    mode: str
    knowledge: str
    question: str


@router.post("/message", response_model=ChatResponse)
def chat_message(req: ChatRequest) -> ChatResponse:
    """
    Chat with a knowledge base — retrieve + optionally generate answer.

    Always returns sources. If generate=True and llm is set, also returns
    a grounded answer. Each message creates a trace (linked via run_id)
    so the user can inspect what happened under the hood.
    """
    from ragforge.pipeline import KnowledgeBase

    try:
        kb = KnowledgeBase.load(req.knowledge)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Use traced versions for observability
    if req.generate and req.llm:
        try:
            result = kb.answer_traced(
                question=req.question,
                top_k=req.top_k,
                mode=req.mode,
                rerank=req.rerank,
                llm=req.llm,
            )
            sources = [
                ChatSource(
                    id=s["id"],
                    text=s["text"],
                    score=s["score"],
                    section=s["metadata"].get("section", ""),
                    source=s["metadata"].get("source", s.get("doc_id", "")),
                )
                for s in result["sources"]
            ]
            return ChatResponse(
                answer=result["answer"],
                sources=sources,
                run_id=result.get("run_id"),
                llm=result.get("llm_name"),
                mode=req.mode,
                knowledge=req.knowledge,
                question=req.question,
            )
        except (ImportError, ValueError, ConnectionError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
    else:
        # Retrieval-only (traced)
        try:
            results, run_id = kb.query_traced(
                question=req.question,
                top_k=req.top_k,
                mode=req.mode,
                rerank=req.rerank,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

        sources = [
            ChatSource(
                id=chunk.id,
                text=chunk.text,
                score=round(score, 4),
                section=chunk.metadata.get("section", ""),
                source=chunk.metadata.get("source", chunk.doc_id),
            )
            for chunk, score in results
        ]
        return ChatResponse(
            answer=None,
            sources=sources,
            run_id=run_id,
            llm=None,
            mode=req.mode,
            knowledge=req.knowledge,
            question=req.question,
        )
