#!/usr/bin/env python3
"""
Example: Docling vs Default parsing and chunking.

This script demonstrates the difference between RAGForge's built-in lightweight
parser/chunker and the Docling-powered backend on a document with tables and
structured content.

The key insight: the default parser works great for simple text/markdown, but
Docling shines on complex documents (PDFs with tables, multi-column layouts,
slides, spreadsheets) where layout analysis matters.

Requirements:
    pip install ragforge[docling]

Usage:
    python examples/docling_vs_default.py

    # Or via CLI:
    ragforge parse examples/sample_with_table.html --parser docling
    ragforge chunk examples/sample_with_table.html --parser docling --strategy docling --show-text
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# ─── Create a sample document with a table (simulates a complex PDF) ───────────

SAMPLE_HTML = """\
<html>
<body>
<h1>Q3 2025 Revenue Report</h1>
<p>This report summarizes revenue across product lines for Q3 2025.
Growth was driven primarily by the Enterprise tier.</p>

<h2>Revenue by Product</h2>
<table>
  <thead>
    <tr><th>Product</th><th>Q2 Revenue</th><th>Q3 Revenue</th><th>Growth</th></tr>
  </thead>
  <tbody>
    <tr><td>Starter</td><td>$1.2M</td><td>$1.4M</td><td>+16%</td></tr>
    <tr><td>Pro</td><td>$4.8M</td><td>$5.1M</td><td>+6%</td></tr>
    <tr><td>Enterprise</td><td>$12.0M</td><td>$15.3M</td><td>+28%</td></tr>
    <tr><td>Total</td><td>$18.0M</td><td>$21.8M</td><td>+21%</td></tr>
  </tbody>
</table>

<h2>Key Takeaways</h2>
<ul>
  <li>Enterprise grew 28% QoQ, driven by 3 new Fortune 500 contracts</li>
  <li>Pro tier showing signs of saturation — consider pricing review</li>
  <li>Starter tier healthy but small — focus on conversion to Pro</li>
</ul>

<h2>Technical Appendix</h2>
<pre><code>
# Revenue calculation methodology
def calculate_growth(q2: float, q3: float) -> float:
    return (q3 - q2) / q2 * 100

# Applied per-product with currency normalization
for product in products:
    product.growth = calculate_growth(product.q2_revenue, product.q3_revenue)
</code></pre>
</body>
</html>
"""


def run_default(html_path: Path) -> None:
    """Parse and chunk using RAGForge's built-in default backend."""
    from ragforge.parsing import parse_file
    from ragforge.chunking import chunk_document

    print("=" * 70)
    print("DEFAULT BACKEND (built-in, zero dependencies)")
    print("=" * 70)

    # Parse
    doc = parse_file(html_path)
    print(f"\nParsed: {doc.source}")
    print(f"Type: {doc.doc_type} | Tokens: ~{doc.token_count}")
    print(f"Text preview (first 200 chars):")
    print(f"  {doc.text[:200]}...")

    # Chunk with structure-aware strategy
    chunks = chunk_document(doc, strategy="structure", max_tokens=256)
    print(f"\nChunks (structure strategy): {len(chunks)}")
    print("-" * 50)
    for c in chunks:
        section = c.metadata.get("section", "(top)")
        oversized = " [OVERSIZED]" if c.metadata.get("oversized") else ""
        print(f"  [Chunk {c.index}] ~{c.token_count} tok | section: {section}{oversized}")
        # Show if table content is intact or split
        if "Revenue" in c.text and "|" in c.text or "$" in c.text:
            print(f"    → Contains table data: YES")
        print(f"    → First 100 chars: {c.text[:100]}")
        print()


def run_docling(html_path: Path) -> None:
    """Parse and chunk using the Docling backend."""
    from ragforge.core.registry import get

    print("\n")
    print("=" * 70)
    print("DOCLING BACKEND (pip install ragforge[docling])")
    print("=" * 70)

    # Parse with Docling
    parser = get("parser", "docling")()
    doc = parser.parse(html_path)
    print(f"\nParsed: {doc.source}")
    print(f"Type: {doc.doc_type} | Tokens: ~{doc.token_count}")
    print(f"Parser: {doc.metadata.get('parser', 'unknown')}")
    print(f"Text preview (first 200 chars):")
    print(f"  {doc.text[:200]}...")

    # Chunk with Docling's structure-aware chunker
    chunker = get("chunker", "docling")(max_tokens=256)
    chunks = chunker.chunk(doc)
    print(f"\nChunks (docling strategy): {len(chunks)}")
    print("-" * 50)
    for c in chunks:
        section = c.metadata.get("section", "(unknown)")
        page = c.metadata.get("page", "?")
        print(f"  [Chunk {c.index}] ~{c.token_count} tok | section: {section} | page: {page}")
        # Check if tables stay intact
        if "$" in c.text or "Revenue" in c.text:
            lines = c.text.strip().split("\n")
            table_lines = [l for l in lines if "|" in l or "$" in l]
            if len(table_lines) >= 3:
                print(f"    → TABLE INTACT ({len(table_lines)} rows preserved together)")
        print(f"    → First 100 chars: {c.text[:100]}")
        print()


def main() -> int:
    # Write sample HTML to a temp file
    tmp = Path(tempfile.mkdtemp()) / "revenue_report.html"
    tmp.write_text(SAMPLE_HTML)
    print(f"Sample document: {tmp}\n")

    # Always run the default backend (no extra deps needed)
    run_default(tmp)

    # Try Docling — skip gracefully if not installed
    try:
        import docling  # noqa: F401
        run_docling(tmp)
    except ImportError:
        print("\n")
        print("=" * 70)
        print("DOCLING BACKEND — SKIPPED (not installed)")
        print("=" * 70)
        print()
        print("To see the Docling comparison, install it:")
        print("  pip install ragforge[docling]")
        print()
        print("Then re-run this example:")
        print("  python examples/docling_vs_default.py")

    # Summary
    print("\n")
    print("─" * 70)
    print("SUMMARY")
    print("─" * 70)
    print("""
┌─────────────────────┬────────────────────────────────────────────────────┐
│ Default backend     │ Docling backend                                    │
├─────────────────────┼────────────────────────────────────────────────────┤
│ Zero dependencies   │ Requires: pip install ragforge[docling]             │
│ Fast, lightweight   │ Slower (layout analysis, OCR)                      │
│ Good for txt/md     │ Best for PDF, DOCX, PPTX, images                  │
│ May split tables    │ Keeps tables/code blocks intact                    │
│ No page metadata    │ Rich metadata (page, section hierarchy)            │
│ No OCR             │ OCR for scanned documents                           │
└─────────────────────┴────────────────────────────────────────────────────┘

Choose based on your documents:
  • Simple markdown/text → default (fast, no deps)
  • Complex PDFs, reports with tables → docling (accurate, heavy)
  • Mix → use docling only where needed via --parser docling
""")

    # Clean up
    tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
