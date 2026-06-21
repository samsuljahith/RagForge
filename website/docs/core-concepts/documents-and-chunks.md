---
sidebar_position: 2
---

# Documents and Chunks

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="90" viewBox="0 0 550 90">
  <rect x="10" y="25" width="65" height="40" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"/>
  <text x="42" y="43" textAnchor="middle" fontSize="7" fontWeight="600" fill="#ff6b2c">Source File</text>
  <text x="42" y="56" textAnchor="middle" fontSize="6" fill="#6a6a80">.pdf .md .html</text>
  <rect x="115" y="20" width="95" height="50" rx="8" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="162" y="38" textAnchor="middle" fontSize="8" fontWeight="700" fill="#7c6ff8">Document</text>
  <text x="162" y="50" textAnchor="middle" fontSize="6" fill="#a78bfa">text + source</text>
  <text x="162" y="61" textAnchor="middle" fontSize="6" fill="#6a6a80">doc_type + metadata</text>
  <rect x="255" y="10" width="80" height="28" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"><animate attributeName="opacity" values="1;0.6;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="295" y="27" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">Chunk 0</text>
  <rect x="255" y="42" width="80" height="28" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"><animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="295" y="59" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">Chunk 1</text>
  <rect x="370" y="25" width="95" height="40" rx="6" fill="#1a1a24" stroke="#22d3ee" strokeWidth="1.5"/>
  <text x="417" y="42" textAnchor="middle" fontSize="7" fontWeight="600" fill="#22d3ee">text + doc_id</text>
  <text x="417" y="55" textAnchor="middle" fontSize="6" fill="#6a6a80">index + metadata</text>
  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M77,45 L113,45"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.5s" repeatCount="indefinite" path="M212,38 L253,24"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.8s" repeatCount="indefinite" path="M212,50 L253,56"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.5s" repeatCount="indefinite" path="M337,40 L368,40"/></circle>
  <text x="485" y="45" fontSize="7" fill="#6a6a80">→ embed</text>
  <text x="275" y="82" textAnchor="middle" fontSize="7" fill="#6a6a80">File → Document (one per file) → Chunks (many per document) → ready for embedding</text>
</svg>
</div>

The shared data format that every module speaks. A parser produces a Document. A chunker turns a Document into Chunks. The pipeline embeds Chunks. Because every module reads and writes these same objects, the pieces fit together cleanly.

## Document

A `Document` represents one source file after parsing:

```python
from ragforge.core.models import Document

doc = Document(
    text="The extracted plain text content...",
    source="path/to/file.md",
    doc_type="md",
    metadata={"filename": "file.md", "bytes": 1234},
    id="a1b2c3d4",  # auto-generated if not provided
)

# Properties
doc.token_count  # estimated tokens (~4 chars per token)
doc.to_dict()    # serialize to JSON-friendly dict
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | str | The extracted plain text content |
| `source` | str | Path or URL the document came from |
| `doc_type` | str | Format: `txt`, `md`, `html`, `pdf` |
| `metadata` | dict | Anything extra (title, page count, etc.) |
| `id` | str | Stable identifier (auto-generated) |

## Chunk

A `Chunk` is a piece of a Document, ready to be embedded and retrieved:

```python
from ragforge.core.models import Chunk

chunk = Chunk(
    text="The chunk's text content...",
    doc_id="a1b2c3d4",  # links back to parent Document
    index=0,             # position within the document
    metadata={"section": "Refund Policy", "strategy": "StructureChunker"},
    id="e5f6g7h8",       # auto-generated if not provided
)

# Properties
chunk.token_count  # estimated tokens
chunk.to_dict()    # serialize to JSON-friendly dict
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | str | The chunk's text |
| `doc_id` | str | ID of the parent Document |
| `index` | int | Position within the document (0, 1, 2...) |
| `metadata` | dict | Section title, strategy used, page number, etc. |
| `id` | str | Stable identifier (auto-generated) |

## Token Estimation

RAGForge uses a simple rule: **~4 characters per token**. This avoids needing a tokenizer dependency while being accurate enough for chunk sizing decisions.

```python
from ragforge.core.models import estimate_tokens

estimate_tokens("Hello, world!")  # 3
estimate_tokens("a" * 1000)      # 250
```

## Serialization

Both Document and Chunk support `to_dict()` and `from_dict()` for JSON serialization. This is what the API layer uses internally:

```python
# Serialize
data = doc.to_dict()
# {"text": "...", "source": "...", "doc_type": "md", "metadata": {...}, "id": "...", "token_count": 42}

# Deserialize
doc = Document.from_dict(data)
```
