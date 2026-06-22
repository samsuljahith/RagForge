# RAGForge

**One workshop for building, evaluating, and optimizing RAG — usable from any language.**

RAGForge brings all RAG engineering tasks into one tool AND exposes everything over an HTTP/JSON API so agents written in any language (Python, JavaScript, Go, C++, etc.) can use it without being written in Python.

## What's Available

| Module | Description |
|--------|-------------|
| **Core** | Document/Chunk data models + plugin registry |
| **Parsing** | `.txt` / `.md` / `.html` / `.pdf` → Document (+ optional Docling backend for complex docs) |
| **Chunking** | Fixed (sliding window) + structure-aware + Docling (keeps tables & code intact) |
| **Pipeline** | Embed + store + hybrid search (dense + BM25 via RRF) + cross-encoder reranking |
| **Answer Generation** | Grounded answers with source citations. Refuses when evidence is insufficient. OpenAI / Anthropic / Ollama |
| **Evaluation** | Hit rate, MRR, precision@k, recall@k, faithfulness. A/B comparison on golden datasets |
| **Quantization** | Compress embeddings + measure cost/quality tradeoff on your data |
| **Migration** | Shadow-index a new embedding model, validate quality, atomic cutover |
| **Coordination** | Multi-agent blackboard (stigmergy). Agents share state instead of direct messaging |
| **Local UI** | `ragforge ui` — tracing dashboard, evaluation viewer, chat interface |
| **API** | HTTP/JSON endpoints for all features, interactive docs at /docs |

## Install

```bash
pip install ragforge            # core (zero dependencies)
pip install ragforge[api]       # add HTTP API server
pip install ragforge[pdf]       # add PDF support (lightweight pypdf)
pip install ragforge[pipeline]  # sentence-transformers embeddings + reranking
pip install ragforge[openai]    # OpenAI embeddings + LLM generation
pip install ragforge[anthropic] # Anthropic LLM generation
pip install ragforge[docling]   # Docling backend (heavy, best for complex docs)
pip install ragforge[ui]        # local web dashboard
pip install ragforge[all]       # everything
```

## Quick Start: CLI

```bash
ragforge info                                      # see registered components
ragforge parse notes.md                            # parse a file
ragforge chunk notes.md --strategy structure       # structure-aware chunking
ragforge knowledge build my-kb ./docs/             # build a knowledge base
ragforge query my-kb "How do refunds work?"        # query it (hybrid search)
ragforge query my-kb "refunds?" --generate --llm ollama  # with LLM answer
ragforge eval run my-kb golden.json                # evaluate retrieval quality
ragforge migrate gate my-kb golden.json --old default --new openai  # decision gate
ragforge agents run config.py                      # run multi-agent task
ragforge serve                                     # start the API server
ragforge ui                                        # launch local dashboard
```

## Quick Start: Python Library

```python
import ragforge as rf

# Parse + chunk
doc = rf.parse_file("notes.md")
chunks = rf.chunk_document(doc, strategy="structure")

for c in chunks:
    print(f"[{c.metadata.get('section')}] ~{c.token_count} tokens")
```

```python
from ragforge.pipeline import build_knowledge_base, query_knowledge_base

# Build a knowledge base
build_knowledge_base(name="my-kb", sources=["./docs/"])

# Query with hybrid search
result = query_knowledge_base(knowledge="my-kb", question="Refund policy?")
for chunk in result["chunks"]:
    print(f"  [{chunk['score']:.3f}] {chunk['text'][:80]}")

# Query with LLM-generated answer
result = query_knowledge_base(
    knowledge="my-kb", question="Refund policy?",
    generate=True, llm="ollama",
)
print(result["answer"])
```

## Quick Start: HTTP API (Any Language)

Start the server:

```bash
pip install ragforge[api]
ragforge serve
# Interactive docs at http://localhost:8000/docs
```

Then call it from any language — Python, JavaScript, Go, curl, anything with HTTP:

```bash
# Parse
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "# Hello\n\nWorld", "doc_type": "md"}'

# Query with generated answer
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"knowledge": "my-kb", "question": "How do refunds work?", "generate": true, "llm": "ollama"}'
```

## Connect an Agent in Any Language

RAGForge's API is plain HTTP/JSON. Any language with an HTTP client can use it:

**JavaScript/Node:**
```javascript
const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ knowledge: "my-kb", question: "Refund policy?", top_k: 3 }),
});
const { chunks, answer } = await resp.json();
```

**Go, Java, C++, Rust, etc.** — same pattern. See `examples/clients/` for full working examples.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server status + version |
| `/capabilities` | GET | List registered parsers, chunkers, etc. |
| `/parse` | POST | Parse text/file → Document |
| `/chunk` | POST | Document → Chunks |
| `/knowledge` | POST | Build/index a knowledge base |
| `/query` | POST | Query with hybrid search (+ optional LLM answer) |
| `/evaluate` | POST | Measure retrieval quality vs golden dataset |
| `/quantize` | POST | Quantize + compare cost/quality |
| `/migrate` | POST | Migrate between embedding models |
| `/migrate/gate` | POST | Decision gate: compare old vs new model (GO/NO_GO) |
| `/migrate/smoke-test` | POST | Post-migration verification |
| `/traces` | GET | List pipeline traces |
| `/coordination/boards` | POST | Create/inspect blackboards |
| `/coordination/run` | POST | Run a multi-agent task |

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

## Docker

```bash
docker build -t ragforge .
docker run -p 8000:8000 ragforge
```

## Development

```bash
git clone https://github.com/samsuljahith/RagForge.git
cd RagForge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[api,dev]"
pytest                    # run the test suite
```

## Documentation Website

Full documentation site built with Docusaurus:

```bash
cd website
npm install
npm run start            # local dev server at localhost:3000
npm run build            # production build
```

## Architecture

Each capability is its own module that **registers** itself via the plugin registry. Adding a new parser, chunker, or evaluator means writing one file — never editing a giant central one.

```
ragforge/
├── core/            # Shared models (Document, Chunk) + plugin registry
├── parsing/         # File → Document (txt, md, html, pdf, docling)
├── chunking/        # Document → Chunks (fixed, structure, docling)
├── pipeline/        # Embed + store + retrieve + generate answers
├── evaluation/      # Measure retrieval + generation quality
├── quantization/    # Compress embeddings + measure tradeoff
├── migration/       # Swap embedding models safely
├── coordination/    # Multi-agent blackboard + orchestrator + benchmark
├── tracing.py       # SQLite-backed trace store for observability
├── api/             # HTTP/JSON endpoints (FastAPI)
└── cli.py           # Command-line interface
```

## License

Apache-2.0. Open source, free to use, contributions welcome.
