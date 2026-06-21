---
sidebar_position: 2
---

# Chunking

Chunking matters more than model choice — that's the hard-won lesson from practitioners. RAGForge ships three strategies: a simple fixed-size baseline, a structure-aware chunker that keeps tables and code blocks intact, and an optional Docling-powered chunker for complex documents.

## Three Strategies

### Fixed (Sliding Window)

The classic approach: split into chunks of ~N tokens with overlap.

```python
from ragforge.chunking import chunk_document

chunks = chunk_document(doc, strategy="fixed", chunk_tokens=256, overlap_tokens=32)
```

- **Good for**: homogeneous text, simple use cases, baselines
- **Bad for**: structured content (tables, code, headers get cut in half)

### Structure-Aware

Respects document structure. Splits on markdown headers and paragraph boundaries, never cuts code blocks or tables, and tags each chunk with its section.

```python
chunks = chunk_document(doc, strategy="structure", max_tokens=384)
```

- **Good for**: markdown docs, knowledge bases, anything with structure
- **Keeps intact**: code blocks, tables, lists within a section
- **Tags**: each chunk has `metadata["section"]` showing where it came from

### Docling (Optional)

Uses IBM's Docling library for layout-aware chunking of complex documents. Best paired with the Docling parser, which gives it the full structured document.

```bash
pip install ragforge[docling]
```

```python
from ragforge.chunking import chunk_document

# Best when document was parsed by DoclingParser (has _docling_doc in metadata)
chunks = chunk_document(doc, strategy="docling", max_tokens=512)
```

- **Good for**: PDFs with tables, DOCX/PPTX, scanned images
- **Requires**: `pip install ragforge[docling]`
- **Best combo**: use `--parser docling --strategy docling` together

```bash
ragforge chunk report.pdf --parser docling --strategy docling --show-text
```

:::note
If you use the docling chunker on a document parsed by the default parser, it falls back to the structure chunker with a warning. For best results, pair docling parser + docling chunker.
:::

## Before/After Comparison

Given this markdown:

```markdown
# Refund Policy

Our refund policy allows returns within 30 days.

## Fee Table

| Item type   | Fee  | Window  |
|-------------|------|---------|
| Electronics | 15%  | 14 days |
| Clothing    | 0%   | 30 days |

## Example Code

​```python
def is_eligible(item):
    return item.unused and item.days_since_purchase <= 30
​```
```

### Fixed chunker (chunk_tokens=64)

The table gets split across chunks. The code block gets cut in half. An embedding of half a table retrieves nothing useful.

### Structure-aware chunker

| Chunk | Section | Content |
|-------|---------|---------|
| 0 | Refund Policy | "Our refund policy allows returns within 30 days." |
| 1 | Fee Table | The complete table (all rows intact) |
| 2 | Example Code | The complete code block |

Each chunk is self-contained and tagged with its section. A query about fees retrieves the whole table.

## CLI

```bash
# Structure-aware (default)
ragforge chunk document.md --strategy structure --show-text

# Fixed with custom size
ragforge chunk document.md --strategy fixed --max-tokens 256

# Docling (for complex PDFs/DOCX)
ragforge chunk report.pdf --parser docling --strategy docling --show-text

# Choose a specific parser backend
ragforge chunk report.pdf --parser docling --strategy structure

# JSON output for scripting
ragforge chunk document.md --json
```

## API

```bash
curl -X POST http://localhost:8000/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "doc": {"text": "# Title\n\nContent...", "source": "x.md", "doc_type": "md", "metadata": {}, "id": "abc"},
    "strategy": "structure",
    "options": {"max_tokens": 384}
  }'
```

## Configuration

### Fixed Chunker Options

| Option | Default | Description |
|--------|---------|-------------|
| `chunk_tokens` | 256 | Target chunk size in tokens |
| `overlap_tokens` | 32 | Overlap between consecutive chunks |

### Structure Chunker Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_tokens` | 384 | Maximum tokens per chunk |
| `min_tokens` | 64 | Minimum tokens (avoids tiny chunks) |

## Chunk Metadata

Every chunk carries metadata about how it was created:

```python
chunk.metadata
# {
#   "strategy": "StructureChunker",
#   "section": "Fee Table",
#   "oversized": False,  # True if block exceeded max_tokens
# }
```

## Writing a Custom Chunker

```python
from ragforge.core.registry import register
from ragforge.chunking.base import Chunker

@register("chunker", "sentence")
class SentenceChunker(Chunker):
    """Split on sentence boundaries."""

    def chunk(self, document):
        import re
        sentences = re.split(r'(?<=[.!?])\s+', document.text)
        chunks = []
        for i, sent in enumerate(sentences):
            chunks.append(self._make_chunk(sent, document, i))
        return chunks
```
