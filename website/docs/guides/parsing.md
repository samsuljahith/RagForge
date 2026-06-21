---
sidebar_position: 1
---

# Parsing Documents

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="110" viewBox="0 0 550 110">
  <rect x="10" y="15" width="45" height="22" rx="4" fill="#1a1a24" stroke="#f87171" strokeWidth="1"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="32" y="29" textAnchor="middle" fontSize="6" fill="#f87171">.pdf</text>
  <rect x="10" y="42" width="45" height="22" rx="4" fill="#1a1a24" stroke="#60a5fa" strokeWidth="1"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
  <text x="32" y="56" textAnchor="middle" fontSize="6" fill="#60a5fa">.html</text>
  <rect x="10" y="69" width="45" height="22" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"><animate attributeName="opacity" values="1;0.7;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="32" y="83" textAnchor="middle" fontSize="6" fill="#34d399">.md</text>
  <rect x="80" y="30" width="80" height="45" rx="8" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="120" y="50" textAnchor="middle" fontSize="8" fontWeight="700" fill="#ff6b2c">Auto-detect</text>
  <text x="120" y="63" textAnchor="middle" fontSize="6" fill="#6a6a80">by extension</text>
  <rect x="195" y="30" width="80" height="45" rx="8" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1.5"/>
  <text x="235" y="48" textAnchor="middle" fontSize="7" fontWeight="600" fill="#7c6ff8">Clean text</text>
  <text x="235" y="60" textAnchor="middle" fontSize="6" fill="#a78bfa">+ metadata</text>
  <text x="235" y="72" textAnchor="middle" fontSize="6" fill="#6a6a80">~token count</text>
  <rect x="310" y="30" width="90" height="45" rx="8" fill="#1a1a24" stroke="#34d399" strokeWidth="2"/>
  <text x="355" y="48" textAnchor="middle" fontSize="8" fontWeight="700" fill="#34d399">Document</text>
  <text x="355" y="60" textAnchor="middle" fontSize="6" fill="#34d399">ready for chunking</text>
  <rect x="435" y="35" width="70" height="35" rx="6" fill="#1a1a24" stroke="#a78bfa" strokeWidth="1" strokeDasharray="3,2"/>
  <text x="470" y="50" textAnchor="middle" fontSize="6" fill="#a78bfa">Optional:</text>
  <text x="470" y="62" textAnchor="middle" fontSize="7" fontWeight="600" fill="#a78bfa">Docling</text>
  <circle r="3" fill="#f87171"><animateMotion dur="1.3s" repeatCount="indefinite" path="M57,26 L78,45"/></circle>
  <circle r="3" fill="#60a5fa"><animateMotion dur="1.5s" repeatCount="indefinite" path="M57,53 L78,52"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.7s" repeatCount="indefinite" path="M57,80 L78,60"/></circle>
  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M162,52 L193,52"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.3s" repeatCount="indefinite" path="M277,52 L308,52"/></circle>
  <text x="275" y="100" textAnchor="middle" fontSize="7" fill="#6a6a80">Any file → auto-detected parser → clean Document object with text + metadata</text>
</svg>
</div>

Parsing is treated as a first-class concern in RAGForge because garbage in = garbage out. The parsing module turns source files into clean `Document` objects with consistent structure.

## Supported Formats

| Format | Extensions | Dependencies | Notes |
|--------|-----------|--------------|-------|
| Plain text | `.txt`, `.text` | None | Read as-is |
| Markdown | `.md`, `.markdown` | None | Preserved for structure-aware chunking |
| HTML | `.html`, `.htm` | None (stdlib) | Tags stripped, scripts/styles removed |
| PDF | `.pdf` | `pypdf` (optional) | `pip install ragforge[pdf]` |
| **Docling** | `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, images | `docling` (optional) | `pip install ragforge[docling]` — heavy but accurate |

## Basic Usage

### Auto-Detection

The simplest way — RAGForge picks the right parser by file extension:

```python
from ragforge.parsing import parse_file

doc = parse_file("report.md")
# doc.text = "# Report Title\n\nContent..."
# doc.doc_type = "md"
# doc.source = "report.md"
# doc.token_count = ~estimated tokens
```

### CLI

```bash
ragforge parse document.html
ragforge parse document.html --preview 1000
ragforge parse document.html --json
```

### API

```bash
# Parse a server-side file
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"path": "/data/report.md"}'

# Parse raw text
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "<p>Hello world</p>", "doc_type": "html"}'
```

## HTML Parsing

The HTML parser strips all tags and extracts visible text using only the standard library (no BeautifulSoup needed):

- Removes `<script>` and `<style>` content
- Converts block tags (`<p>`, `<div>`, `<h1>`-`<h6>`) to line breaks
- Collapses excessive whitespace

```python
doc = parse_file("page.html")
# Input:  <html><script>var x=1;</script><h1>Title</h1><p>Content</p></html>
# Output: "Title\nContent"
```

## PDF Parsing

PDF support is optional to keep the core install light:

```bash
pip install ragforge[pdf]
```

```python
doc = parse_file("paper.pdf")
print(doc.metadata)  # {"filename": "paper.pdf", "pages": 12}
```

If `pypdf` isn't installed, you get a clear error message telling you how to enable it — not a confusing traceback.

## Docling Backend (Advanced)

For complex documents — multi-column PDFs, files with tables, Office docs (DOCX/PPTX/XLSX), or scanned images — RAGForge integrates IBM's [Docling](https://github.com/DS4SD/docling) library as an optional backend.

### When to Use Docling

| Scenario | Use |
|----------|-----|
| Simple markdown / text files | Default parser (fast, zero deps) |
| Basic PDFs with text only | Default `pdf` parser (pypdf) |
| PDFs with tables, complex layouts | **Docling** |
| DOCX, PPTX, XLSX files | **Docling** |
| Scanned documents / images | **Docling** (has OCR) |

### Installation

```bash
pip install ragforge[docling]
```

:::caution
Docling is a heavyweight dependency (~1GB+ with models). Only install it if you actually need it for complex documents. The default parser handles simple files perfectly.
:::

### Usage

Docling is an **explicit-choice** backend — you must request it by name. It never activates automatically.

**CLI:**
```bash
ragforge parse report.pdf --parser docling
ragforge chunk report.pdf --parser docling --strategy docling --show-text
```

**Python:**
```python
from ragforge.core.registry import get

# Parse with Docling (full layout analysis)
parser = get("parser", "docling")()
doc = parser.parse("quarterly_report.pdf")

# Chunk with Docling (structure-aware, keeps tables intact)
chunker = get("chunker", "docling")(max_tokens=384)
chunks = chunker.chunk(doc)

for c in chunks:
    print(f"[{c.metadata.get('section')}] page {c.metadata.get('page')} — {c.token_count} tok")
```

**API:**
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"path": "/data/report.pdf", "parser": "docling"}'

curl -X POST http://localhost:8000/chunk \
  -H "Content-Type: application/json" \
  -d '{"doc": {...}, "strategy": "docling", "options": {"max_tokens": 384}}'
```

### Docling vs Default: What's Different

**Parsing:** Docling uses layout analysis to understand document structure — columns, headers, tables, figures — then exports clean markdown. The default parser just extracts raw text.

**Chunking:** Docling's chunker uses the structured document hierarchy to split at natural boundaries (sections, pages). It carries richer metadata: page numbers, heading hierarchy, content type. The default structure chunker infers structure from markdown syntax.

**Best combo:** Use `--parser docling --strategy docling` together. The docling chunker works best when given a document parsed by the docling parser (which provides the full structured representation). If you use the docling chunker on a document parsed by the default parser, it falls back to the built-in structure chunker with a warning.

### Supported Formats

| Format | Extensions |
|--------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |
| Excel | `.xlsx` |
| HTML | `.html`, `.htm` |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp` |

### Metadata

The Docling parser produces richer metadata than the defaults:

| Field | Description |
|-------|-------------|
| `filename` | Source filename |
| `parser` | Always `"docling"` |
| `_docling_doc` | Internal structured document (used by docling chunker) |

## Writing a Custom Parser

Add a new parser by creating one file:

```python
# ragforge/parsing/docx_parser.py

from pathlib import Path
from ragforge.core.registry import register
from ragforge.core.models import Document
from ragforge.parsing.base import Parser

@register("parser", "docx")
class DocxParser(Parser):
    extensions = {".docx"}

    def parse(self, path: str | Path) -> Document:
        # Your parsing logic here
        from docx import Document as DocxDoc
        p = Path(path)
        doc = DocxDoc(str(p))
        text = "\n\n".join(para.text for para in doc.paragraphs)
        return Document(
            text=text,
            source=str(p),
            doc_type="docx",
            metadata={"filename": p.name},
        )
```

Import it in `parsing/__init__.py` and it's immediately available in the CLI, API, and library.

## Metadata

Each parser attaches useful metadata:

| Parser | Metadata fields |
|--------|----------------|
| Text/MD | `filename`, `bytes` |
| HTML | `filename` |
| PDF | `filename`, `pages` |
| Docling | `filename`, `parser`, page numbers, section hierarchy (via chunker) |
