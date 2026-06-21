---
sidebar_position: 4
---

# Evaluating RAG Quality

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="110" viewBox="0 0 550 110">
  <rect x="10" y="30" width="70" height="45" rx="6" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1.5"/>
  <text x="45" y="48" textAnchor="middle" fontSize="7" fontWeight="600" fill="#fbbf24">Golden Set</text>
  <text x="45" y="60" textAnchor="middle" fontSize="6" fill="#6a6a80">Q&amp;A pairs</text>
  <text x="45" y="70" textAnchor="middle" fontSize="6" fill="#6a6a80">ground truth</text>
  <rect x="110" y="15" width="60" height="30" rx="6" fill="#1a1a24" stroke="#3b82f6" strokeWidth="1.5"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="140" y="34" textAnchor="middle" fontSize="7" fontWeight="600" fill="#3b82f6">Config A</text>
  <rect x="110" y="55" width="60" height="30" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
  <text x="140" y="74" textAnchor="middle" fontSize="7" fontWeight="600" fill="#ff6b2c">Config B</text>
  <rect x="205" y="25" width="75" height="50" rx="8" fill="#1a1a24" stroke="#22d3ee" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.8s" repeatCount="indefinite"/></rect>
  <text x="242" y="47" textAnchor="middle" fontSize="8" fontWeight="700" fill="#22d3ee">Evaluate</text>
  <text x="242" y="60" textAnchor="middle" fontSize="6" fill="#6a6a80">per question</text>
  <text x="242" y="70" textAnchor="middle" fontSize="6" fill="#6a6a80">+ judge LLM</text>
  <text x="315" y="25" fontSize="6" fill="#a0a0b8">hit_rate</text>
  <rect x="350" y="19" width="80" height="7" rx="3" fill="#1a1a24" stroke="#2a2a34" strokeWidth="0.5"/><rect x="350" y="19" width="0" height="7" rx="3" fill="#34d399"><animate attributeName="width" from="0" to="68" dur="2s" repeatCount="indefinite"/></rect><text x="435" y="25" fontSize="6" fontWeight="700" fill="#34d399">85%</text>
  <text x="315" y="40" fontSize="6" fill="#a0a0b8">MRR</text>
  <rect x="350" y="34" width="80" height="7" rx="3" fill="#1a1a24" stroke="#2a2a34" strokeWidth="0.5"/><rect x="350" y="34" width="0" height="7" rx="3" fill="#7c6ff8"><animate attributeName="width" from="0" to="58" dur="2s" repeatCount="indefinite"/></rect><text x="435" y="40" fontSize="6" fontWeight="700" fill="#7c6ff8">73%</text>
  <text x="315" y="55" fontSize="6" fill="#a0a0b8">precision@5</text>
  <rect x="350" y="49" width="80" height="7" rx="3" fill="#1a1a24" stroke="#2a2a34" strokeWidth="0.5"/><rect x="350" y="49" width="0" height="7" rx="3" fill="#ff6b2c"><animate attributeName="width" from="0" to="50" dur="2s" repeatCount="indefinite"/></rect><text x="435" y="55" fontSize="6" fontWeight="700" fill="#ff6b2c">62%</text>
  <text x="315" y="70" fontSize="6" fill="#a0a0b8">faithfulness</text>
  <rect x="350" y="64" width="80" height="7" rx="3" fill="#1a1a24" stroke="#2a2a34" strokeWidth="0.5"/><rect x="350" y="64" width="0" height="7" rx="3" fill="#a78bfa"><animate attributeName="width" from="0" to="74" dur="2s" repeatCount="indefinite"/></rect><text x="435" y="70" fontSize="6" fontWeight="700" fill="#a78bfa">92%</text>
  <text x="390" y="88" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">✓ Config A wins</text>
  <circle r="3" fill="#fbbf24"><animateMotion dur="1.5s" repeatCount="indefinite" path="M82,52 L108,30"/></circle>
  <circle r="3" fill="#3b82f6"><animateMotion dur="1.5s" repeatCount="indefinite" path="M172,30 L203,42"/></circle>
  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.8s" repeatCount="indefinite" path="M172,70 L203,55"/></circle>
  <circle r="3" fill="#22d3ee"><animateMotion dur="1.5s" repeatCount="indefinite" path="M282,50 L313,35"/></circle>
  <text x="275" y="105" textAnchor="middle" fontSize="7" fill="#6a6a80">Golden dataset → evaluate both configs → concrete metric bars → winner declared</text>
</svg>
</div>

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
