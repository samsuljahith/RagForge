Add a new feature to RAGForge following the project's conventions.

1. First read neighboring files in the relevant module to match existing patterns.
2. Implement the feature in the appropriate module (respect the plugin registry pattern if adding a
   parser/chunker/embedder).
3. Expose it consistently across all relevant surfaces: Python library, HTTP API (api/routes/), and CLI (cli.py).
4. Write tests in tests/ using mocked embedders/LLMs (never download real models).
5. Run `pytest tests/ -q` and confirm no regressions (baseline ~299 passed, 3 skipped).
6. HONESTY CHECK: add no fake numbers or marketing claims. If this changes a README/site claim, flag it.
7. Summarize what changed per file.
