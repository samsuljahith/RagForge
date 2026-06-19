---
sidebar_position: 2
---

# Installation

RAGForge is pip-installable with optional extras for heavier features.

## Core Install

The core package has **zero dependencies** and gives you parsing, chunking, and the CLI:

```bash
pip install ragforge
```

## Optional Extras

Install only what you need:

```bash
# API server (FastAPI + Uvicorn)
pip install ragforge[api]

# PDF parsing support
pip install ragforge[pdf]

# Everything
pip install ragforge[all]
```

### Available Extras

| Extra | What it adds | Dependencies |
|-------|-------------|--------------|
| `[api]` | HTTP/JSON API server, interactive docs | FastAPI, Uvicorn, Pydantic |
| `[pdf]` | PDF file parsing | pypdf |
| `[pipeline]` | Production embedding models | sentence-transformers |
| `[all]` | All of the above | Everything |
| `[dev]` | Development tools | pytest, httpx, ruff |

## Development Install

For contributing or running from source:

```bash
git clone https://github.com/ragforge/ragforge.git
cd ragforge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[api,dev]"
```

## Docker

Run the API server as a container:

```bash
docker build -t ragforge .
docker run -p 8000:8000 ragforge
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

## Verify Installation

```bash
ragforge info
```

You should see the registered parsers, chunkers, and module status.

## Requirements

- Python 3.9 or later
- No other system dependencies for the core install
