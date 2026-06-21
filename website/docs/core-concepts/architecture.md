---
sidebar_position: 1
---

# Architecture

RAGForge is designed as independent modules under a shared core, connected by a plugin registry. This keeps each piece testable and replaceable while the whole system feels like one tool.

## System Overview

```mermaid
graph TB
    subgraph "Clients (Any Language)"
        PY[Python Agent]
        JS[JavaScript Agent]
        GO[Go Agent]
        CURL[curl / any HTTP]
    end

    subgraph "RAGForge API Layer"
        API[FastAPI Server]
        DOCS[/docs - Swagger UI/]
    end

    subgraph "RAGForge Core"
        REG[Plugin Registry]
        MOD[Document / Chunk Models]
    end

    subgraph "Modules"
        PARSE[Parsing]
        CHUNK[Chunking]
        PIPE[Pipeline + Generation]
        EVAL[Evaluation]
        QUANT[Quantization]
        MIG[Migration]
        COORD[Coordination]
        UI[Local UI]
    end

    PY --> API
    JS --> API
    GO --> API
    CURL --> API
    API --> DOCS
    API --> REG
    REG --> PARSE
    REG --> CHUNK
    REG --> PIPE
    REG --> EVAL
    REG --> QUANT
    REG --> MIG
    REG --> COORD
    MOD --> PARSE
    MOD --> CHUNK
    MOD --> PIPE
    UI --> API
```

## Design Principles

### 1. Shared Core, Independent Modules

Every module depends on `core/` (the data models and registry) but never on each other unless there's a real dependency (e.g., evaluation depends on pipeline for querying).

### 2. Plugin Registry

The registry is the trick that keeps RAGForge extensible:

```python
from ragforge.core.registry import register

@register("chunker", "my-custom")
class MyChunker(Chunker):
    def chunk(self, document: Document) -> list[Chunk]:
        ...
```

Adding a new parser, chunker, or embedding model = adding one file. No giant central file to edit.

### 3. Dual Interface

Every feature works both ways:
- **Python library**: `import ragforge; rf.parse_file("x.md")`
- **HTTP API**: `POST /parse {"path": "x.md"}`

The API layer is a thin translation between HTTP/JSON and the Python modules.

### 4. Zero-Dep Core

The core install requires nothing. Heavy dependencies (FastAPI, ML models, vector DBs) live in optional extras so `pip install ragforge` is instant.

## Data Flow

```mermaid
flowchart LR
    FILES[Source Files] --> PARSE[Parser]
    PARSE --> DOC[Document]
    DOC --> CHUNK[Chunker]
    CHUNK --> CHUNKS[Chunks]
    CHUNKS --> EMBED[Embedding]
    EMBED --> STORE[Vector Store]
    QUERY[Query] --> EMBED
    EMBED --> SEARCH[Hybrid Search]
    STORE --> SEARCH
    SEARCH --> RERANK[Reranker]
    RERANK --> RESULTS[Retrieved Chunks]
    RESULTS --> LLM[LLM Generation]
    LLM --> ANSWER[Grounded Answer + Sources]
```

## Module Dependencies

```mermaid
graph BT
    CORE[Core: Models + Registry]
    PARSE[Parsing] --> CORE
    CHUNK[Chunking] --> CORE
    PIPE[Pipeline + Generation] --> CORE
    PIPE --> PARSE
    PIPE --> CHUNK
    EVAL[Evaluation] --> PIPE
    QUANT[Quantization] --> EVAL
    MIG[Migration] --> EVAL
    MIG --> PIPE
    COORD[Coordination] --> CORE
    UI[Local UI] --> API
    API[API Layer] --> CORE
    API --> PARSE
    API --> CHUNK
    API --> PIPE
    API --> EVAL
    API --> QUANT
    API --> MIG
    API --> COORD
```

## Directory Structure

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
├── api/             # HTTP/JSON endpoints (FastAPI)
├── tracing.py       # SQLite-backed trace store for observability
├── ui_static/       # Pre-built frontend for ragforge ui
└── cli.py           # Command-line interface
```
