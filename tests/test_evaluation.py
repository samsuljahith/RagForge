"""
Tests for the evaluation module.

Covers:
  - Golden dataset schema (create, serialize, load/save JSON+CSV)
  - Retrieval metrics (known inputs → known scores, pure math)
  - LLM-judge metrics (mocked provider, no real keys)
  - Evaluator end-to-end on a tiny golden set
  - A/B compare delta logic
  - API endpoint /evaluate
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ragforge.evaluation.golden import GoldenItem, GoldenDataset
from ragforge.evaluation.metrics import (
    hit_rate,
    precision_at_k,
    recall_at_k,
    mrr,
    judge_faithfulness,
    judge_answer_relevance,
    _parse_score,
    RETRIEVAL_METRICS,
    JUDGE_METRICS,
    ALL_METRICS,
)
from ragforge.evaluation.evaluator import Evaluator, EvalReport, ItemResult, evaluate_knowledge_base


# ===========================================================================
# Golden Dataset
# ===========================================================================


class TestGoldenItem:
    def test_create_minimal(self):
        item = GoldenItem(question="What is X?")
        assert item.question == "What is X?"
        assert item.expected_answer == ""
        assert item.relevant_chunk_ids == []

    def test_create_full(self):
        item = GoldenItem(
            question="Q?",
            expected_answer="A.",
            relevant_chunk_ids=["c1", "c2"],
            relevant_sources=["doc.md"],
            notes="test note",
        )
        assert item.relevant_chunk_ids == ["c1", "c2"]
        assert item.notes == "test note"

    def test_to_dict_omits_empty(self):
        item = GoldenItem(question="Q?", expected_answer="A.")
        d = item.to_dict()
        assert "question" in d
        assert "expected_answer" in d
        assert "relevant_chunk_ids" not in d  # empty list omitted
        assert "notes" not in d  # empty string omitted

    def test_from_dict(self):
        d = {"question": "Q?", "expected_answer": "A.", "extra_field": "ignored"}
        item = GoldenItem.from_dict(d)
        assert item.question == "Q?"
        assert item.expected_answer == "A."

    def test_from_dict_csv_string_lists(self):
        d = {"question": "Q?", "relevant_chunk_ids": "c1, c2, c3"}
        item = GoldenItem.from_dict(d)
        assert item.relevant_chunk_ids == ["c1", "c2", "c3"]


class TestGoldenDataset:
    def test_from_dicts(self):
        data = [
            {"question": "Q1?", "expected_answer": "A1"},
            {"question": "Q2?"},
            {"question": ""},  # should be skipped (empty question)
        ]
        ds = GoldenDataset.from_dicts(data)
        assert len(ds) == 2

    def test_iteration(self):
        ds = GoldenDataset.from_dicts([{"question": "Q1?"}, {"question": "Q2?"}])
        questions = [item.question for item in ds]
        assert questions == ["Q1?", "Q2?"]

    def test_save_load_json(self, tmp_path):
        ds = GoldenDataset.from_dicts([
            {"question": "Q1?", "expected_answer": "A1"},
            {"question": "Q2?", "relevant_chunk_ids": ["c1"]},
        ])
        path = tmp_path / "golden.json"
        ds.save_json(path)
        assert path.exists()

        loaded = GoldenDataset.load_json(path)
        assert len(loaded) == 2
        assert loaded[0].question == "Q1?"
        assert loaded[1].relevant_chunk_ids == ["c1"]

    def test_save_load_csv(self, tmp_path):
        ds = GoldenDataset.from_dicts([
            {"question": "Q1?", "expected_answer": "A1", "relevant_chunk_ids": ["c1", "c2"]},
        ])
        path = tmp_path / "golden.csv"
        ds.save_csv(path)
        assert path.exists()

        loaded = GoldenDataset.load_csv(path)
        assert len(loaded) == 1
        assert loaded[0].question == "Q1?"
        assert loaded[0].relevant_chunk_ids == ["c1", "c2"]

    def test_load_auto_detect(self, tmp_path):
        ds = GoldenDataset.from_dicts([{"question": "Q?"}])
        ds.save(tmp_path / "test.json")
        ds.save(tmp_path / "test.csv")

        from_json = GoldenDataset.load(tmp_path / "test.json")
        from_csv = GoldenDataset.load(tmp_path / "test.csv")
        assert len(from_json) == 1
        assert len(from_csv) == 1

    def test_load_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            GoldenDataset.load(tmp_path / "nonexistent.json")


# ===========================================================================
# Retrieval Metrics — pure math, known inputs → known outputs
# ===========================================================================


class TestHitRate:
    def test_hit(self):
        assert hit_rate(["a", "b", "c"], ["b"]) == 1.0

    def test_miss(self):
        assert hit_rate(["a", "b", "c"], ["x", "y"]) == 0.0

    def test_empty_retrieved(self):
        assert hit_rate([], ["a"]) == 0.0

    def test_empty_relevant(self):
        assert hit_rate(["a", "b"], []) == 1.0

    def test_first_position(self):
        assert hit_rate(["target", "other"], ["target"]) == 1.0


class TestPrecisionAtK:
    def test_perfect(self):
        assert precision_at_k(["a", "b"], ["a", "b"]) == 1.0

    def test_half(self):
        assert precision_at_k(["a", "b", "c", "d"], ["a", "c"]) == 0.5

    def test_zero(self):
        assert precision_at_k(["x", "y"], ["a", "b"]) == 0.0

    def test_empty_retrieved(self):
        assert precision_at_k([], ["a"]) == 0.0

    def test_one_of_three(self):
        assert abs(precision_at_k(["a", "b", "c"], ["a"]) - 1/3) < 1e-9


class TestRecallAtK:
    def test_perfect(self):
        assert recall_at_k(["a", "b", "c"], ["a", "b"]) == 1.0

    def test_half(self):
        assert recall_at_k(["a", "b"], ["a", "b", "c", "d"]) == 0.5

    def test_zero(self):
        assert recall_at_k(["x", "y"], ["a", "b"]) == 0.0

    def test_empty_relevant(self):
        assert recall_at_k(["a"], []) == 1.0

    def test_empty_retrieved(self):
        assert recall_at_k([], ["a", "b"]) == 0.0


class TestMRR:
    def test_first_position(self):
        assert mrr(["target", "other", "another"], ["target"]) == 1.0

    def test_second_position(self):
        assert mrr(["other", "target", "another"], ["target"]) == 0.5

    def test_third_position(self):
        assert abs(mrr(["a", "b", "target"], ["target"]) - 1/3) < 1e-9

    def test_not_found(self):
        assert mrr(["a", "b", "c"], ["x"]) == 0.0

    def test_empty_relevant(self):
        assert mrr(["a", "b"], []) == 1.0

    def test_multiple_relevant_first_matters(self):
        # MRR cares about the FIRST relevant result
        assert mrr(["a", "rel1", "rel2"], ["rel1", "rel2"]) == 0.5


# ===========================================================================
# LLM-Judge Metrics — mocked
# ===========================================================================


class MockJudge:
    """Mock LLM that returns predictable scores."""

    def __init__(self, score: str = "0.8"):
        self._score = score

    @property
    def name(self):
        return "mock-judge"

    def generate(self, prompt: str, **opts) -> str:
        return self._score


class TestJudgeFaithfulness:
    def test_returns_parsed_score(self):
        judge = MockJudge("0.9")
        score = judge_faithfulness("The answer.", ["Context chunk."], judge)
        assert score == 0.9

    def test_empty_answer(self):
        judge = MockJudge("0.9")
        score = judge_faithfulness("", ["Context."], judge)
        assert score == 0.0

    def test_empty_context(self):
        judge = MockJudge("0.9")
        score = judge_faithfulness("Answer.", [], judge)
        assert score == 0.0


class TestJudgeAnswerRelevance:
    def test_returns_parsed_score(self):
        judge = MockJudge("0.75")
        score = judge_answer_relevance("What is X?", "X is Y.", judge)
        assert score == 0.75

    def test_empty_answer(self):
        judge = MockJudge("0.9")
        score = judge_answer_relevance("Q?", "", judge)
        assert score == 0.0

    def test_empty_question(self):
        judge = MockJudge("0.9")
        score = judge_answer_relevance("", "A.", judge)
        assert score == 0.0


class TestParseScore:
    def test_simple_float(self):
        assert _parse_score("0.8") == 0.8

    def test_with_text(self):
        assert _parse_score("The score is 0.7 based on analysis") == 0.7

    def test_out_of_range_defaults(self):
        assert _parse_score("5.0") == 0.5  # out of [0,1], fallback

    def test_no_number_defaults(self):
        assert _parse_score("I cannot determine") == 0.5


# ===========================================================================
# Evaluator — end-to-end with a real (tiny) KB
# ===========================================================================


class TestEvaluator:
    def _build_kb(self, tmp_path):
        from ragforge.pipeline import KnowledgeBase

        (tmp_path / "doc.md").write_text(
            "# Refunds\n\nRefunds are processed within 30 days.\n\n"
            "# Shipping\n\nShipping takes 5-7 business days.\n\n"
            "# Returns\n\nReturns accepted within 14 days."
        )
        return KnowledgeBase.build(
            name="eval-test-kb",
            sources=[str(tmp_path)],
            persist=False,
        )

    def test_run_retrieval_metrics(self, tmp_path):
        kb = self._build_kb(tmp_path)
        # Use chunk IDs from the actual KB
        chunk_ids = [c.id for c in kb.store.chunks]

        golden = GoldenDataset.from_dicts([
            {"question": "Refund window?", "relevant_chunk_ids": [chunk_ids[0]]},
            {"question": "Shipping time?", "relevant_chunk_ids": [chunk_ids[1]]},
        ])

        evaluator = Evaluator(kb)
        report = evaluator.run(golden, metrics=["hit_rate", "mrr", "precision_at_k"])

        assert report.knowledge == "eval-test-kb"
        assert report.num_items == 2
        assert "hit_rate" in report.summary
        assert "mrr" in report.summary
        assert "precision_at_k" in report.summary
        # All scores should be floats between 0 and 1
        for score in report.summary.values():
            assert 0.0 <= score <= 1.0

    def test_run_returns_per_item_results(self, tmp_path):
        kb = self._build_kb(tmp_path)
        golden = GoldenDataset.from_dicts([{"question": "Refund?"}])

        evaluator = Evaluator(kb)
        report = evaluator.run(golden, metrics=["hit_rate"])

        assert len(report.items) == 1
        assert report.items[0].question == "Refund?"
        assert len(report.items[0].retrieved_ids) > 0

    def test_report_to_dict(self, tmp_path):
        kb = self._build_kb(tmp_path)
        golden = GoldenDataset.from_dicts([{"question": "Q?"}])

        evaluator = Evaluator(kb)
        report = evaluator.run(golden, metrics=["hit_rate"])

        d = report.to_dict()
        assert "knowledge" in d
        assert "summary" in d
        assert "items" in d
        assert "config" in d

    def test_report_print_table(self, tmp_path, capsys):
        kb = self._build_kb(tmp_path)
        golden = GoldenDataset.from_dicts([{"question": "Q?"}])

        evaluator = Evaluator(kb)
        report = evaluator.run(golden, metrics=["hit_rate", "mrr"])
        output = report.print_table()

        assert "hit_rate" in output
        assert "mrr" in output


class TestEvaluatorCompare:
    def _build_two_kbs(self, tmp_path):
        from ragforge.pipeline import KnowledgeBase

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("# Info\n\nThe answer is 42.\n\n# Other\n\nIrrelevant.")

        kb_a = KnowledgeBase.build(
            name="compare-a",
            sources=[str(docs)],
            chunk_strategy="fixed",
            persist=False,
        )
        kb_b = KnowledgeBase.build(
            name="compare-b",
            sources=[str(docs)],
            chunk_strategy="structure",
            persist=False,
        )
        return kb_a, kb_b

    def test_compare_returns_deltas(self, tmp_path):
        kb_a, kb_b = self._build_two_kbs(tmp_path)

        golden = GoldenDataset.from_dicts([
            {"question": "What is the answer?"},
        ])

        comparison = Evaluator.compare(
            kb_a, kb_b, golden,
            metrics=["hit_rate", "mrr"],
            label_a="fixed",
            label_b="structure",
        )

        assert "delta" in comparison
        assert "winner" in comparison
        assert "report_a" in comparison
        assert "report_b" in comparison
        assert comparison["label_a"] == "fixed"
        assert comparison["label_b"] == "structure"
        # Deltas are floats
        for metric, delta in comparison["delta"].items():
            assert isinstance(delta, float)

    def test_compare_print(self, tmp_path, capsys):
        kb_a, kb_b = self._build_two_kbs(tmp_path)
        golden = GoldenDataset.from_dicts([{"question": "answer?"}])

        comparison = Evaluator.compare(
            kb_a, kb_b, golden, metrics=["hit_rate"],
            label_a="fixed", label_b="structure",
        )
        output = Evaluator.print_comparison(comparison)

        assert "fixed" in output
        assert "structure" in output
        assert "Winner" in output


# ===========================================================================
# Functional interface
# ===========================================================================


class TestEvaluateKnowledgeBase:
    def test_basic(self, tmp_path):
        from ragforge.pipeline import build_knowledge_base

        (tmp_path / "doc.md").write_text("# Test\n\nThe answer is here.")
        build_knowledge_base(name="eval-func-test", sources=[str(tmp_path)])

        result = evaluate_knowledge_base(
            knowledge="eval-func-test",
            golden_dataset=[{"question": "What is the answer?"}],
            metrics=["hit_rate", "mrr"],
        )

        assert result["knowledge"] == "eval-func-test"
        assert "summary" in result
        assert result["num_questions"] == 1

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "eval-func-test"
        if kb_path.exists():
            shutil.rmtree(kb_path)


# ===========================================================================
# API endpoint
# ===========================================================================


class TestAPIEvaluate:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from ragforge.api import app
        return TestClient(app)

    def test_evaluate_missing_kb(self, client):
        resp = client.post("/evaluate", json={
            "knowledge": "nonexistent-eval-kb",
            "golden_dataset": [{"question": "test?"}],
        })
        assert resp.status_code == 404

    def test_evaluate_success(self, client, tmp_path):
        (tmp_path / "doc.md").write_text("# Test\n\nContent for eval.")
        client.post("/knowledge", json={
            "name": "api-eval-kb",
            "sources": [str(tmp_path)],
        })

        resp = client.post("/evaluate", json={
            "knowledge": "api-eval-kb",
            "golden_dataset": [
                {"question": "What is the content?"},
            ],
            "metrics": ["hit_rate", "mrr"],
            "top_k": 3,
            "mode": "hybrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["knowledge"] == "api-eval-kb"
        assert "summary" in data
        assert data["num_questions"] == 1
        assert "hit_rate" in data["summary"]

        # Cleanup
        kb_path = Path.home() / ".ragforge" / "knowledge_bases" / "api-eval-kb"
        if kb_path.exists():
            shutil.rmtree(kb_path)
