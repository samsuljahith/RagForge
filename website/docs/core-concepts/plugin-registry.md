---
sidebar_position: 3
---

# Plugin Registry

The registry is how RAGForge stays extensible without becoming a tangled mess. Each parser, chunker, embedding model, and store registers itself under a name. Other code can then request "the structure-aware chunker" by name without importing it directly.

## How It Works

```python
from ragforge.core.registry import register, get, available

# Register a class
@register("chunker", "my-custom")
class MyCustomChunker:
    ...

# Look it up by name
chunker_cls = get("chunker", "my-custom")
chunker = chunker_cls()

# List what's available
available("chunker")   # ['fixed', 'my-custom', 'structure']
available("parser")    # ['html', 'pdf', 'text']
```

## Why This Matters

Adding a new feature means writing one new file that registers itself. You never edit a central file. This is the pattern that keeps big projects manageable:

```python
# File: ragforge/chunking/my_chunker.py

from ragforge.core.registry import register
from ragforge.chunking.base import Chunker

@register("chunker", "semantic")
class SemanticChunker(Chunker):
    """Splits on semantic boundaries using sentence embeddings."""

    def chunk(self, document):
        # Your implementation here
        ...
```

That's it. The new chunker is now available everywhere:
- CLI: `ragforge chunk file.md --strategy semantic`
- API: `POST /chunk {"strategy": "semantic"}`
- Python: `chunk_document(doc, strategy="semantic")`

## API

### `register(kind, name)`

Class decorator that registers a class under a `(kind, name)` pair.

```python
@register("parser", "docx")
class DocxParser(Parser):
    ...
```

### `get(kind, name)`

Look up a registered class. Raises `KeyError` with a helpful message if not found.

```python
cls = get("chunker", "structure")
```

### `available(kind)`

List all registered names for a kind:

```python
available("chunker")  # ['fixed', 'structure']
available("parser")   # ['html', 'pdf', 'text']
```

### `all_kinds()`

List every kind that has at least one registered item:

```python
all_kinds()  # ['chunker', 'embedding', 'parser', 'store']
```

### `registered_info()`

Full registry as a dict (used by the `/capabilities` API endpoint):

```python
registered_info()
# {'chunker': ['fixed', 'structure'], 'parser': ['html', 'pdf', 'text'], ...}
```

## Current Registry Contents

| Kind | Registered Names |
|------|-----------------|
| `parser` | `text`, `html`, `pdf` |
| `chunker` | `fixed`, `structure` |
| `embedding` | `default`, `quantized` |
| `store` | `memory` |
