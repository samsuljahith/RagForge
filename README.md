# RAGForge

**One workshop for building, evaluating, and optimizing RAG — usable from any language.**

RAGForge brings all RAG engineering tasks into one tool AND exposes everything over an HTTP/JSON API so agents written in any language (Python, JavaScript, Go, C++, etc.) can use it without being written in Python.

> Status: All core modules built and working. API fully functional.

## What's Available

| Module | Description |
|--------|-------------|
| **Core** | Document/Chunk data models + plugin registry |
| **Parsing** | `.txt` / `.md` / `.html` / `.pdf` → Document (+ optional Docling backend for complex docs) |
| **Chunking** | Fixed (sliding window) + structure-aware + Docling (keeps tables & code intact) |
| **Pipeline** | Embed + store + hybrid search (dense + BM25) + reranking |
| **Evaluation** | Precision, recall, faithfulness metrics vs golden dataset |
| **Quantization** | Quantize embeddings + compare cost/quality tradeoff |
| **Migration** | Safely move between embedding models with quality validation |
| **Coordination** | Multi-agent blackboard coordination + cost benchmarking (cheaper than direct messaging) |
| **API** | HTTP/JSON endpoints for all features, interactive docs at /docs |

## Install

```bash
pip install ragforge            # core (zero dependencies)
pip install ragforge[api]       # add HTTP API server
pip install ragforge[pdf]       # add PDF support (lightweight pypdf)
pip install ragforge[docling]   # add Docling backend (heavy, best for complex docs)
pip install ragforge[all]       # everything
```

## Parsing Backends

RAGForge offers two parsing backends. Choose based on your document complexity:

| | Default | Docling |
|---|---------|---------|
| **Install** | Included (zero deps) | `pip install ragforge[docling]` |
| **Speed** | Fast | Slower (layout analysis + OCR) |
| **Best for** | Plain text, markdown, simple HTML | PDFs with tables, DOCX, PPTX, XLSX, scanned images |
| **Table handling** | Strips tags, may lose structure | Preserves table structure with cell data |
| **Code blocks** | Keeps intact (structure chunker) | Keeps intact with richer metadata |
| **OCR** | No | Yes (scanned documents, images) |
| **Metadata** | Filename, byte count | Page numbers, section hierarchy, content type |
| **Formats** | .txt, .md, .html, .pdf | .pdf, .docx, .pptx, .xlsx, .html, images |

**When to use which:**
- **Default** — you have simple markdown, text, or basic HTML. Instant, no dependencies.
- **Docling** — you have complex PDFs (multi-column, tables), Office docs, or scanned images.
  You need accurate table extraction and page-level metadata.

**Usage:**

```bash
# CLI
ragforge parse report.pdf --parser docling
ragforge chunk report.pdf --parser docling --strategy docling

# Python
from ragforge.core.registry import get
parser = get("parser", "docling")()
doc = parser.parse("report.pdf")

chunker = get("chunker", "docling")(max_tokens=384)
chunks = chunker.chunk(doc)
```

```bash
# API
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"path": "/data/report.pdf", "parser": "docling"}'

curl -X POST http://localhost:8000/chunk \
  -H "Content-Type: application/json" \
  -d '{"doc": {...}, "strategy": "docling"}'
```

The docling chunker works best when paired with the docling parser (which provides
the structured document). If you use the docling chunker on a document parsed by
the default parser, it falls back to RAGForge's built-in structure chunker with a
warning.

## Quick Start: CLI

```bash
ragforge info                                      # see registered components
ragforge parse notes.md                            # parse a file
ragforge chunk notes.md --strategy structure       # structure-aware chunking
ragforge knowledge build my-kb ./docs/             # build a knowledge base
ragforge knowledge query my-kb "How do refunds work?"  # query it
ragforge serve                                     # start the API server
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

# Query with hybrid search + reranking
result = query_knowledge_base(knowledge="my-kb", question="Refund policy?")
for chunk in result["chunks"]:
    print(f"  [{chunk['score']:.3f}] {chunk['text'][:80]}")
```

## Quick Start: HTTP API (Any Language)

Start the server:

```bash
ragforge serve
# Interactive docs at http://localhost:8000/docs
```

Then call it from any language — Python, JavaScript, Go, curl, anything with HTTP:

```bash
# Parse
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "# Hello\n\nWorld", "doc_type": "md"}'

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"knowledge": "my-kb", "question": "How do refunds work?", "top_k": 5}'
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
const { chunks } = await resp.json();
```

**Go, Java, C++, Rust, etc.** — same pattern. See `examples/clients/` for full working examples.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server status + version |
| `/capabilities` | GET | List registered plugins |
| `/parse` | POST | Parse text/file → Document |
| `/chunk` | POST | Document → Chunks |
| `/knowledge` | POST | Build/index a knowledge base |
| `/query` | POST | Query with hybrid search |
| `/evaluate` | POST | Measure retrieval quality |
| `/quantize` | POST | Quantize + compare cost/quality |
| `/migrate` | POST | Migrate between embedding models |

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

## Docker

```bash
docker build -t ragforge .
docker run -p 8000:8000 ragforge
```

## Development

```bash
git clone https://github.com/ragforge/ragforge.git
cd ragforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[api,dev]"
pytest                    # run all 86 tests
```

## Documentation Website

Full documentation site built with Docusaurus:

```bash
cd website
npm install
npm run start            # local dev server at localhost:3000
npm run build            # production build
```

## Multi-Agent Coordination

RAGForge includes a blackboard-based coordination module for running multiple agents together
without the cost of direct agent-to-agent messaging.

**The problem:** In most multi-agent frameworks, agents pass messages directly to each other.
Each handoff re-sends the full conversation history to an LLM — context grows with every step,
and cost grows with it.

**The solution:** Agents read/write a shared blackboard instead. Each agent only reads the
specific entries it needs. The orchestrator is a zero-token deterministic loop, not an
LLM-powered router.

```python
from ragforge.coordination import InMemoryBlackboard, Agent, AgentResult, Orchestrator

board = InMemoryBlackboard()
board.write("question", "How do refunds work?", author="user")

def researcher_trigger(b):
    return b.has_key("question") and not b.has_key("findings")

def researcher_action(b, agent_id):
    q = b.read("question")
    # ... call KB/LLM ...
    b.write("findings", "Refunds take 3-5 days...", author=agent_id,
            tags={"confidence": 0.9, "status": "ready"})
    return AgentResult(agent_id=agent_id, entries_read=["question"],
                       entries_written=["findings"], tokens_used=150)

agents = [Agent(id="researcher", trigger=researcher_trigger, action=researcher_action)]
orch = Orchestrator(board, agents, goal=lambda b: b.has_key("final_answer"), max_steps=20)
result = orch.run()
print(f"Done in {len(result.steps)} steps, {result.total_tokens} tokens")
```

**Benchmark the savings:**

```bash
ragforge agents benchmark examples/multi_agent_coordination.py
```

This runs the same task both ways (direct messaging vs blackboard) and prints the token/cost
difference. See `examples/multi_agent_coordination.py` for a full 3-agent example.

**Key features:**
- Blackboard persists to SQLite (crash recovery — if an agent dies, shared state remains)
- Tags/markers for stigmergy (agents react to signals, not direct calls)
- Deadlock detection + max-steps safety
- Full tracing (shows up in the UI dashboard)
- API endpoints for remote coordination

## Architecture

Each capability is its own module that **registers** itself via the plugin registry. Adding a new parser, chunker, or evaluator means writing one file — never editing a giant central one.

```
ragforge/
├── core/           # Shared models (Document, Chunk) + plugin registry
├── parsing/        # File → Document
├── chunking/       # Document → Chunks
├── pipeline/       # Embed + store + retrieve (hybrid search)
├── evaluation/     # Measure retrieval quality
├── quantization/   # Compress + compare cost/quality
├── migration/      # Swap embedding models safely
├── coordination/   # Multi-agent blackboard + orchestrator + benchmark
├── api/            # HTTP/JSON endpoints (FastAPI)
└── cli.py          # Command-line interface
```

## License

Apache-2.0. Open source, free to use, contributions welcome.
