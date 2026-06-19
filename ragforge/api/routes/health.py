"""GET /health — basic liveness check with version info."""

from __future__ import annotations

from fastapi import APIRouter

from ragforge import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict:
    """
    Health check endpoint.

    Returns server status and version. Use this to verify the API is running
    and reachable from your agent (in any language).
    """
    return {
        "status": "healthy",
        "version": __version__,
        "service": "ragforge",
    }
