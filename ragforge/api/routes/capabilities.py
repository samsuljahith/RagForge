"""GET /capabilities — list all registered parsers, chunkers, etc."""

from __future__ import annotations

from fastapi import APIRouter

from ragforge.core.registry import registered_info

router = APIRouter(tags=["system"])


@router.get("/capabilities")
def list_capabilities() -> dict:
    """
    List all registered capabilities.

    Returns which parsers, chunkers, and other plugins are available on this
    server. Useful for agents to discover what operations they can request.
    """
    return {
        "capabilities": registered_info(),
    }
