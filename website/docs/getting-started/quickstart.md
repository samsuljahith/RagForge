---
sidebar_position: 3
---

# Quickstart

Get productive with RAGForge in under 5 minutes. Three ways to use it: CLI, Python library, or HTTP API.

## CLI

```bash
# See what's registered
ragforge info

# Parse a file into clean text
ragforge parse notes.md

# Chunk with structure-aware splitting (keeps tables/code intact)
ragforge chunk notes.md --strategy structure --show-text

# Build a knowledge base from a folder of docs
ragforge knowledge build my-kb ./docs/ --strategy structure

# Query it with hybrid search
ragforge query my-kb "How do refunds work?"

# Query with LLM-generated answer
ragforge query my-kb "How do refunds work?" --generate --llm ollama

# Evaluate against a golden dataset
ragforge eval run my-kb golden.json

# Start the API server
ragforge serve

# Launch the local UI (tracing, eval, chat)
ragforge ui
```

## Python Library

```python
import ragforge as rf

# Parse any supported file
doc = rf.parse_file("knowledge-base/refund-policy.md")
print(f"Parsed: {doc.source}, ~{doc.token_count} tokens")

# Chunk with structure-aware splitting
chunks = rf.chunk_document(doc, strategy="structure")
for chunk in chunks:
    print(f"  [{chunk.metadata.get('section')}] ~{chunk.token_count} tok")
```

### Build and Query a Knowledge Base

```python
from ragforge.pipeline import build_knowledge_base, query_knowledge_base

# Index documents
build_knowledge_base(
    name="my-kb",
    sources=["./docs/"],
    chunk_strategy="structure",
)

# Query with hybrid search (retrieval only)
result = query_knowledge_base(
    knowledge="my-kb",
    question="What is the refund policy?",
    top_k=5,
)

for chunk in result["chunks"]:
    print(f"  score={chunk['score']:.3f}: {chunk['text'][:80]}...")

# Query with LLM-generated answer (grounded, with sources)
result = query_knowledge_base(
    knowledge="my-kb",
    question="What is the refund policy?",
    generate=True,
    llm="ollama",
)
print(result["answer"])
```

## HTTP API

Start the server:

```bash
pip install ragforge[api]
ragforge serve
```

Then call it from any language:

```bash
# Health check
curl http://localhost:8000/health

# Parse text
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "# Hello\n\nWorld", "doc_type": "md"}'

# Chunk a document
curl -X POST http://localhost:8000/chunk \
  -H "Content-Type: application/json" \
  -d '{"doc": {"text": "# Title\n\nContent", "source": "x", "doc_type": "md", "metadata": {}, "id": "abc"}, "strategy": "structure"}'
```

Interactive API docs are auto-served at [http://localhost:8000/docs](http://localhost:8000/docs).

## What's Next

- [Architecture](../core-concepts/architecture) — understand how the pieces fit together
- [Parsing guide](../guides/parsing) — all supported formats (including Docling)
- [Chunking guide](../guides/chunking) — fixed vs structure-aware, when to use each
- [Pipeline guide](../guides/pipeline) — embed, store, retrieve, generate answers
- [Evaluation guide](../guides/evaluation) — measure retrieval quality
- [Local UI](../guides/ui) — launch the tracing/eval/chat dashboard
- [Coordination](../guides/coordination) — multi-agent blackboard coordination
- [Using from any language](../any-language/overview) — connect agents in JS, Go, etc.
