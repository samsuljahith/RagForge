Run or extend a RAGForge benchmark honestly.

1. Use a real, recognized dataset (e.g. a small BEIR dataset) with real relevance labels — never invent a golden set.
2. Use real embedding models; keep the corpus small enough to finish on normal hardware.
3. Compute the real metrics (recall@k, precision@k, MRR) and save results to benchmarks/ as JSON + an honest
   markdown summary.
4. Report the ACTUAL numbers, whatever they are. Never fabricate or round-to-flatter. A regression caught is a
   valid, valuable result.
