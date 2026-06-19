"""
Concrete parsers.

- TextParser:     plain .txt and .md (markdown kept as-is; structure-aware chunking
                  will use the markdown headers later)
- HtmlParser:     strips tags using only the standard library (no heavy deps)
- PdfParser:      optional — uses pypdf IF installed, otherwise gives a clear,
                  friendly message instead of crashing

Design choice: the core install stays light. PDF support is optional because PDF
libraries are heavy, and not every user needs them. Users who want PDFs run
`pip install ragforge[pdf]` and it just works.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from ragforge.core.models import Document
from ragforge.core.registry import register
from ragforge.parsing.base import Parser


@register("parser", "text")
class TextParser(Parser):
    """Handles plain text and markdown. Reads the file and returns its content as-is."""

    extensions = {".txt", ".md", ".markdown", ".text"}

    def parse(self, path: str | Path) -> Document:
        p = Path(path)
        text = p.read_text(encoding="utf-8", errors="replace")
        doc_type = "md" if p.suffix.lower() in {".md", ".markdown"} else "txt"
        return Document(
            text=text,
            source=str(p),
            doc_type=doc_type,
            metadata={"filename": p.name, "bytes": p.stat().st_size},
        )


class _TagStripper(HTMLParser):
    """Collects visible text from HTML, skipping <script>/<style> content."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"script", "style"}:
            self._skip = True
        # treat block tags as line breaks so text doesn't all run together
        if tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        # collapse excessive blank lines
        lines = [ln.strip() for ln in raw.splitlines()]
        out: list[str] = []
        for ln in lines:
            if ln or (out and out[-1]):  # keep single blank lines, drop runs
                out.append(ln)
        return "\n".join(out).strip()


@register("parser", "html")
class HtmlParser(Parser):
    """Strips HTML tags to plain text using only the standard library."""

    extensions = {".html", ".htm"}

    def parse(self, path: str | Path) -> Document:
        p = Path(path)
        raw = p.read_text(encoding="utf-8", errors="replace")
        stripper = _TagStripper()
        stripper.feed(raw)
        return Document(
            text=stripper.text(),
            source=str(p),
            doc_type="html",
            metadata={"filename": p.name},
        )


@register("parser", "pdf")
class PdfParser(Parser):
    """
    Extracts text from PDFs using pypdf (optional dependency).

    If pypdf isn't installed, raises a clear message telling the user how to enable it,
    instead of a confusing ImportError deep in a traceback.
    """

    extensions = {".pdf"}

    def parse(self, path: str | Path) -> Document:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError(
                "PDF support needs the 'pypdf' package. "
                "Install it with:  pip install ragforge[pdf]   (or: pip install pypdf)"
            ) from exc

        p = Path(path)
        reader = PdfReader(str(p))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(pages).strip()
        return Document(
            text=text,
            source=str(p),
            doc_type="pdf",
            metadata={"filename": p.name, "pages": len(pages)},
        )


# --- convenience: pick the right parser automatically ---------------------------

def parse_file(path: str | Path) -> Document:
    """
    Auto-detect the right parser by file extension and parse the file.

    This is the function most users will call. It hides the parser selection so you
    can just say parse_file('whatever.pdf') and get a Document back.
    """
    from ragforge.core.registry import available, get

    p = Path(path)
    for name in available("parser"):
        parser = get("parser", name)()
        if parser.supports(p):
            return parser.parse(p)
    raise ValueError(
        f"No parser supports '{p.suffix}'. Supported types: "
        + ", ".join(sorted({e for n in available('parser') for e in get('parser', n).extensions}))
    )
