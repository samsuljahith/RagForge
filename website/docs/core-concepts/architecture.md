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
        PIPE[Pipeline]
        EVAL[Evaluation]
        QUANT[Quantization]
        MIG[Migration]
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
    MOD --> PARSE
    MOD --> CHUNK
    MOD --> PIPE
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
```

## Module Dependencies

```mermaid
graph BT
    CORE[Core: Models + Registry]
    PARSE[Parsing] --> CORE
    CHUNK[Chunking] --> CORE
    PIPE[Pipeline] --> CORE
    PIPE --> PARSE
    PIPE --> CHUNK
    EVAL[Evaluation] --> PIPE
    QUANT[Quantization] --> EVAL
    MIG[Migration] --> EVAL
    MIG --> PIPE
    API[API Layer] --> CORE
    API --> PARSE
    API --> CHUNK
    API --> PIPE
    API --> EVAL
    API --> QUANT
    API --> MIG
```
