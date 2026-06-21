---
sidebar_position: 4
---

# Evaluating RAG Quality

"No eval meant flying blind — half our improvements were regressions." The evaluation module gives you concrete numbers: did we find the right chunks? Is the generated answer faithful to the sources?

## Quick Start

```python
from ragforge.pipeline import KnowledgeBase
from ragforge.evaluation import Evaluator, GoldenDataset

kb = KnowledgeBase.load("my-kb")
golden = GoldenDataset.load("golden.json")

evaluator = Evaluator(kb)
report = evaluator.run(golden)
report.print_table()
```

Output:
```
╔═══════════════════╤═════════╗
║ Metric            │ Score   ║
╠═══════════════════╪═════════╣
║ hit_rate          │  0.850  ║
║ precision_at_k    │  0.620  ║
║ recall_at_k       │  0.780  ║
║ mrr               │  0.730  ║
╚═══════════════════╧═════════╝
```

## Metrics

### Retrieval Metrics (no LLM needed)

| Metric | What it measures |
|--------|-----------------|
| `hit_rate` | Was at least one relevant chunk in the top-k? (binary per query) |
| `precision_at_k` | What fraction of top-k chunks are relevant? |
| `recall_at_k` | What fraction of all relevant chunks were retrieved? |
| `mrr` | Mean Reciprocal Rank — how high is the first relevant chunk? |

### LLM-as-Judge Metrics (requires an LLM)

| Metric | What it measures |
|--------|-----------------|
| `faithfulness` | Is the generated answer supported by the retrieved chunks? (no hallucination) |
| `answer_relevance` | Does the answer actually address the question? |

```python
# Include judge metrics (requires LLM)
report = evaluator.run(golden, metrics=["hit_rate", "mrr", "faithfulness"],
                       generate=True, llm="ollama")
```

## Golden Dataset

A golden dataset is your ground truth — questions paired with their correct answers and/or relevant chunk IDs.

### Format (JSON)

```json
[
  {
    "question": "What is the refund window for electronics?",
    "expected_chunks": ["chunk_id_1", "chunk_id_2"],
    "expected_answer": "14 days"
  },
  {
    "question": "Are digital goods refundable?",
    "expected_chunks": ["chunk_id_5"],
    "expected_answer": "Non-refundable once downloaded"
  }
]
```

- `question` (required): The test question
- `expected_chunks` (optional): IDs of chunks that should be retrieved
- `expected_answer` (optional): The correct answer text (for judge metrics)

### Bootstrap a Golden Dataset

Generate a draft from an existing KB (review before using as ground truth):

```bash
ragforge eval bootstrap my-kb --out golden_draft.json -n 20 --llm ollama
```

```python
from ragforge.evaluation import generate_golden_draft

golden = generate_golden_draft(knowledge="my-kb", num_items=20, llm="ollama")
golden.save("golden_draft.json")
```

## A/B Comparison

Compare two knowledge bases (different chunking strategies, embedding models, etc.) on the same golden dataset:

```python
from ragforge.evaluation import Evaluator

comparison = Evaluator.compare(kb_a, kb_b, golden)
Evaluator.print_comparison(comparison)
```

Output shows each metric side-by-side with the delta:
```
Config A (structure) vs Config B (fixed):
  hit_rate:       0.85 vs 0.72  (+0.13)
  precision_at_k: 0.62 vs 0.48  (+0.14)
  mrr:            0.73 vs 0.61  (+0.12)
Winner: Config A
```

## CLI

```bash
# Run evaluation against a golden dataset
ragforge eval run my-kb golden.json

# With specific metrics
ragforge eval run my-kb golden.json --metrics hit_rate,mrr,precision_at_k

# With LLM judge metrics
ragforge eval run my-kb golden.json --generate --llm ollama --metrics hit_rate,faithfulness

# A/B compare two KBs
ragforge eval compare kb-structure kb-fixed golden.json

# Bootstrap a golden dataset
ragforge eval bootstrap my-kb --out golden.json -n 20 --llm ollama

# JSON output
ragforge eval run my-kb golden.json --json
```

## API

```bash
# Run evaluation
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge": "my-kb",
    "golden_path": "golden.json",
    "metrics": ["hit_rate", "mrr", "precision_at_k"],
    "top_k": 5
  }'
```

Example response:
```json
{
  "metrics": {
    "hit_rate": 0.85,
    "precision_at_k": 0.62,
    "recall_at_k": 0.78,
    "mrr": 0.73
  },
  "num_items": 20,
  "details": [...]
}
```

## When to Evaluate

- **Before shipping**: Validate your chunking strategy finds the right answers
- **After changes**: Confirm improvements didn't break other queries (regression)
- **Comparing configs**: Fixed vs structure-aware vs docling on your actual data
- **Model comparison**: Does a smaller/cheaper embedding still retrieve well enough?
- **After quantization**: Did compression hurt retrieval quality?
