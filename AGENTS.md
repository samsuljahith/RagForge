---
description: 
alwaysApply: true
---

# RAGForge — Agent Instructions

You are working on RAGForge, an open-source RAG + multi-agent toolkit (Python). It's usable as a library,
an HTTP API (FastAPI), and a CLI. Modules: parsing, chunking, retrieval/pipeline, generation, evaluation,
quantization, migration (incl. the decision gate), coordination, and a local UI. ~299 tests.

## Core principles
- HONESTY OVER HYPE. Never add hardcoded performance claims, fake benchmark numbers, or marketing language to
  code, docstrings, examples, or README. The only numbers that appear are ones produced by a real run.
- Match the existing architecture: clean modular design, plugin registry (parsers/chunkers/embedders
  self-register), light core with heavy deps as optional extras. Don't introduce heavy dependencies without
  strong reason.
- Every feature must work across all three surfaces where relevant: library, HTTP API, CLI. Keep them consistent.

## Code style
- Python, type hints throughout, clear docstrings. Prefer stdlib over new dependencies.
- Preserve the existing patterns — read neighboring files before adding code so new code matches conventions.
- Use plain dash "-", not em dash, in comments and docs.

## Testing (required)
- Every new feature or fix needs tests. Use mocked embedders/LLMs in tests — never download real models in CI.
- Before finishing any task, run `pytest tests/ -q` and confirm no regressions (baseline: ~299 passed, 3 skipped).
- When fixing a bug, first reproduce it with a failing test, then fix, then confirm the test passes.

## Examples must be honest
- Every script in examples/ must produce output that actually supports what it claims to demonstrate.
  No scenario heading that the numbers contradict. No claim the code doesn't back up.

## When making technical decisions
- Prioritize correctness, simplicity, and maintainability over cleverness or raw speed.
- If a change would make a public claim (README/site) true or false, flag it. Code and claims must match.
- Verify CLI commands and API endpoints against the actual code (cli.py, api/routes/) — never invent flags
  or endpoints in docs or examples.

## Scope discipline
- RAGForge owns the RAG pipeline + the migration *decision* (is a new model worth it) + evaluation.
- It does NOT own enterprise operational rollout (dual-write orchestration, multi-env deployment, ACL/permissions
  mapping, ingestion-connector syncing). Don't add those — they're out of scope by design.
