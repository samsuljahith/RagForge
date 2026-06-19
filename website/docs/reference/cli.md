---
sidebar_position: 1
---

# CLI Reference

The `ragforge` command provides access to all features from the terminal.

## Global Options

```
ragforge --version    Show version and exit
ragforge --help       Show help
```

## Commands

### `ragforge info`

Show registered components and module status.

```bash
ragforge info
```

**Output:**
```
RAGForge v0.1.0

  parser      : html, pdf, text
  chunker     : fixed, structure
  embedding   : default, quantized
  store       : memory

Modules:
  core          ✓  shared data models + plugin registry
  parsing       ✓  txt / md / html / pdf -> Document
  chunking      ✓  fixed + structure-aware -> Chunks
  pipeline      ✓  embed + store + hybrid search + rerank
  evaluation    ✓  precision / recall / faithfulness
  quantization  ✓  quantize + compare cost/quality
  migration     ✓  re-embed + validate + swap models
  api           ✓  HTTP/JSON API (ragforge serve)
```

---

### `ragforge parse`

Parse a file into clean text.

```bash
ragforge parse <path> [--preview N] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `path` | (required) | File to parse (.txt .md .html .pdf) |
| `--preview` | 500 | Characters of text to show |
| `--json` | false | Output as JSON |

**Examples:**
```bash
ragforge parse notes.md
ragforge parse report.pdf --preview 1000
ragforge parse page.html --json
```

---

### `ragforge chunk`

Parse then chunk a file.

```bash
ragforge chunk <path> [--strategy STRATEGY] [--max-tokens N] [--show-text] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `path` | (required) | File to chunk |
| `--strategy` | `structure` | `fixed` or `structure` |
| `--max-tokens` | None | Target chunk size in tokens |
| `--show-text` | false | Print each chunk's text |
| `--json` | false | Output as JSON array |

**Examples:**
```bash
ragforge chunk notes.md --strategy structure --show-text
ragforge chunk notes.md --strategy fixed --max-tokens 256
ragforge chunk report.pdf --json
```

---

### `ragforge knowledge build`

Build a knowledge base from source files.

```bash
ragforge knowledge build <name> <sources...> [--strategy STRATEGY] [--embedding-model MODEL] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `name` | (required) | Name for the knowledge base |
| `sources` | (required) | Files or directories to index |
| `--strategy` | `structure` | Chunking strategy |
| `--embedding-model` | `default` | Embedding model |
| `--json` | false | Output as JSON |

**Examples:**
```bash
ragforge knowledge build my-kb ./docs/ ./policies/
ragforge knowledge build my-kb data.md --strategy fixed --json
```

---

### `ragforge knowledge query`

Query a knowledge base.

```bash
ragforge knowledge query <name> <question> [--top-k N] [--no-rerank] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `name` | (required) | Knowledge base name |
| `question` | (required) | Question to ask |
| `--top-k` | 5 | Number of results |
| `--no-rerank` | false | Skip reranking |
| `--json` | false | Output as JSON |

**Examples:**
```bash
ragforge knowledge query my-kb "How do refunds work?"
ragforge knowledge query my-kb "shipping time" --top-k 3 --json
```

---

### `ragforge serve`

Start the HTTP/JSON API server.

```bash
ragforge serve [--host HOST] [--port PORT] [--reload]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Port number |
| `--reload` | false | Auto-reload on code changes (dev mode) |

**Examples:**
```bash
ragforge serve
ragforge serve --host 0.0.0.0 --port 9000
ragforge serve --reload  # development
```

Requires: `pip install ragforge[api]`
