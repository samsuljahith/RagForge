# RAGForge

> Build AI that reads your documents and answers honestly — parsing, retrieval, grounded answers, and evaluation in one toolkit. Runs on your machine. Free and open source.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Tests](https://img.shields.io/badge/tests-302%20passing-brightgreen)
![Runs locally](https://img.shields.io/badge/runs-locally-orange)
![Any language](https://img.shields.io/badge/HTTP%20API-any%20language-purple)

<!-- TODO: add banner image at assets/banner.png -->
<!-- TODO: add UI screenshot at assets/dashboard.png -->

---

## What is RAGForge?

Building a RAG system means stitching together half a dozen separate tools — a parser, a chunker, an embedder, a vector store, a retriever, an LLM caller, and some way to know if any of it actually works. RAGForge puts all of that into one library with a consistent Python API, a CLI, and an HTTP server so any language can use it.

It's aimed at developers building document Q&A, knowledge-base search, or any system where an LLM needs to answer from a corpus rather than from training memory.

---

## Quick start

### Install

```bash
pip install ragforge                 # core — zero dependencies
pip install ragforge[pipeline]       # local embeddings + reranking (sentence-transformers)
pip install ragforge[api]            # HTTP server (FastAPI + Uvicorn)
pip install ragforge[pdf]            # PDF parsing (pypdf)
pip install ragforge[openai]         # OpenAI embeddings + LLM generation
pip install ragforge[anthropic]      # Anthropic LLM generation
pip install ragforge[docling]        # Docling parser for complex documents
pip install ragforge[ui]             # local web dashboard
pip install ragforge[all]            # everything
```

### Python

```python
from ragforge.pipeline import build_knowledge_base, query_knowledge_base

# Index documents
build_knowledge_base(name="my-kb", sources=["./docs/"])

# Retrieve relevant chunks
result = query_knowledge_base(knowledge="my-kb", question="How do refunds work?")
for chunk in result["chunks"]:
    print(f"  [{chunk['score']:.3f}] {chunk['text'][:100]}")

# Get a grounded answer
result = query_knowledge_base(
    knowledge="my-kb",
    question="How do refunds work?",
    generate=True,
    llm="ollama",        # or "openai" / "anthropic"
)
print(result["answer"])
```

The LLM is instructed to answer only from retrieved context. If the answer isn't there, it says so.

### CLI

```bash
ragforge knowledge build my-kb ./docs/          # index documents
ragforge query my-kb "How do refunds work?"     # hybrid search
ragforge query my-kb "How do refunds work?" \
  --generate --llm ollama                       # retrieve + grounded answer
ragforge eval run my-kb golden.json             # measure retrieval quality
ragforge serve                                  # start HTTP API
ragforge ui                                     # open local dashboard
```

### Local dashboard

```bash
pip install ragforge[ui]
ragforge ui
# Opens http://127.0.0.1:8000/ui — traces, evaluation results, live chat
```

---

## What's inside

| Module | What it does |
|--------|-------------|
| **Parsing** | `.txt`, `.md`, `.html`, `.pdf` → `Document`. Optional Docling backend for complex layouts — preserves tables and code blocks |
| **Chunking** | Fixed-size sliding window, structure-aware (splits on headings), or Docling-aware. Configurable token budget |
| **Retrieval** | Dense vector search + BM25 keyword search, fused with Reciprocal Rank Fusion. Optional cross-encoder reranking |
| **Answers** | Grounded responses via OpenAI, Anthropic, or Ollama. Cites sources; refuses to hallucinate |
| **Evaluation** | Precision@k, recall@k, MRR, faithfulness. A/B compare two configurations on the same golden set |
| **Quantization** | Compress embeddings; measure cost/quality tradeoff on your corpus before committing |
| **Migration** | Shadow-index a candidate model, gate on real quality metrics, then swap atomically |
| **Multi-agent** | Blackboard coordination (stigmergy): agents post to a shared store instead of calling each other directly |
| **Dashboard** | Local web UI — pipeline traces, evaluation results, live chat against your knowledge base |

---

## Don't migrate blind — the migration decision gate

Switching embedding models means re-embedding your entire corpus. If the candidate model performs worse on your data, you've paid the compute cost and degraded production retrieval.

The migration gate compares both models on your corpus against a labelled query set and blocks the cutover if the candidate regresses on recall. The gate runs before any re-embedding happens.

**Benchmarked on BEIR/SciFact (5,183 docs, 300 labelled queries):** comparing `all-MiniLM-L6-v2` against a smaller candidate model (`paraphrase-MiniLM-L3-v2`), the gate detected a 16-point recall@5 regression and returned **NO_GO**, blocking the migration.

| Metric | Baseline | Candidate | Delta |
|--------|----------|-----------|-------|
| recall@5 | 0.738 | 0.575 | **−0.163** |
| precision@5 | 0.164 | 0.126 | −0.038 |
| MRR | 0.600 | 0.468 | −0.132 |

The gate's value is that it quantified the regression on a real corpus before any irreversible work happened.

```bash
ragforge migrate gate my-kb golden.json \
  --old all-MiniLM-L6-v2 \
  --new paraphrase-MiniLM-L3-v2
# Prints a full metric table. Exits 0 (GO) or 1 (NO_GO).
```

To reproduce the SciFact benchmark:

```bash
pip install datasets sentence-transformers numpy
python benchmarks/run_migration_gate_benchmark.py
```

---

## Use it from any language

RAGForge exposes everything as a plain HTTP/JSON API. Any language with an HTTP client can use it.

```bash
pip install ragforge[api]
ragforge serve
# http://127.0.0.1:8000 — Swagger UI at /docs
```

```bash
# Build a knowledge base
curl -X POST http://127.0.0.1:8000/knowledge \
  -H "Content-Type: application/json" \
  -d '{"name": "my-kb", "sources": ["./docs/"]}'

# Query it
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"knowledge": "my-kb", "question": "How do refunds work?", "top_k": 3}'
```

Full working examples (curl, Python, JavaScript) in [`examples/clients/`](examples/clients/).

**Endpoints:**

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/health` | GET | Server status + version |
| `/capabilities` | GET | Registered parsers, chunkers, embedders |
| `/parse` | POST | Text or file → Document |
| `/chunk` | POST | Document → Chunks |
| `/knowledge` | POST | Build / index a knowledge base |
| `/query` | POST | Hybrid search + optional LLM answer |
| `/evaluate` | POST | Score against a golden dataset |
| `/quantize` | POST | Compress embeddings, measure tradeoff |
| `/migrate/gate` | POST | GO / NO_GO decision before a model swap |
| `/migrate` | POST | Execute a (gated) migration |
| `/migrate/smoke-test` | POST | Post-migration verification |
| `/traces` | GET | Pipeline trace history |
| `/coordination/boards` | POST | Create a shared blackboard |
| `/coordination/run` | POST | Run a multi-agent task |

---

## Links

- **Docs:** [rag-forge-website.vercel.app](https://rag-forge-website.vercel.app)
- **GitHub:** [github.com/samsuljahith/RagForge](https://github.com/samsuljahith/RagForge)
- Made by [Samsul Jahith](https://github.com/samsuljahith)

---

## License

Apache-2.0. Contributions welcome — feedback especially. Open an issue or send a PR.
