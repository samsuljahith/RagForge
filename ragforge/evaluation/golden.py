"""
Golden dataset schema and utilities.

A golden dataset is the ground truth you evaluate your RAG system against.
Each item is a question with (optionally) the expected answer and/or the IDs
of chunks that SHOULD be retrieved. Without a golden set, you're flying blind.

Schema:
    GoldenItem — one test case (question + expected outputs)
    GoldenDataset — a list of items + load/save (JSON, CSV)

Bootstrap:
    generate_golden_draft() — use an LLM to generate candidate Q&A pairs
    from existing chunks. Clearly marked as DRAFT (human must review).
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GoldenItem:
    """
    One test case in a golden dataset.

    Fields:
        question: The test question to ask the RAG system.
        expected_answer: (Optional) The correct/expected answer text.
        relevant_chunk_ids: (Optional) IDs of chunks that SHOULD appear in results.
        relevant_sources: (Optional) Source file paths that contain the answer.
        notes: (Optional) Human notes about this test case.
    """

    question: str
    expected_answer: str = ""
    relevant_chunk_ids: list[str] = field(default_factory=list)
    relevant_sources: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        d = asdict(self)
        # Remove empty optional fields for cleaner JSON
        return {k: v for k, v in d.items() if v}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldenItem":
        """Construct from a dict (lenient — ignores unknown keys)."""
        fields = {"question", "expected_answer", "relevant_chunk_ids", "relevant_sources", "notes"}
        filtered = {k: v for k, v in data.items() if k in fields}
        # Handle string-to-list for CSV imports
        for list_field in ("relevant_chunk_ids", "relevant_sources"):
            val = filtered.get(list_field)
            if isinstance(val, str) and val:
                filtered[list_field] = [s.strip() for s in val.split(",")]
            elif val is None:
                filtered[list_field] = []
        return cls(**filtered)


class GoldenDataset:
    """
    A collection of GoldenItems — the ground truth for evaluation.

    Supports loading from and saving to JSON and CSV files.
    Can also be constructed programmatically from a list of dicts.

    Usage:
        # From file
        dataset = GoldenDataset.load("golden.json")

        # From dicts
        dataset = GoldenDataset.from_dicts([
            {"question": "Refund window?", "expected_answer": "30 days"},
        ])

        # Iterate
        for item in dataset:
            print(item.question)
    """

    def __init__(self, items: list[GoldenItem] | None = None) -> None:
        self.items: list[GoldenItem] = items or []

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, idx: int) -> GoldenItem:
        return self.items[idx]

    @classmethod
    def from_dicts(cls, data: list[dict[str, Any]]) -> "GoldenDataset":
        """Construct from a list of dicts (e.g. from JSON or API input)."""
        items = [GoldenItem.from_dict(d) for d in data if d.get("question")]
        return cls(items=items)

    def to_dicts(self) -> list[dict[str, Any]]:
        """Serialize all items to plain dicts."""
        return [item.to_dict() for item in self.items]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_json(self, path: str | Path) -> None:
        """Save the golden dataset to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dicts(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "GoldenDataset":
        """Load a golden dataset from a JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Golden dataset not found: {path}")
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON array, got {type(data).__name__}")
        return cls.from_dicts(data)

    def save_csv(self, path: str | Path) -> None:
        """Save the golden dataset to a CSV file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["question", "expected_answer", "relevant_chunk_ids", "relevant_sources", "notes"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in self.items:
                row = {
                    "question": item.question,
                    "expected_answer": item.expected_answer,
                    "relevant_chunk_ids": ",".join(item.relevant_chunk_ids),
                    "relevant_sources": ",".join(item.relevant_sources),
                    "notes": item.notes,
                }
                writer.writerow(row)

    @classmethod
    def load_csv(cls, path: str | Path) -> "GoldenDataset":
        """Load a golden dataset from a CSV file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Golden dataset not found: {path}")
        items = []
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(GoldenItem.from_dict(dict(row)))
        return cls(items=items)

    @classmethod
    def load(cls, path: str | Path) -> "GoldenDataset":
        """Load from JSON or CSV based on file extension."""
        p = Path(path)
        if p.suffix.lower() == ".csv":
            return cls.load_csv(p)
        return cls.load_json(p)

    def save(self, path: str | Path) -> None:
        """Save to JSON or CSV based on file extension."""
        p = Path(path)
        if p.suffix.lower() == ".csv":
            self.save_csv(p)
        else:
            self.save_json(p)


# ---------------------------------------------------------------------------
# Bootstrap: generate a draft golden set from existing chunks
# ---------------------------------------------------------------------------


def generate_golden_draft(
    knowledge: str,
    num_items: int = 10,
    llm: str = "ollama",
    llm_opts: dict[str, Any] | None = None,
) -> GoldenDataset:
    """
    Generate a DRAFT golden dataset from an existing KnowledgeBase.

    Uses an LLM to generate candidate question/answer pairs from chunks.
    The output is clearly a DRAFT — a human MUST review and correct it
    before using it as ground truth for evaluation.

    Args:
        knowledge: Name of the knowledge base to bootstrap from.
        num_items: Approximate number of Q&A pairs to generate.
        llm: LLM provider name ("ollama", "openai", "anthropic").
        llm_opts: Options for the LLM provider.

    Returns:
        A GoldenDataset marked as draft (each item has notes="DRAFT - review before use").
    """
    from ragforge.pipeline import KnowledgeBase
    from ragforge.pipeline.generation import get_llm

    kb = KnowledgeBase.load(knowledge)
    provider = get_llm(llm, **(llm_opts or {}))

    # Sample chunks (spread evenly across the KB)
    all_chunks = kb.store.chunks
    if not all_chunks:
        return GoldenDataset(items=[])

    # Pick evenly-spaced chunks
    step = max(1, len(all_chunks) // num_items)
    sampled = all_chunks[::step][:num_items]

    items: list[GoldenItem] = []
    for chunk in sampled:
        prompt = (
            "Given this text from a knowledge base, generate exactly ONE question that "
            "this text can answer, and the concise answer. Respond in this exact format:\n"
            "Q: <question>\n"
            "A: <answer>\n\n"
            f"TEXT:\n{chunk.text[:500]}"
        )

        try:
            response = provider.generate(prompt, temperature=0.3)
            # Parse Q: and A: from response
            q_line = ""
            a_line = ""
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith("Q:"):
                    q_line = line[2:].strip()
                elif line.startswith("A:"):
                    a_line = line[2:].strip()

            if q_line:
                items.append(GoldenItem(
                    question=q_line,
                    expected_answer=a_line,
                    relevant_chunk_ids=[chunk.id],
                    relevant_sources=[chunk.metadata.get("source", chunk.doc_id)],
                    notes="DRAFT - review before use",
                ))
        except Exception:
            # Skip chunks that fail — bootstrap is best-effort
            continue

    return GoldenDataset(items=items)
