---
sidebar_position: 3
---

# Python API Reference

The Python library interface. Everything the API does, the library does directly (no server needed).

## Top-Level Imports

```python
import ragforge as rf

rf.parse_file(path)           # Parse any supported file
rf.chunk_document(doc, ...)   # Chunk a Document
rf.available(kind)            # List registered plugins
rf.__version__                # Current version string
```

---

## ragforge.parsing

### `parse_file(path) -> Document`

Auto-detect format by extension and parse.

```python
from ragforge.parsing import parse_file

doc = parse_file("notes.md")      # -> Document(doc_type="md")
doc = parse_file("page.html")     # -> Document(doc_type="html")
doc = parse_file("paper.pdf")     # -> Document(doc_type="pdf")
```

Raises `ValueError` if no parser supports the extension. Raises `ImportError` for PDF if pypdf is not installed.

---

## ragforge.chunking

### `chunk_document(document, strategy, **kwargs) -> list[Chunk]`

Chunk a Document using a named strategy.

```python
from ragforge.chunking import chunk_document

# Structure-aware (default)
chunks = chunk_document(doc, strategy="structure", max_tokens=384)

# Fixed sliding window
chunks = chunk_document(doc, strategy="fixed", chunk_tokens=256, overlap_tokens=32)
```

---

## ragforge.pipeline

### `KnowledgeBase` (primary interface)

```python
from ragforge.pipeline import KnowledgeBase

# Build from source files
kb = KnowledgeBase.build(name="my-kb", sources=["./docs/"], chunk_strategy="structure")

# Load existing
kb = KnowledgeBase.load("my-kb")

# Query (retrieval only)
results = kb.query("How do refunds work?", mode="hybrid", top_k=5, rerank=True)
for chunk, score in results:
    print(f"  [{score:.3f}] {chunk.text[:80]}...")

# Answer (retrieval + generation)
result = kb.answer("How do refunds work?", llm="ollama")
print(result["answer"])
print(result["sources"])
```

### `build_knowledge_base(name, sources, ...) -> dict`

Functional interface (used by API/CLI).

```python
from ragforge.pipeline import build_knowledge_base

result = build_knowledge_base(
    name="my-kb",
    sources=["./docs/"],
    embedding_model="default",
    chunk_strategy="structure",
)
```

### `query_knowledge_base(knowledge, question, ...) -> dict`

Functional interface with optional answer generation.

```python
from ragforge.pipeline import query_knowledge_base

result = query_knowledge_base(
    knowledge="my-kb",
    question="How do refunds work?",
    top_k=5,
    mode="hybrid",
    rerank=True,
    generate=True,
    llm="ollama",
)
# result["chunks"], result["answer"], result["llm"]
```

---

## ragforge.evaluation

### `Evaluator` (primary interface)

```python
from ragforge.pipeline import KnowledgeBase
from ragforge.evaluation import Evaluator, GoldenDataset

kb = KnowledgeBase.load("my-kb")
golden = GoldenDataset.load("golden.json")

evaluator = Evaluator(kb)
report = evaluator.run(golden, metrics=["hit_rate", "mrr", "precision_at_k"])
report.print_table()
```

### `Evaluator.compare(kb_a, kb_b, golden) -> dict`

A/B comparison between two knowledge bases.

```python
comparison = Evaluator.compare(kb_a, kb_b, golden)
Evaluator.print_comparison(comparison)
```

### `GoldenDataset`

```python
from ragforge.evaluation import GoldenDataset

golden = GoldenDataset.load("golden.json")  # Load from file
golden.save("output.json")                  # Save to file
print(len(golden))                          # Number of items
```

### `generate_golden_draft(knowledge, num_items, llm) -> GoldenDataset`

Bootstrap a draft golden dataset from an existing KB.

```python
from ragforge.evaluation import generate_golden_draft

golden = generate_golden_draft(knowledge="my-kb", num_items=20, llm="ollama")
golden.save("golden_draft.json")
```

### Available Metrics

```python
from ragforge.evaluation import RETRIEVAL_METRICS, JUDGE_METRICS, ALL_METRICS
# RETRIEVAL_METRICS = ["hit_rate", "precision_at_k", "recall_at_k", "mrr"]
# JUDGE_METRICS = ["faithfulness", "answer_relevance"]
```

---

## ragforge.quantization

### `quantize_and_compare(target, knowledge, options) -> dict`

Quantize and report cost/quality tradeoff.

```python
from ragforge.quantization import quantize_and_compare

result = quantize_and_compare(
    target="default",
    knowledge="my-kb",
    options={"bits": 8},
)
```

---

## ragforge.migration

### `migrate_knowledge_base(knowledge, from_model, to_model, ...) -> dict`

Safely migrate between embedding models.

```python
from ragforge.migration import migrate_knowledge_base

result = migrate_knowledge_base(
    knowledge="my-kb",
    from_model="default",
    to_model="quantized",
    validate=True,
)
```

---

## ragforge.core

### Data Models

```python
from ragforge.core.models import Document, Chunk, estimate_tokens

doc = Document(text="...", source="file.md", doc_type="md")
chunk = Chunk(text="...", doc_id=doc.id, index=0)
tokens = estimate_tokens("some text")  # ~len/4
```

### Registry

```python
from ragforge.core.registry import register, get, available, all_kinds, registered_info

@register("parser", "custom")
class CustomParser: ...

cls = get("parser", "custom")
names = available("parser")
all_kinds()       # ["chunker", "embedding", "parser", "store"]
registered_info() # full dict
```


---

## ragforge.coordination

### `Blackboard` / `InMemoryBlackboard`

Shared key/value workspace for multi-agent coordination.

```python
from ragforge.coordination import InMemoryBlackboard, Blackboard

# In-memory (for testing/ephemeral tasks)
board = InMemoryBlackboard()

# Persistent (SQLite-backed, survives crashes)
board = Blackboard("my-task")

# Write entries with markers
board.write("findings", {"data": "..."}, author="researcher", tags={"confidence": 0.9})

# Read
entry = board.read("findings")           # by key
entries = board.read_by_tag("confidence", lambda v: v > 0.5)  # by tag predicate
history = board.history(key="findings")   # all writes to a key
```

### `Agent` / `Orchestrator`

```python
from ragforge.coordination import Agent, AgentResult, Orchestrator

def my_trigger(board):
    return board.has_key("input") and not board.has_key("output")

def my_action(board, agent_id):
    data = board.read("input")
    board.write("output", f"processed: {data.value}", author=agent_id)
    return AgentResult(agent_id=agent_id, entries_read=["input"], entries_written=["output"])

agent = Agent(id="processor", trigger=my_trigger, action=my_action, max_fires=1)
orch = Orchestrator(board, [agent], goal=lambda b: b.has_key("output"), max_steps=10)
result = orch.run()
# result.termination_reason, result.steps, result.total_tokens
```

### `run_benchmark(task) -> BenchmarkResult`

Compare direct-messaging vs blackboard cost.

```python
from ragforge.coordination import BenchmarkTask, run_benchmark

task = BenchmarkTask(
    description="My task",
    agents=agents,
    goal=goal_fn,
    simulate_direct=direct_fn,
)
result = run_benchmark(task)
print(result.summary())
print(f"Token savings: {result.token_savings_pct:.1f}%")
```

### `traced_run(board, agents, goal, ...) -> OrchestratorResult`

Run with tracing (results appear in the UI dashboard).

```python
from ragforge.coordination import traced_run

result = traced_run(board, agents, goal=goal_fn)
```
