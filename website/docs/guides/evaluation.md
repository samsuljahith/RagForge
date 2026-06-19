---
sidebar_position: 4
---

# Evaluating RAG Quality

"No eval meant flying blind... half our improvements were regressions." The evaluation module measures retrieval and answer quality so changes are provable, not vibes.

## Quick Start

```python
from ragforge.evaluation import evaluate_knowledge_base

result = evaluate_knowledge_base(
    knowledge="my-kb",
    golden_dataset=[
        {"question": "What is the refund window?", "expected_answer": "30 days"},
        {"question": "Are digital goods refundable?", "expected_answer": "non-refundable once downloaded"},
    ],
    metrics=["precision", "recall", "faithfulness"],
)

print(f"Precision:    {result['summary']['precision']:.2%}")
print(f"Recall:       {result['summary']['recall']:.2%}")
print(f"Faithfulness: {result['summary']['faithfulness']:.2%}")
```

## Metrics

| Metric | What it measures |
|--------|-----------------|
| **Precision** | What fraction of retrieved chunks are actually relevant? |
| **Recall** | What fraction of relevant information was retrieved? |
| **Faithfulness** | Do the retrieved chunks contain the expected answer? |

## Golden Dataset Format

```json
[
  {
    "question": "What is the refund window for electronics?",
    "expected_answer": "14 days",
    "expected_chunks": ["chunk_id_1", "chunk_id_2"]
  }
]
```

- `question` (required): The test question
- `expected_answer` (optional): The correct answer text
- `expected_chunks` (optional): IDs of chunks that should be retrieved

## A/B Comparison

Compare two configurations on the same data:

```python
from ragforge.evaluation import compare_configs

result = compare_configs(
    knowledge="my-kb",
    golden_dataset=golden,
    config_a={"sources": ["./docs/"], "chunk_strategy": "fixed"},
    config_b={"sources": ["./docs/"], "chunk_strategy": "structure"},
)

print(f"Winner: config_{result['winner']}")
print(f"Delta:  {result['delta']}")
```

## API

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge": "my-kb",
    "golden_dataset": [
      {"question": "Refund window?", "expected_answer": "30 days"}
    ]
  }'
```

## Use Cases

- **Before shipping**: Validate that your chunking strategy retrieves the right answers
- **After changes**: Confirm improvements didn't break other queries (regression testing)
- **Comparing strategies**: Fixed vs structure-aware chunking on your actual data
- **Model comparison**: Does a smaller/cheaper model still retrieve well enough?
