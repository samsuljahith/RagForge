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
    print("  coordination  ✓  multi-agent blackboard + cost benchmark")
    print("  api           ✓  HTTP/JSON API (ragforge serve)")
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    """Parse a file into clean text."""
    if args.parser:
        # Use a specific parser backend by name (e.g. "docling")
        from ragforge.core.registry import get

        parser_cls = get("parser", args.parser)
        parser_instance = parser_cls()
        doc = parser_instance.parse(args.path)
    else:
        doc = parse_file(args.path)

    if args.json:
        # Remove non-serializable _docling_doc from JSON output
        doc_dict = doc.to_dict()
        doc_dict.get("metadata", {}).pop("_docling_doc", None)
        print(json.dumps(doc_dict, indent=2))
    else:
        print(f"Parsed: {doc.source}")
        print(f"Type   : {doc.doc_type}")
        print(f"Tokens : ~{doc.token_count}")
        if doc.metadata.get("parser"):
            print(f"Parser : {doc.metadata['parser']}")
        print("-" * 50)
        preview = doc.text[: args.preview]
        print(preview + ("…" if len(doc.text) > args.preview else ""))
    return 0


def _cmd_chunk(args: argparse.Namespace) -> int:
    """Parse then chunk a file."""
    if args.parser:
        from ragforge.core.registry import get

        parser_cls = get("parser", args.parser)
        doc = parser_cls().parse(args.path)
    else:
        doc = parse_file(args.path)

    kwargs = {}
    if args.strategy == "structure" and args.max_tokens:
        kwargs["max_tokens"] = args.max_tokens
    if args.strategy == "fixed" and args.max_tokens:
        kwargs["chunk_tokens"] = args.max_tokens
    if args.strategy == "docling" and args.max_tokens:
        kwargs["max_tokens"] = args.max_tokens
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


def _cmd_agents_run(args: argparse.Namespace) -> int:
    """Run a multi-agent task from a config file."""
    from ragforge.coordination import Blackboard, InMemoryBlackboard
    from ragforge.coordination.agent import Orchestrator
    from pathlib import Path
    import importlib.util

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    # Load the config module (a Python file that defines agents, goal, etc.)
    spec = importlib.util.spec_from_file_location("agent_config", str(config_path))
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    # The config module must define: agents (list), and optionally: goal, max_steps, board_name
    if not hasattr(config_mod, "agents"):
        print("Error: Config must define 'agents' (a list of Agent instances).", file=sys.stderr)
        return 1

    agents = config_mod.agents
    goal = getattr(config_mod, "goal", None)
    max_steps = getattr(config_mod, "max_steps", args.max_steps)
    board_name = getattr(config_mod, "board_name", "cli-run")

    # Create board (persistent or in-memory)
    if args.persist:
        board = Blackboard(board_name)
    else:
        board = InMemoryBlackboard(board_name)

    # Seed the board if config provides initial entries
    if hasattr(config_mod, "seed"):
        for entry in config_mod.seed:
            board.write(entry["key"], entry["value"], author=entry.get("author", "seed"),
                        tags=entry.get("tags", {}))

    # Run orchestration
    orch = Orchestrator(board, agents, goal=goal, max_steps=max_steps)
    result = orch.run()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Coordination run complete.")
        print(f"  Steps:       {len(result.steps)}")
        print(f"  Tokens:      {result.total_tokens:,}")
        print(f"  Cost:        ${result.total_cost_usd:.4f}")
        print(f"  Terminated:  {result.termination_reason}")
        print(f"  Duration:    {result.total_duration_ms:.0f}ms")
        if result.steps:
            print(f"\n  Agent timeline:")
            for i, step in enumerate(result.steps):
                tok = f" ({step.tokens_used} tok)" if step.tokens_used else ""
                print(f"    [{i}] {step.agent_id}: wrote {step.entries_written}{tok}")
        print(f"\n  Board keys: {list(board.keys())}")

    if not isinstance(board, InMemoryBlackboard):
        board.close()
    return 0


def _cmd_agents_benchmark(args: argparse.Namespace) -> int:
    """Run a direct-vs-blackboard cost comparison from a config file."""
    from ragforge.coordination.benchmark import run_benchmark, BenchmarkTask
    from pathlib import Path
    import importlib.util

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    # Load the config module (must define a BenchmarkTask or the pieces to build one)
    spec = importlib.util.spec_from_file_location("benchmark_config", str(config_path))
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    # Config can provide either a full BenchmarkTask or the pieces
    if hasattr(config_mod, "benchmark_task"):
        task = config_mod.benchmark_task
    elif hasattr(config_mod, "agents") and hasattr(config_mod, "simulate_direct"):
        task = BenchmarkTask(
            description=getattr(config_mod, "description", "CLI benchmark"),
            agents=config_mod.agents,
            goal=getattr(config_mod, "goal", lambda b: False),
            simulate_direct=config_mod.simulate_direct,
            max_steps=getattr(config_mod, "max_steps", args.max_steps),
        )
    else:
        print(
            "Error: Config must define either 'benchmark_task' (a BenchmarkTask) or "
            "both 'agents' and 'simulate_direct'.",
            file=sys.stderr,
        )
        return 1

    result = run_benchmark(task)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())
    return 0


def _cmd_agents_board(args: argparse.Namespace) -> int:
    """Inspect a blackboard's current state."""
    from ragforge.coordination import Blackboard

    board = Blackboard(args.name)
    entries = board.read_all()

    if args.json:
        print(json.dumps(board.to_dict(), indent=2))
    else:
        print(f"Blackboard: {args.name}")
        print(f"Entries: {len(entries)}  |  History: {board.history_count()} writes")
        print()
        if entries:
            for e in entries:
                tags_str = f"  tags={e.tags}" if e.tags else ""
                val_preview = str(e.value)[:80]
                print(f"  [{e.key}] v{e.version} by {e.author}{tags_str}")
                print(f"    {val_preview}")
                print()
        else:
            print("  (empty)")

    board.close()
    return 0


def _cmd_migrate_gate(args: argparse.Namespace) -> int:
    """Run the migration decision gate (compare old vs new model on golden set)."""
    from ragforge.migration.gate import run_decision_gate
    from ragforge.migration.migrator import _get_embedder
    from ragforge.pipeline.knowledge import KnowledgeBase
    from ragforge.evaluation.golden import GoldenDataset

    kb = KnowledgeBase.load(args.knowledge)
    golden = GoldenDataset.load(args.golden)
    old_embedder = _get_embedder(args.old)
    new_embedder = _get_embedder(args.new)

    decision = run_decision_gate(
        chunks=kb.store.chunks if hasattr(kb, 'store') else [],
        old_embedder=old_embedder,
        new_embedder=new_embedder,
        golden=golden,
        primary_metric=args.metric,
        threshold_margin=args.margin,
        top_k=args.k,
        hot_set_only=not args.full_corpus,
    )

    if args.json:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        decision.print_table()
    return 0 if decision.recommendation == "GO" else 1


def _cmd_migrate_run(args: argparse.Namespace) -> int:
    """Run a migration (optionally gated)."""
    if args.gated:
        from ragforge.migration import migrate_with_gate

        result = migrate_with_gate(
            knowledge=args.knowledge,
            from_model=args.old,
            to_model=args.new,
            golden_path=args.golden,
            primary_metric=args.metric,
            threshold_margin=args.margin,
            top_k=args.k,
            hot_set_first=not args.full_corpus,
            force=args.force,
        )
    else:
        from ragforge.migration import migrate_knowledge_base

        result = migrate_knowledge_base(
            knowledge=args.knowledge,
            from_model=args.old,
            to_model=args.new,
            validate=bool(args.golden),
            golden_path=args.golden,
            force=args.force,
        )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        print(f"Migration: {status}")
        if result.get("gate_decision"):
            print(f"  Gate: {result['gate_decision'].get('recommendation', 'N/A')}")
        print(f"  Chunks migrated: {result.get('num_chunks_migrated', 0)}")
    return 0 if result.get("status") == "migrated" else 1


def _cmd_migrate_smoke(args: argparse.Namespace) -> int:
    """Run post-migration smoke test."""
    from ragforge.migration.gate import smoke_test
    from ragforge.evaluation.golden import GoldenDataset

    golden = GoldenDataset.load(args.golden)
    result = smoke_test(
        knowledge=args.knowledge,
        golden=golden,
        top_k=args.k,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        result.print_summary()
    return 0 if result.passed else 1


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
    sp.add_argument(
        "--parser",
        default=None,
        help="parser backend: 'text', 'html', 'pdf', 'docling' (default: auto-detect by extension)",
    )
    sp.add_argument("--preview", type=int, default=500, help="characters of text to show")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_parse)

    # --- chunk ---
    sp = sub.add_parser("chunk", help="parse then chunk a file")
    sp.add_argument("path", help="file to chunk")
    sp.add_argument(
        "--parser",
        default=None,
        help="parser backend: 'text', 'html', 'pdf', 'docling' (default: auto-detect by extension)",
    )
    sp.add_argument("--strategy", choices=["fixed", "structure", "docling"], default="structure")
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
    sp.add_argument("--strategy", choices=["fixed", "structure", "docling"], default="structure")
    sp.add_argument(
        "--parser",
        default=None,
        help="parser backend: 'text', 'html', 'pdf', 'docling' (default: auto-detect by extension)",
    )
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

    # --- agents ---
    agents_parser = sub.add_parser("agents", help="multi-agent coordination via blackboard")
    agents_sub = agents_parser.add_subparsers(dest="agents_command", required=True)

    # agents run
    sp = agents_sub.add_parser("run", help="run a multi-agent task from a config file")
    sp.add_argument("config", help="path to agent config (.py file defining agents + goal)")
    sp.add_argument("--max-steps", type=int, default=50, help="max orchestration steps (default: 50)")
    sp.add_argument("--persist", action="store_true", help="persist blackboard to disk (survives crashes)")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_agents_run)

    # agents benchmark
    sp = agents_sub.add_parser("benchmark", help="compare direct-messaging vs blackboard cost")
    sp.add_argument("config", help="path to benchmark config (.py file defining task)")
    sp.add_argument("--max-steps", type=int, default=50, help="max orchestration steps (default: 50)")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_agents_benchmark)

    # agents board
    sp = agents_sub.add_parser("board", help="inspect a persisted blackboard")
    sp.add_argument("name", help="blackboard name")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_agents_board)

    # --- migrate ---
    migrate_parser = sub.add_parser("migrate", help="migrate between embedding models (with decision gate)")
    migrate_sub = migrate_parser.add_subparsers(dest="migrate_command", required=True)

    # migrate gate
    sp = migrate_sub.add_parser("gate", help="run the decision gate (compare old vs new model)")
    sp.add_argument("knowledge", help="knowledge base name")
    sp.add_argument("golden", help="path to golden dataset (JSON)")
    sp.add_argument("--old", required=True, help="current embedding model name")
    sp.add_argument("--new", required=True, help="candidate embedding model name")
    sp.add_argument("-k", type=int, default=5, help="top-k for retrieval metrics (default: 5)")
    sp.add_argument("--metric", default="recall_at_k", help="primary metric for GO/NO_GO (default: recall_at_k)")
    sp.add_argument("--margin", type=float, default=0.0, help="allowed regression margin (default: 0.0)")
    sp.add_argument("--full-corpus", action="store_true", help="evaluate full corpus (not just hot set)")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_migrate_gate)

    # migrate run
    sp = migrate_sub.add_parser("run", help="run a migration (optionally gated)")
    sp.add_argument("knowledge", help="knowledge base name")
    sp.add_argument("--old", required=True, help="current embedding model name")
    sp.add_argument("--new", required=True, help="target embedding model name")
    sp.add_argument("--golden", default=None, help="path to golden dataset (required for --gated)")
    sp.add_argument("--gated", action="store_true", help="run decision gate first, abort if NO_GO")
    sp.add_argument("--force", action="store_true", help="proceed even if gate says NO_GO")
    sp.add_argument("-k", type=int, default=5, help="top-k for gate metrics")
    sp.add_argument("--metric", default="recall_at_k", help="primary metric for gate")
    sp.add_argument("--margin", type=float, default=0.0, help="allowed regression margin")
    sp.add_argument("--full-corpus", action="store_true", help="gate on full corpus")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_migrate_run)

    # migrate smoke-test
    sp = migrate_sub.add_parser("smoke-test", help="post-migration smoke test")
    sp.add_argument("knowledge", help="knowledge base name")
    sp.add_argument("golden", help="path to golden dataset (JSON)")
    sp.add_argument("-k", type=int, default=5, help="top-k for retrieval (default: 5)")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_migrate_smoke)

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
