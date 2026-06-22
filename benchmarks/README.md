# Migration Decision Gate Benchmark

Real benchmark using a public retrieval dataset with human relevance labels.

## Setup

- **Dataset**: scifact (via BeIR / Hugging Face datasets)
- **Corpus size**: 5183 documents
- **Queries**: 300 queries with human relevance judgments
- **Model A (baseline)**: `sentence-transformers/all-MiniLM-L6-v2`
- **Model B (candidate)**: `sentence-transformers/paraphrase-MiniLM-L3-v2`
- **Date**: 2026-06-22

Each document is treated as one chunk (no re-chunking) so the BEIR qrels
map directly to chunk IDs. This gives an honest retrieval comparison.

## Results

### k=5

| Metric | Model A | Model B | Delta |
|--------|---------|---------|-------|
| recall_at_k | 0.7379 | 0.5751 | -0.1628 |
| precision_at_k | 0.1640 | 0.1260 | -0.0380 |
| mrr | 0.5997 | 0.4682 | -0.1315 |

**Gate verdict: NO_GO**

Reason: New model regresses recall_at_k: 0.7379 → 0.5751 (delta: -0.1628, exceeds margin 0.0)

### k=10

| Metric | Model A | Model B | Delta |
|--------|---------|---------|-------|
| recall_at_k | 0.7833 | 0.6489 | -0.1344 |
| precision_at_k | 0.0883 | 0.0730 | -0.0153 |
| mrr | 0.6047 | 0.4772 | -0.1275 |

**Gate verdict: NO_GO**

Reason: New model regresses recall_at_k: 0.7833 → 0.6489 (delta: -0.1344, exceeds margin 0.0)

## Interpretation

These are real numbers from a real retrieval benchmark. The decision gate
uses recall@k as the primary metric (configurable). If the candidate model
regresses on recall, the gate blocks the migration — saving the cost of
re-embedding your entire corpus with a model that would make retrieval worse.

## Reproducibility

```bash
pip install datasets sentence-transformers numpy
python benchmarks/run_migration_gate_benchmark.py
```

The script loads the dataset from Hugging Face, downloads both models,
and runs the full comparison. Results will vary slightly between machines
(floating point) but the relative ordering should be consistent.