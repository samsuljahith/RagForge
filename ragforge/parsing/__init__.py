"""Parsing: turn source files (txt, md, html, pdf) into clean Documents."""

# importing the concrete parsers registers them in the registry
from ragforge.parsing.text_parser import (
    HtmlParser,
    PdfParser,
    TextParser,
    parse_file,
)

__all__ = ["TextParser", "HtmlParser", "PdfParser", "parse_file"]
