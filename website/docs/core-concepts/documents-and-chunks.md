---
sidebar_position: 2
---

# Documents and Chunks

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
