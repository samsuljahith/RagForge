---
sidebar_position: 3
---

# Python API Reference

The Python library interface. Everything the API does, the library does directly (no server needed).

## Top-Level Imports

```python
import ragforge as rf

rf.parse_file(path)           # Parse any supported file
rf.chunk_document(doc, ...)   # Chunk a Document
rf.available(kind)            # List registered plugins
rf.__version__                # Current version string
```

---

## ragforge.parsing

### `parse_file(path) -> Document`

Auto-detect format by extension and parse.

```python
from ragforge.parsing import parse_file

doc = parse_file("notes.md")      # -> Document(doc_type="md")
doc = parse_file("page.html")     # -> Document(doc_type="html")
doc = parse_file("paper.pdf")     # -> Document(doc_type="pdf")
```

Raises `ValueError` if no parser supports the extension. Raises `ImportError` for PDF if pypdf is not installed.

---

## ragforge.chunking

### `chunk_document(document, strategy, **kwargs) -> list[Chunk]`

Chunk a Document using a named strategy.

```python
from ragforge.chunking import chunk_document

# Structure-aware (default)
chunks = chunk_document(doc, strategy="structure", max_tokens=384)

# Fixed sliding window
chunks = chunk_document(doc, strategy="fixed", chunk_tokens=256, overlap_tokens=32)
```

---

## ragforge.pipeline

### `build_knowledge_base(name, sources, ...) -> dict`

Build and persist a knowledge base.

```python
from ragforge.pipeline import build_knowledge_base

result = build_knowledge_base(
    name="my-kb",
    sources=["./docs/", "policy.md"],
    embedding_model="default",
    chunk_strategy="structure",
    chunk_options={"max_tokens": 384},
)
# Returns: {"name": ..., "status": "built", "num_documents": ..., "num_chunks": ..., "embedding_model": ...}
```

### `query_knowledge_base(knowledge, question, ...) -> dict`

Query with hybrid search (dense + BM25 + reranking).

```python
from ragforge.pipeline import query_knowledge_base

result = query_knowledge_base(
    knowledge="my-kb",
    question="How do refunds work?",
    top_k=5,
    rerank=True,
)
# Returns: {"question": ..., "knowledge": ..., "chunks": [...], "answer": None}
```

---

## ragforge.evaluation

### `evaluate_knowledge_base(knowledge, golden_dataset, metrics) -> dict`

Evaluate retrieval quality.

```python
from ragforge.evaluation import evaluate_knowledge_base

result = evaluate_knowledge_base(
    knowledge="my-kb",
    golden_dataset=[
        {"question": "Refund window?", "expected_answer": "30 days"},
    ],
    metrics=["precision", "recall", "faithfulness"],
)
```

### `compare_configs(knowledge, golden_dataset, config_a, config_b) -> dict`

A/B comparison between configurations.

```python
from ragforge.evaluation import compare_configs

result = compare_configs(
    knowledge="base",
    golden_dataset=golden,
    config_a={"sources": srcs, "chunk_strategy": "fixed"},
    config_b={"sources": srcs, "chunk_strategy": "structure"},
)
# Returns: {"config_a": ..., "results_a": ..., "results_b": ..., "delta": ..., "winner": "b"}
```

### `compute_precision(retrieved_ids, relevant_ids) -> float`

### `compute_recall(retrieved_ids, relevant_ids) -> float`

---

## ragforge.quantization

### `quantize_and_compare(target, knowledge, options) -> dict`

Quantize and report cost/quality tradeoff.

```python
from ragforge.quantization import quantize_and_compare

result = quantize_and_compare(
    target="default",
    knowledge="my-kb",
    options={"bits": 8},
)
```

---

## ragforge.migration

### `migrate_knowledge_base(knowledge, from_model, to_model, ...) -> dict`

Safely migrate between embedding models.

```python
from ragforge.migration import migrate_knowledge_base

result = migrate_knowledge_base(
    knowledge="my-kb",
    from_model="default",
    to_model="quantized",
    validate=True,
)
```

---

## ragforge.core

### Data Models

```python
from ragforge.core.models import Document, Chunk, estimate_tokens

doc = Document(text="...", source="file.md", doc_type="md")
chunk = Chunk(text="...", doc_id=doc.id, index=0)
tokens = estimate_tokens("some text")  # ~len/4
```

### Registry

```python
from ragforge.core.registry import register, get, available, all_kinds, registered_info

@register("parser", "custom")
class CustomParser: ...

cls = get("parser", "custom")
names = available("parser")
all_kinds()       # ["chunker", "embedding", "parser", "store"]
registered_info() # full dict
```
