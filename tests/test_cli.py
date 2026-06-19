"""Tests for the CLI."""

import pytest

from ragforge.cli import main, build_parser


class TestCLI:
    def test_info(self, capsys):
        ret = main(["info"])
        assert ret == 0
        output = capsys.readouterr().out
        assert "RAGForge" in output
        assert "parser" in output or "chunker" in output

    def test_parse(self, tmp_path, capsys):
        f = tmp_path / "test.txt"
        f.write_text("Hello from CLI test.")
        ret = main(["parse", str(f)])
        assert ret == 0
        output = capsys.readouterr().out
        assert "Hello from CLI test" in output

    def test_parse_json(self, tmp_path, capsys):
        f = tmp_path / "test.txt"
        f.write_text("JSON test.")
        ret = main(["parse", str(f), "--json"])
        assert ret == 0
        import json
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["text"] == "JSON test."

    def test_chunk(self, tmp_path, capsys):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nContent here.\n\n# Section 2\n\nMore content.")
        ret = main(["chunk", str(f), "--strategy", "structure"])
        assert ret == 0
        output = capsys.readouterr().out
        assert "chunks" in output.lower() or "chunk" in output.lower()

    def test_chunk_json(self, tmp_path, capsys):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nHello.")
        ret = main(["chunk", str(f), "--json"])
        assert ret == 0
        import json
        output = capsys.readouterr().out
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_parse_missing_file(self, capsys):
        ret = main(["parse", "/nonexistent/file.txt"])
        assert ret == 1

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_build_parser(self):
        p = build_parser()
        assert p.prog == "ragforge"
