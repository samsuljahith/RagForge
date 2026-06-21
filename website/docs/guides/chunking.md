---
sidebar_position: 2
---

# Chunking

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="120" viewBox="0 0 550 120">
  <rect x="10" y="30" width="70" height="55" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"/>
  <text x="45" y="48" textAnchor="middle" fontSize="7" fontWeight="600" fill="#ff6b2c">Document</text>
  <rect x="18" y="55" width="54" height="8" rx="2" fill="#7c6ff8" opacity="0.3"/><text x="45" y="62" textAnchor="middle" fontSize="5" fill="#a78bfa"># Header</text>
  <rect x="18" y="66" width="54" height="8" rx="2" fill="#34d399" opacity="0.3"/><text x="45" y="73" textAnchor="middle" fontSize="5" fill="#34d399">table</text>
  <rect x="18" y="77" width="54" height="8" rx="2" fill="#22d3ee" opacity="0.3"/><text x="45" y="84" textAnchor="middle" fontSize="5" fill="#22d3ee">code</text>
  <rect x="115" y="20" width="80" height="35" rx="8" fill="#1a1a24" stroke="#34d399" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="155" y="38" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Structure</text>
  <text x="155" y="49" textAnchor="middle" fontSize="6" fill="#6a6a80">context-first</text>
  <rect x="115" y="65" width="80" height="35" rx="8" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1.5"/>
  <text x="155" y="83" textAnchor="middle" fontSize="7" fontWeight="600" fill="#fbbf24">Fixed</text>
  <text x="155" y="94" textAnchor="middle" fontSize="6" fill="#6a6a80">sliding window</text>
  <rect x="240" y="10" width="100" height="28" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"><animate attributeName="opacity" values="1;0.6;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="290" y="24" textAnchor="middle" fontSize="6" fontWeight="600" fill="#34d399">Chunk 1 [Header]</text>
  <text x="290" y="33" textAnchor="middle" fontSize="5" fill="#6a6a80">paragraph ✓</text>
  <rect x="240" y="44" width="100" height="28" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"><animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="290" y="58" textAnchor="middle" fontSize="6" fontWeight="600" fill="#34d399">Chunk 2 [Section]</text>
  <text x="290" y="67" textAnchor="middle" fontSize="5" fill="#6a6a80">TABLE intact ✓</text>
  <rect x="240" y="78" width="100" height="28" rx="5" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"><animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite"/></rect>
  <text x="290" y="92" textAnchor="middle" fontSize="6" fontWeight="600" fill="#34d399">Chunk 3 [Section]</text>
  <text x="290" y="101" textAnchor="middle" fontSize="5" fill="#6a6a80">CODE intact ✓</text>
  <rect x="380" y="35" width="90" height="45" rx="8" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="2"/>
  <text x="425" y="53" textAnchor="middle" fontSize="7" fontWeight="700" fill="#7c6ff8">Each chunk</text>
  <text x="425" y="65" textAnchor="middle" fontSize="6" fill="#a78bfa">tagged with section</text>
  <text x="425" y="75" textAnchor="middle" fontSize="6" fill="#6a6a80">+ token count</text>
  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M82,55 L113,37"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.5s" repeatCount="indefinite" path="M197,37 L238,24"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.8s" repeatCount="indefinite" path="M197,37 L238,58"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="2s" repeatCount="indefinite" path="M197,37 L238,92"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.5s" repeatCount="indefinite" path="M342,55 L378,55"/></circle>
  <text x="275" y="115" textAnchor="middle" fontSize="7" fill="#6a6a80">Document → analyze structure → split at boundaries → tagged chunks (tables/code never cut)</text>
</svg>
</div>

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
