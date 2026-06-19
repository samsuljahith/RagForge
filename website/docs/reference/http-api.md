---
sidebar_position: 2
---

# HTTP API Reference

All endpoints accept and return JSON. Start the server with `ragforge serve` or `uvicorn ragforge.api:app`.

Interactive docs (try endpoints live): `http://localhost:8000/docs`

## System

### GET /health

Health check. Returns server status and version.

**Response:**
```json
{"status": "healthy", "version": "0.1.0", "service": "ragforge"}
```

---

### GET /capabilities

List all registered plugins.

**Response:**
```json
{
  "capabilities": {
    "parser": ["html", "pdf", "text"],
    "chunker": ["fixed", "structure"],
    "embedding": ["default", "quantized"],
    "store": ["memory"]
  }
}
```

---

## Parsing

### POST /parse

Parse a file or raw text into a Document.

**Request:**
```json
{
  "path": "/data/file.md",
  "text": null,
  "doc_type": "txt",
  "source": "api-input"
}
```

Provide either `path` (server-side file) OR `text` (raw content). Not both.

**Response (200):**
```json
{
  "id": "a1b2c3d4",
  "text": "# Title\n\nContent...",
  "source": "/data/file.md",
  "doc_type": "md",
  "metadata": {"filename": "file.md", "bytes": 1234},
  "token_count": 42
}
```

**Errors:**
- `400` — Neither path nor text provided
- `404` — File not found
- `422` — Missing optional dependency (e.g., pypdf)

---

## Chunking

### POST /chunk

Split a Document into Chunks.

**Request:**
```json
{
  "doc": {"text": "...", "source": "...", "doc_type": "md", "metadata": {}, "id": "..."},
  "strategy": "structure",
  "options": {"max_tokens": 384}
}
```

**Options by strategy:**
- `structure`: `{"max_tokens": 384, "min_tokens": 64}`
- `fixed`: `{"chunk_tokens": 256, "overlap_tokens": 32}`

**Response (200):**
```json
{
  "chunks": [
    {
      "id": "e5f6g7h8",
      "text": "Chunk content...",
      "doc_id": "a1b2c3d4",
      "index": 0,
      "metadata": {"strategy": "StructureChunker", "section": "Title"},
      "token_count": 28
    }
  ],
  "count": 3,
  "strategy": "structure"
}
```

**Errors:**
- `400` — Invalid document, unknown strategy, or bad options

---

## Pipeline

### POST /knowledge

Build/index a knowledge base from source documents.

**Request:**
```json
{
  "name": "my-kb",
  "sources": ["/data/docs/", "/data/policy.md"],
  "embedding_model": "default",
  "chunk_strategy": "structure",
  "chunk_options": {}
}
```

**Response (200):**
```json
{
  "name": "my-kb",
  "status": "built",
  "num_documents": 5,
  "num_chunks": 23,
  "embedding_model": "default"
}
```

**Errors:**
- `501` — Pipeline module not installed

---

### POST /query

Query a knowledge base with hybrid search.

**Request:**
```json
{
  "knowledge": "my-kb",
  "question": "How do refunds work?",
  "top_k": 5,
  "rerank": true
}
```

**Response (200):**
```json
{
  "question": "How do refunds work?",
  "knowledge": "my-kb",
  "chunks": [
    {
      "id": "c1d2e3f4",
      "text": "Refunds are processed within 30 days...",
      "doc_id": "a1b2c3d4",
      "index": 0,
      "metadata": {"section": "Refund Policy"},
      "score": 0.0312
    }
  ],
  "answer": null
}
```

**Errors:**
- `404` — Knowledge base not found
- `501` — Pipeline module not installed

---

## Evaluation

### POST /evaluate

Evaluate retrieval quality against a golden dataset.

**Request:**
```json
{
  "knowledge": "my-kb",
  "golden_dataset": [
    {"question": "Refund window?", "expected_answer": "30 days"}
  ],
  "metrics": ["precision", "recall", "faithfulness"]
}
```

**Response (200):**
```json
{
  "knowledge": "my-kb",
  "metrics": [
    {"name": "precision", "score": 0.85, "details": {"per_question": [0.85]}},
    {"name": "recall", "score": 0.90, "details": {"per_question": [0.90]}},
    {"name": "faithfulness", "score": 0.92, "details": {"per_question": [0.92]}}
  ],
  "summary": {"precision": 0.85, "recall": 0.90, "faithfulness": 0.92},
  "num_questions": 1
}
```

---

## Quantization

### POST /quantize

Quantize a model and report cost/quality tradeoff.

**Request:**
```json
{
  "target": "default",
  "knowledge": "my-kb",
  "options": {"bits": 8}
}
```

**Response (200):**
```json
{
  "target": "default",
  "status": "quantized",
  "report": {
    "before": {"model": "default", "bits": 32, "dimension": 128},
    "after": {"model": "default_quantized_8bit", "bits": 8, "compression_ratio": 4.0},
    "quality_delta": -0.02,
    "cost_reduction": 0.75
  }
}
```

---

## Migration

### POST /migrate

Migrate a knowledge base between embedding models.

**Request:**
```json
{
  "knowledge": "my-kb",
  "from_model": "default",
  "to_model": "quantized",
  "run_validation": true,
  "options": {}
}
```

**Response (200):**
```json
{
  "knowledge": "my-kb",
  "from_model": "default",
  "to_model": "quantized",
  "status": "migrated",
  "quality_before": 1.0,
  "quality_after": 0.95,
  "num_chunks_migrated": 23
}
```

**Errors:**
- `404` — Knowledge base not found
- `501` — Migration module not installed

---

## Error Format

All errors return JSON:

```json
{"detail": "Human-readable error message"}
```

Standard HTTP status codes:
- `400` — Bad request (invalid input)
- `404` — Resource not found
- `422` — Validation error or missing dependency
- `500` — Internal server error
- `501` — Module not installed
