"""Tests for the parsing module."""

import tempfile
from pathlib import Path

import pytest

from ragforge.parsing import parse_file
from ragforge.parsing.text_parser import TextParser, HtmlParser


class TestTextParser:
    def test_parse_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello, world!")
        doc = parse_file(str(f))
        assert doc.text == "Hello, world!"
        assert doc.doc_type == "txt"
        assert doc.source == str(f)

    def test_parse_md(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nContent here.")
        doc = parse_file(str(f))
        assert doc.doc_type == "md"
        assert "# Title" in doc.text

    def test_metadata(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("data")
        doc = parse_file(str(f))
        assert "filename" in doc.metadata
        assert doc.metadata["filename"] == "test.txt"


class TestHtmlParser:
    def test_strips_tags(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body><h1>Title</h1><p>Content</p></body></html>")
        doc = parse_file(str(f))
        assert doc.doc_type == "html"
        assert "Title" in doc.text
        assert "Content" in doc.text
        assert "<h1>" not in doc.text

    def test_strips_script(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><script>var x=1;</script><p>Visible</p></html>")
        doc = parse_file(str(f))
        assert "var x=1" not in doc.text
        assert "Visible" in doc.text

    def test_strips_style(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><style>body{color:red}</style><p>Text</p></html>")
        doc = parse_file(str(f))
        assert "color:red" not in doc.text
        assert "Text" in doc.text


class TestParseFile:
    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("stuff")
        with pytest.raises(ValueError, match="No parser supports"):
            parse_file(str(f))

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_file("/nonexistent/file.txt")

    def test_auto_detect_html(self, tmp_path):
        f = tmp_path / "page.htm"
        f.write_text("<p>Hello</p>")
        doc = parse_file(str(f))
        assert doc.doc_type == "html"
