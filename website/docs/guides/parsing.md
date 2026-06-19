---
sidebar_position: 1
---

# Parsing Documents

Parsing is treated as a first-class concern in RAGForge because garbage in = garbage out. The parsing module turns source files into clean `Document` objects with consistent structure.

## Supported Formats

| Format | Extensions | Dependencies | Notes |
|--------|-----------|--------------|-------|
| Plain text | `.txt`, `.text` | None | Read as-is |
| Markdown | `.md`, `.markdown` | None | Preserved for structure-aware chunking |
| HTML | `.html`, `.htm` | None (stdlib) | Tags stripped, scripts/styles removed |
| PDF | `.pdf` | `pypdf` (optional) | `pip install ragforge[pdf]` |

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
