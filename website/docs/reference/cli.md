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

---

### `ragforge parse`

Parse a file into clean text.

```bash
ragforge parse <path> [--parser PARSER] [--preview N] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `path` | (required) | File to parse |
| `--parser` | auto-detect | Parser backend: `text`, `html`, `pdf`, `docling` |
| `--preview` | 500 | Characters of text to show |
| `--json` | false | Output as JSON |

```bash
ragforge parse notes.md
ragforge parse report.pdf --parser docling --json
```

---

### `ragforge chunk`

Parse then chunk a file.

```bash
ragforge chunk <path> [--parser PARSER] [--strategy STRATEGY] [--max-tokens N] [--show-text] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `path` | (required) | File to chunk |
| `--parser` | auto-detect | Parser backend: `text`, `html`, `pdf`, `docling` |
| `--strategy` | `structure` | `fixed`, `structure`, or `docling` |
| `--max-tokens` | None | Target chunk size in tokens |
| `--show-text` | false | Print each chunk's text |
| `--json` | false | Output as JSON |

```bash
ragforge chunk notes.md --strategy structure --show-text
ragforge chunk report.pdf --parser docling --strategy docling --max-tokens 512
```

---

### `ragforge knowledge build`

Build a knowledge base from source files.

```bash
ragforge knowledge build <name> <sources...> [--strategy STRATEGY] [--parser PARSER] [--embedder MODEL] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `name` | (required) | Name for the knowledge base |
| `sources` | (required) | Files or directories to index |
| `--strategy` | `structure` | `fixed`, `structure`, or `docling` |
| `--parser` | auto-detect | Parser backend |
| `--embedder` | `default` | `default`, `sentence-transformers`, `openai` |
| `--json` | false | Output as JSON |

```bash
ragforge knowledge build my-kb ./docs/
ragforge knowledge build my-kb ./reports/ --parser docling --strategy docling
```

---

### `ragforge query`

Query a knowledge base.

```bash
ragforge query <knowledge> <question> [-k N] [--mode MODE] [--rerank] [--generate] [--llm PROVIDER] [--model MODEL] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `knowledge` | (required) | Knowledge base name |
| `question` | (required) | Question to ask |
| `-k` | 5 | Number of results |
| `--mode` | `hybrid` | `dense`, `bm25`, or `hybrid` |
| `--rerank` | false | Apply cross-encoder reranking |
| `--generate` | false | Generate a grounded answer using an LLM |
| `--llm` | None | LLM provider: `openai`, `anthropic`, `ollama` |
| `--model` | None | Override the default model |
| `--json` | false | Output as JSON |

```bash
ragforge query my-kb "How do refunds work?"
ragforge query my-kb "refund policy" --mode hybrid --rerank
ragforge query my-kb "shipping time" --generate --llm ollama
ragforge query my-kb "API limits" --generate --llm openai --model gpt-4o --json
```

---

### `ragforge eval`

Evaluate RAG quality. Has subcommands: `run`, `compare`, `bootstrap`.

#### `ragforge eval run`

Evaluate a KB against a golden dataset.

```bash
ragforge eval run <knowledge> <golden> [-k N] [--mode MODE] [--rerank] [--generate] [--llm PROVIDER] [--metrics METRICS] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `knowledge` | (required) | Knowledge base name |
| `golden` | (required) | Path to golden dataset (JSON) |
| `-k` | 5 | Top-k for retrieval |
| `--mode` | `hybrid` | Retrieval mode |
| `--rerank` | false | Apply reranking |
| `--generate` | false | Generate answers (for judge metrics) |
| `--llm` | None | LLM provider for generation + judge |
| `--metrics` | all retrieval | Comma-separated metric names |
| `--json` | false | Output as JSON |

```bash
ragforge eval run my-kb golden.json
ragforge eval run my-kb golden.json --metrics hit_rate,mrr --json
ragforge eval run my-kb golden.json --generate --llm ollama --metrics faithfulness
```

#### `ragforge eval compare`

A/B compare two KBs on the same golden set.

```bash
ragforge eval compare <knowledge_a> <knowledge_b> <golden> [-k N] [--mode MODE] [--rerank] [--metrics METRICS] [--json]
```

```bash
ragforge eval compare kb-structure kb-fixed golden.json
```

#### `ragforge eval bootstrap`

Generate a draft golden dataset from an existing KB.

```bash
ragforge eval bootstrap <knowledge> [--out FILE] [-n N] [--llm PROVIDER]
```

```bash
ragforge eval bootstrap my-kb --out golden_draft.json -n 20 --llm ollama
```

---

### `ragforge agents`

Multi-agent coordination. Has subcommands: `run`, `benchmark`, `board`.

#### `ragforge agents run`

Run a multi-agent task from a Python config file.

```bash
ragforge agents run <config> [--max-steps N] [--persist] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `config` | (required) | Path to agent config (.py file) |
| `--max-steps` | 50 | Maximum orchestration steps |
| `--persist` | false | Persist blackboard to disk |
| `--json` | false | Output as JSON |

```bash
ragforge agents run examples/multi_agent_coordination.py
ragforge agents run my_agents.py --persist --max-steps 20
```

#### `ragforge agents benchmark`

Compare direct-messaging vs blackboard coordination cost.

```bash
ragforge agents benchmark <config> [--max-steps N] [--json]
```

```bash
ragforge agents benchmark examples/multi_agent_coordination.py
```

#### `ragforge agents board`

Inspect a persisted blackboard.

```bash
ragforge agents board <name> [--json]
```

```bash
ragforge agents board my-task --json
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
| `--reload` | false | Auto-reload on code changes |

```bash
ragforge serve
ragforge serve --host 0.0.0.0 --port 9000 --reload
```

Requires: `pip install ragforge[api]`

---

### `ragforge ui`

Launch the local web dashboard (tracing, evaluation, chat).

```bash
ragforge ui [--host HOST] [--port PORT] [--no-browser]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Port number |
| `--no-browser` | false | Don't auto-open the browser |

```bash
ragforge ui
ragforge ui --port 9000 --no-browser
```

Requires: `pip install ragforge[ui]`
