---
sidebar_position: 99
---

# Contributing

RAGForge is open source (Apache-2.0) and welcomes contributions.

## Development Setup

```bash
git clone https://github.com/ragforge/ragforge.git
cd ragforge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[api,dev]"
```

## Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_parsing.py

# With coverage
pytest --cov=ragforge
```

## Adding a New Parser

1. Create `ragforge/parsing/your_parser.py`
2. Subclass `Parser` and register it:

```python
from ragforge.core.registry import register
from ragforge.parsing.base import Parser

@register("parser", "docx")
class DocxParser(Parser):
    extensions = {".docx"}

    def parse(self, path):
        # Your implementation
        ...
```

3. Import it in `ragforge/parsing/__init__.py`
4. Add a test in `tests/test_parsing.py`
5. Done — it's automatically available in CLI, API, and library

## Adding a New Chunker

Same pattern:

1. Create `ragforge/chunking/your_chunker.py`
2. Subclass `Chunker` and register it
3. Import in `ragforge/chunking/__init__.py`
4. Add tests

## Code Style

- Python 3.9+ compatible
- Type hints encouraged
- Docstrings on all public classes and functions
- Run `ruff check .` before committing

## Project Structure

```
ragforge/
├── core/           # Shared models + registry (stable, rarely changes)
├── parsing/        # File -> Document
├── chunking/       # Document -> Chunks
├── pipeline/       # Embed + store + retrieve
├── evaluation/     # Measure quality
├── quantization/   # Compress + compare
├── migration/      # Swap models safely
├── api/            # HTTP/JSON endpoints
└── cli.py          # Command-line interface
```

## Pull Request Guidelines

- One feature per PR
- Include tests
- Update docs if adding user-facing features
- Keep the core install dependency-free (heavy deps go in extras)

## Code of Conduct

Be kind. Be constructive. We're all here to build something useful.

## License

Apache-2.0. Your contributions are licensed under the same terms.
