---
sidebar_position: 3
---

# Quickstart

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="80" viewBox="0 0 550 80">
  <rect x="10" y="20" width="80" height="40" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"/>
  <text x="50" y="38" textAnchor="middle" fontSize="7" fontWeight="600" fill="#ff6b2c">pip install</text>
  <text x="50" y="50" textAnchor="middle" fontSize="6" fill="#6a6a80">ragforge</text>
  <rect x="130" y="15" width="60" height="25" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="160" y="31" textAnchor="middle" fontSize="7" fill="#34d399">CLI</text>
  <rect x="130" y="45" width="60" height="25" rx="5" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
  <text x="160" y="61" textAnchor="middle" fontSize="7" fill="#7c6ff8">Python</text>
  <rect x="220" y="15" width="60" height="25" rx="5" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1"><animate attributeName="opacity" values="1;0.7;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="250" y="31" textAnchor="middle" fontSize="7" fill="#fbbf24">HTTP API</text>
  <rect x="320" y="20" width="100" height="40" rx="8" fill="#1a1a24" stroke="#34d399" strokeWidth="2"/>
  <text x="370" y="38" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Parse → Chunk</text>
  <text x="370" y="50" textAnchor="middle" fontSize="6" fill="#34d399">→ Search → Answer</text>
  <rect x="450" y="25" width="75" height="30" rx="6" fill="#1a1a24" stroke="#22d3ee" strokeWidth="1.5"/>
  <text x="487" y="44" textAnchor="middle" fontSize="7" fontWeight="600" fill="#22d3ee">Result ✓</text>
  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M92,40 L128,30"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.5s" repeatCount="indefinite" path="M192,27 L318,35"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.3s" repeatCount="indefinite" path="M422,40 L448,40"/></circle>
  <text x="275" y="75" textAnchor="middle" fontSize="7" fill="#6a6a80">Install → choose your interface (CLI / Python / API) → full RAG pipeline → answers</text>
</svg>
</div>

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
