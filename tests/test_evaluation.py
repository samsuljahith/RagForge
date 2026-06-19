"""Tests for the evaluation module."""

import pytest

from ragforge.evaluation.evaluator import compute_precision, compute_recall


class TestPrecision:
    def test_perfect(self):
        assert compute_precision(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_zero(self):
        assert compute_precision(["a", "b"], ["c", "d"]) == 0.0

    def test_partial(self):
        assert compute_precision(["a", "b", "c", "d"], ["a", "b"]) == 0.5

    def test_empty_retrieved(self):
        assert compute_precision([], ["a", "b"]) == 0.0


class TestRecall:
    def test_perfect(self):
        assert compute_recall(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_zero(self):
        assert compute_recall(["x", "y"], ["a", "b"]) == 0.0

    def test_partial(self):
        assert compute_recall(["a", "b"], ["a", "b", "c", "d"]) == 0.5

    def test_empty_relevant(self):
        assert compute_recall(["a"], []) == 1.0

    def test_empty_retrieved(self):
        assert compute_recall([], ["a", "b"]) == 0.0
