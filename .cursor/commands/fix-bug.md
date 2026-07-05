Fix a bug in RAGForge using test-driven debugging.

1. Reproduce the bug first with a FAILING test that captures the real problem.
2. Find the root cause (read the actual code path, don't guess).
3. Fix it.
4. Confirm the failing test now passes, and run `pytest tests/ -q` to confirm no regressions.
5. Explain the root cause and the fix in plain language.
