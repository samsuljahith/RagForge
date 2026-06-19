# RAGForge

**One workshop for building, evaluating, and optimizing RAG — usable from any language.**

RAGForge brings all RAG engineering tasks into one tool AND exposes everything over an HTTP/JSON API so agents written in any language (Python, JavaScript, Go, C++, etc.) can use it without being written in Python.

> Status: All core modules built and working. API fully functional.

## What's Available

| Module | Description |
|--------|-------------|
| **Core** | Document/Chunk data models + plugin registry |
| **Parsing** | `.txt` / `.md` / `.html` / `.pdf` → Document |
| **Chunking** | Fixed (sliding window) + structure-aware (keeps tables & code intact) |
| **Pipeline** | Embed + store + hybrid search (dense + BM25) + reranking |
| **Evaluation** | Precision, recall, faithfulness metrics vs golden dataset |
| **Quantization** | Quantize embeddings + compare cost/quality tradeoff |
| **Migration** | Safely move between embedding models with quality validation |
| **API** | HTTP/JSON endpoints for all features, interactive docs at /docs |

## Install

```bash
pip install ragforge            # core (zero dependencies)
pip install ragforge[api]       # add HTTP API server
pip install ragforge[pdf]       # add PDF support
pip install ragforge[all]       # everything
```

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
├── api/            # HTTP/JSON endpoints (FastAPI)
└── cli.py          # Command-line interface
```

## License

Apache-2.0. Open source, free to use, contributions welcome.
