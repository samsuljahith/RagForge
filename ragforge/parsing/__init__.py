"""Parsing: turn source files (txt, md, html, pdf) into clean Documents."""

# importing the concrete parsers registers them in the registry
from ragforge.parsing.text_parser import (
    HtmlParser,
    PdfParser,
    TextParser,
    parse_file,
)
from ragforge.parsing.docling_parser import DoclingParser

__all__ = ["TextParser", "HtmlParser", "PdfParser", "DoclingParser", "parse_file"]
