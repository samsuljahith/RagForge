"""
RAGForge command-line interface.

This is what makes RAGForge feel like ONE tool: a single `ragforge` command with
subcommands for each capability.

Usage:
    ragforge info
    ragforge parse path/to/file.md
    ragforge chunk path/to/file.md --strategy structure --max-tokens 384
    ragforge knowledge build my-kb docs/ --strategy structure --embedder default
    ragforge query my-kb "How do refunds work?" --mode hybrid --rerank
    ragforge serve --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys

from ragforge import __version__
from ragforge.core import available, registered_info
from ragforge.parsing import parse_file
from ragforge.chunking import chunk_document


def _cmd_info(args: argparse.Namespace) -> int:
    """Show registered components and module status."""
    print(f"RAGForge v{__version__}")
    print()
    info = registered_info()
    for kind, names in info.items():
        print(f"  {kind:12s}: {', '.join(names)}")
    print()
    print("Modules:")
    print("  core          ✓  shared data models + plugin registry")
    print("  parsing       ✓  txt / md / html / pdf -> Document")
    print("  chunking      ✓  fixed + structure-aware -> Chunks")
    print("  pipeline      ✓  embed + store + hybrid search + rerank")
    print("  evaluation    ✓  precision / recall / faithfulness")
    print("  quantization  ✓  quantize + compare cost/quality")
    print("  migration     ✓  re-embed + validate + swap models")
    print("  api           ✓  HTTP/JSON API (ragforge serve)")
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    """Parse a file into clean text."""
    doc = parse_file(args.path)
    if args.json:
        print(json.dumps(doc.to_dict(), indent=2))
    else:
        print(f"Parsed: {doc.source}")
        print(f"Type   : {doc.doc_type}")
        print(f"Tokens : ~{doc.token_count}")
        print("-" * 50)
        preview = doc.text[: args.preview]
        print(preview + ("…" if len(doc.text) > args.preview else ""))
    return 0


def _cmd_chunk(args: argparse.Namespace) -> int:
    """Parse then chunk a file."""
    doc = parse_file(args.path)
    kwargs = {}
    if args.strategy == "structure" and args.max_tokens:
        kwargs["max_tokens"] = args.max_tokens
    if args.strategy == "fixed" and args.max_tokens:
        kwargs["chunk_tokens"] = args.max_tokens
    chunks = chunk_document(doc, strategy=args.strategy, **kwargs)

    if args.json:
        print(json.dumps([c.to_dict() for c in chunks], indent=2))
        return 0

    print(f"Document: {doc.source}  (~{doc.token_count} tokens)")
    print(f"Strategy: {args.strategy}  ->  {len(chunks)} chunks\n")
    for c in chunks:
        section = c.metadata.get("section", "")
        tag = "  [oversized]" if c.metadata.get("oversized") else ""
        head = f"[chunk {c.index}] ~{c.token_count} tok"
        head += f"  | section: {section}" if section else ""
        head += tag
        print(head)
        if args.show_text:
            print("    " + c.text[:200].replace("\n", "\n    "))
            print()
    return 0


def _cmd_knowledge_build(args: argparse.Namespace) -> int:
    """Build a knowledge base from source files."""
    from ragforge.pipeline import build_knowledge_base

    result = build_knowledge_base(
        name=args.name,
        sources=args.sources,
        embedding_model=args.embedder,
        chunk_strategy=args.strategy,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Knowledge base '{result['name']}' built successfully.")
        print(f"  Documents: {result['num_documents']}")
        print(f"  Chunks   : {result['num_chunks']}")
        print(f"  Embedder : {result['embedding_model']}")
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    """Query a knowledge base."""
    from ragforge.pipeline import query_knowledge_base

    llm_opts = {}
    if hasattr(args, "model") and args.model:
        llm_opts["model"] = args.model

    result = query_knowledge_base(
        knowledge=args.knowledge,
        question=args.question,
        top_k=args.k,
        mode=args.mode,
        rerank=args.rerank,
        generate=args.generate,
        llm=args.llm,
        llm_opts=llm_opts if llm_opts else None,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query: {result['question']}")
        print(f"Knowledge base: {result['knowledge']}")
        print(f"Mode: {args.mode}  |  Rerank: {args.rerank}")

        # Print generated answer if present
        if result.get("answer"):
            print(f"\n{'─' * 60}")
            print(f"Answer (via {result.get('llm', 'unknown')}):")
            print(f"{'─' * 60}")
            print(result["answer"])
            print(f"{'─' * 60}")
            print(f"\nSources ({len(result['chunks'])} chunks):\n")
        else:
            print(f"Results: {len(result['chunks'])} chunks\n")

        for c in result["chunks"]:
            section = c["metadata"].get("section", "")
            head = f"  [{c['index']}] score={c['score']:.4f}"
            head += f"  | {section}" if section else ""
            print(head)
            print(f"      {c['text'][:120]}...")
            print()
    return 0


def _cmd_eval_run(args: argparse.Namespace) -> int:
    """Run evaluation against a golden dataset."""
    from ragforge.pipeline import KnowledgeBase
    from ragforge.evaluation import Evaluator, GoldenDataset

    kb = KnowledgeBase.load(args.knowledge)
    golden = GoldenDataset.load(args.golden)

    metrics = args.metrics.split(",") if args.metrics else None

    evaluator = Evaluator(kb)
    report = evaluator.run(
        golden,
        metrics=metrics,
        top_k=args.k,
        mode=args.mode,
        rerank=args.rerank,
        generate=args.generate,
        llm=args.llm,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        report.print_table()
    return 0


def _cmd_eval_compare(args: argparse.Namespace) -> int:
    """A/B compare two KBs on the same golden set."""
    from ragforge.pipeline import KnowledgeBase
    from ragforge.evaluation import Evaluator, GoldenDataset

    kb_a = KnowledgeBase.load(args.knowledge_a)
    kb_b = KnowledgeBase.load(args.knowledge_b)
    golden = GoldenDataset.load(args.golden)

    metrics = args.metrics.split(",") if args.metrics else None

    comparison = Evaluator.compare(
        kb_a, kb_b, golden,
        metrics=metrics,
        top_k=args.k,
        mode=args.mode,
        rerank=args.rerank,
        label_a=args.knowledge_a,
        label_b=args.knowledge_b,
    )

    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        Evaluator.print_comparison(comparison)
    return 0


def _cmd_eval_bootstrap(args: argparse.Namespace) -> int:
    """Generate a draft golden dataset from an existing KB."""
    from ragforge.evaluation import generate_golden_draft

    print(f"Generating draft golden dataset from '{args.knowledge}'...")
    golden = generate_golden_draft(
        knowledge=args.knowledge,
        num_items=args.n,
        llm=args.llm,
    )
    golden.save(args.out)
    print(f"Saved {len(golden)} items to {args.out}")
    print("NOTE: This is a DRAFT. Review and correct before using as ground truth.")
    return 0


def _cmd_ui(args: argparse.Namespace) -> int:
    """Launch the local web dashboard (tracing, evaluation, chat)."""
    try:
        import uvicorn
    except ImportError:
        print(
            "Error: UI dependencies not installed.\n"
            "Install with:  pip install ragforge[ui]",
            file=sys.stderr,
        )
        return 1

    from pathlib import Path

    # Check if static files exist
    static_dir = Path(__file__).parent / "ui_static"
    if not static_dir.exists() or not (static_dir / "index.html").exists():
        print(
            "UI static files not found. Building frontend...",
            file=sys.stderr,
        )
        ui_src = Path(__file__).parent.parent / "ui"
        if ui_src.exists() and (ui_src / "package.json").exists():
            import subprocess
            try:
                subprocess.run(["npm", "install"], cwd=str(ui_src), check=True, capture_output=True)
                subprocess.run(["npm", "run", "build"], cwd=str(ui_src), check=True, capture_output=True)
                print("Frontend built successfully.", file=sys.stderr)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"Failed to build frontend: {e}", file=sys.stderr)
                print("Run 'cd ui && npm install && npm run build' manually.", file=sys.stderr)
                return 1
        else:
            print(
                "Error: ui/ source directory not found.\n"
                "The UI must be pre-built to ragforge/ui_static/.",
                file=sys.stderr,
            )
            return 1

    # Mount static files in the FastAPI app
    from ragforge.api.app import app
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/ui/{path:path}")
    async def serve_ui(path: str):
        """Serve the SPA — all non-API routes go to index.html."""
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/ui")
    async def serve_ui_root():
        return FileResponse(str(static_dir / "index.html"))

    # Mount assets
    if (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="ui-assets")

    url = f"http://{args.host}:{args.port}/ui"
    print(f"RAGForge UI v{__version__}")
    print(f"Dashboard: {url}")
    print(f"API docs:  http://{args.host}:{args.port}/docs")

    if not args.no_browser:
        import webbrowser
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the HTTP/JSON API server."""
    try:
        import uvicorn
    except ImportError:
        print(
            "Error: API dependencies not installed.\n"
            "Install with:  pip install ragforge[api]",
            file=sys.stderr,
        )
        return 1

    print(f"RAGForge API v{__version__}")
    print(f"Starting server on {args.host}:{args.port}")
    print(f"Interactive docs: http://{args.host}:{args.port}/docs")
    uvicorn.run("ragforge.api:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ragforge",
        description="Build, evaluate, and optimize RAG — all in one place.",
    )
    p.add_argument("--version", action="version", version=f"RAGForge {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # --- info ---
    sp = sub.add_parser("info", help="show registered components and module status")
    sp.set_defaults(func=_cmd_info)

    # --- parse ---
    sp = sub.add_parser("parse", help="parse a file into clean text")
    sp.add_argument("path", help="file to parse (.txt .md .html .pdf)")
    sp.add_argument("--preview", type=int, default=500, help="characters of text to show")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_parse)

    # --- chunk ---
    sp = sub.add_parser("chunk", help="parse then chunk a file")
    sp.add_argument("path", help="file to chunk")
    sp.add_argument("--strategy", choices=["fixed", "structure"], default="structure")
    sp.add_argument("--max-tokens", type=int, default=None, help="target chunk size in tokens")
    sp.add_argument("--show-text", action="store_true", help="print each chunk's text")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_chunk)

    # --- knowledge ---
    kb_parser = sub.add_parser("knowledge", help="build knowledge bases")
    kb_sub = kb_parser.add_subparsers(dest="kb_command", required=True)

    # knowledge build
    sp = kb_sub.add_parser("build", help="build a knowledge base from files")
    sp.add_argument("name", help="name for the knowledge base")
    sp.add_argument("sources", nargs="+", help="files or directories to index")
    sp.add_argument("--strategy", choices=["fixed", "structure"], default="structure")
    sp.add_argument(
        "--embedder",
        default="default",
        help="embedder to use: 'default', 'sentence-transformers', 'openai'",
    )
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_knowledge_build)

    # --- query (top-level command) ---
    sp = sub.add_parser("query", help="query a knowledge base")
    sp.add_argument("knowledge", help="knowledge base name")
    sp.add_argument("question", help="question to ask")
    sp.add_argument("-k", type=int, default=5, help="number of results (default: 5)")
    sp.add_argument(
        "--mode",
        choices=["dense", "bm25", "hybrid"],
        default="hybrid",
        help="retrieval mode (default: hybrid)",
    )
    sp.add_argument("--rerank", action="store_true", help="apply cross-encoder reranking")
    sp.add_argument(
        "--generate",
        action="store_true",
        help="generate a grounded answer using an LLM (requires --llm)",
    )
    sp.add_argument(
        "--llm",
        default=None,
        help="LLM provider for answer generation: 'openai', 'anthropic', 'ollama'",
    )
    sp.add_argument(
        "--model",
        default=None,
        help="override the default model for the LLM provider",
    )
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_query)

    # --- eval ---
    eval_parser = sub.add_parser("eval", help="evaluate RAG quality")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", required=True)

    # eval run
    sp = eval_sub.add_parser("run", help="evaluate a KB against a golden dataset")
    sp.add_argument("knowledge", help="knowledge base name")
    sp.add_argument("golden", help="path to golden dataset (JSON or CSV)")
    sp.add_argument("-k", type=int, default=5, help="top-k for retrieval (default: 5)")
    sp.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="hybrid")
    sp.add_argument("--rerank", action="store_true", help="apply reranking")
    sp.add_argument("--generate", action="store_true", help="generate answers (for judge metrics)")
    sp.add_argument("--llm", default=None, help="LLM provider for generation + judge")
    sp.add_argument(
        "--metrics",
        default=None,
        help="comma-separated metrics (default: all retrieval metrics)",
    )
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_eval_run)

    # eval compare
    sp = eval_sub.add_parser("compare", help="A/B compare two configs on same golden set")
    sp.add_argument("knowledge_a", help="first knowledge base name")
    sp.add_argument("knowledge_b", help="second knowledge base name")
    sp.add_argument("golden", help="path to golden dataset (JSON or CSV)")
    sp.add_argument("-k", type=int, default=5, help="top-k for retrieval")
    sp.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="hybrid")
    sp.add_argument("--rerank", action="store_true")
    sp.add_argument("--metrics", default=None, help="comma-separated metrics")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_eval_compare)

    # eval bootstrap
    sp = eval_sub.add_parser("bootstrap", help="generate a draft golden dataset from a KB")
    sp.add_argument("knowledge", help="knowledge base to generate from")
    sp.add_argument("--out", default="golden_draft.json", help="output file path")
    sp.add_argument("-n", type=int, default=10, help="number of items to generate")
    sp.add_argument("--llm", default="ollama", help="LLM provider for generation")
    sp.set_defaults(func=_cmd_eval_bootstrap)

    # --- serve ---
    sp = sub.add_parser("serve", help="start the HTTP/JSON API server")
    sp.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    sp.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    sp.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev mode)")
    sp.set_defaults(func=_cmd_serve)

    # --- ui ---
    sp = sub.add_parser("ui", help="launch the local web dashboard (traces, eval, chat)")
    sp.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    sp.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    sp.add_argument("--no-browser", action="store_true", help="don't auto-open the browser")
    sp.set_defaults(func=_cmd_ui)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, ImportError, ConnectionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
