---
sidebar_position: 3
---

# Plugin Registry

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="100" viewBox="0 0 500 100">
  <rect x="180" y="15" width="140" height="50" rx="10" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="250" y="37" textAnchor="middle" fontSize="9" fontWeight="700" fill="#ff6b2c">Registry</text>
  <text x="250" y="50" textAnchor="middle" fontSize="6" fill="#6a6a80">@register(kind, name)</text>
  <text x="250" y="60" textAnchor="middle" fontSize="6" fill="#6a6a80">get(kind, name) → class</text>
  <rect x="20" y="75" width="60" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="50" y="88" textAnchor="middle" fontSize="6" fill="#34d399">TextParser</text>
  <rect x="90" y="75" width="60" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
  <text x="120" y="88" textAnchor="middle" fontSize="6" fill="#34d399">PdfParser</text>
  <rect x="160" y="75" width="60" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="1;0.7;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="190" y="88" textAnchor="middle" fontSize="6" fill="#7c6ff8">FixedChunker</text>
  <rect x="230" y="75" width="75" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="0.7;1;0.7" dur="2.2s" repeatCount="indefinite"/></rect>
  <text x="267" y="88" textAnchor="middle" fontSize="6" fill="#7c6ff8">StructureChunker</text>
  <rect x="315" y="75" width="70" height="20" rx="4" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1"/>
  <text x="350" y="88" textAnchor="middle" fontSize="6" fill="#fbbf24">DefaultEmbed</text>
  <rect x="395" y="75" width="65" height="20" rx="4" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1"/>
  <text x="427" y="88" textAnchor="middle" fontSize="6" fill="#fbbf24">InMemoryStore</text>
  <circle r="2.5" fill="#34d399"><animateMotion dur="2s" repeatCount="indefinite" path="M50,74 L210,67"/></circle>
  <circle r="2.5" fill="#7c6ff8"><animateMotion dur="2.2s" repeatCount="indefinite" path="M230,74 L240,67"/></circle>
  <circle r="2.5" fill="#fbbf24"><animateMotion dur="2.4s" repeatCount="indefinite" path="M380,74 L280,67"/></circle>
  <text x="250" y="12" textAnchor="middle" fontSize="7" fill="#6a6a80">Add a feature = add one file with @register. Never edit a central file.</text>
</svg>
</div>

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
