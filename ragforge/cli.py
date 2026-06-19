"""
RAGForge command-line interface.

This is what makes RAGForge feel like ONE tool: a single `ragforge` command with
subcommands for each capability.

Usage:
    ragforge info
    ragforge parse path/to/file.md
    ragforge chunk path/to/file.md --strategy structure --max-tokens 384
    ragforge knowledge build my-kb docs/ --strategy structure
    ragforge knowledge query my-kb "How do refunds work?"
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
        embedding_model=args.embedding_model,
        chunk_strategy=args.strategy,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Knowledge base '{result['name']}' built successfully.")
        print(f"  Documents: {result['num_documents']}")
        print(f"  Chunks   : {result['num_chunks']}")
        print(f"  Model    : {result['embedding_model']}")
    return 0


def _cmd_knowledge_query(args: argparse.Namespace) -> int:
    """Query a knowledge base."""
    from ragforge.pipeline import query_knowledge_base

    result = query_knowledge_base(
        knowledge=args.name,
        question=args.question,
        top_k=args.top_k,
        rerank=not args.no_rerank,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query: {result['question']}")
        print(f"Knowledge base: {result['knowledge']}")
        print(f"Results: {len(result['chunks'])} chunks\n")
        for c in result["chunks"]:
            section = c["metadata"].get("section", "")
            head = f"  [{c['index']}] score={c['score']:.4f}"
            head += f"  section: {section}" if section else ""
            print(head)
            print(f"      {c['text'][:120]}...")
            print()
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
    kb_parser = sub.add_parser("knowledge", help="build and query knowledge bases")
    kb_sub = kb_parser.add_subparsers(dest="kb_command", required=True)

    # knowledge build
    sp = kb_sub.add_parser("build", help="build a knowledge base from files")
    sp.add_argument("name", help="name for the knowledge base")
    sp.add_argument("sources", nargs="+", help="files or directories to index")
    sp.add_argument("--strategy", choices=["fixed", "structure"], default="structure")
    sp.add_argument("--embedding-model", default="default", help="embedding model to use")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_knowledge_build)

    # knowledge query
    sp = kb_sub.add_parser("query", help="query a knowledge base")
    sp.add_argument("name", help="knowledge base name")
    sp.add_argument("question", help="question to ask")
    sp.add_argument("--top-k", type=int, default=5, help="number of results")
    sp.add_argument("--no-rerank", action="store_true", help="skip reranking")
    sp.add_argument("--json", action="store_true", help="output as JSON")
    sp.set_defaults(func=_cmd_knowledge_query)

    # --- serve ---
    sp = sub.add_parser("serve", help="start the HTTP/JSON API server")
    sp.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    sp.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    sp.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev mode)")
    sp.set_defaults(func=_cmd_serve)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
