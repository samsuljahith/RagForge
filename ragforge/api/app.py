"""
FastAPI application factory and main app instance.

The app is structured so it can be:
  - imported directly: `from ragforge.api import app`
  - started via CLI: `ragforge serve`
  - started via uvicorn: `uvicorn ragforge.api:app`
"""

from __future__ import annotations

from fastapi import FastAPI

from ragforge import __version__


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="RAGForge API",
        description=(
            "One workshop for building, evaluating, and optimizing RAG — "
            "usable from any language via this HTTP/JSON API."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Import and include routers
    from ragforge.api.routes import health, parse, chunk, capabilities
    from ragforge.api.routes import knowledge, query, evaluate, quantize, migrate
    from ragforge.api.routes import traces, ui_eval, ui_chat

    application.include_router(health.router)
    application.include_router(capabilities.router)
    application.include_router(parse.router)
    application.include_router(chunk.router)
    application.include_router(knowledge.router)
    application.include_router(query.router)
    application.include_router(evaluate.router)
    application.include_router(quantize.router)
    application.include_router(migrate.router)
    application.include_router(traces.router)
    application.include_router(ui_eval.router)
    application.include_router(ui_chat.router)

    return application


app = create_app()
