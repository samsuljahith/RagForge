"""
RAGForge HTTP/JSON API — the language-agnostic gateway.

This is what makes RAGForge usable from ANY language. Agents written in Python,
JavaScript, Go, C++, or anything else connect over plain HTTP/JSON. FastAPI
auto-generates interactive docs at /docs (Swagger) and /redoc.

Start the server:
    ragforge serve            # CLI
    uvicorn ragforge.api:app  # direct

All endpoints accept and return JSON with Pydantic validation and clear error messages.
"""

from ragforge.api.app import app, create_app

__all__ = ["app", "create_app"]
