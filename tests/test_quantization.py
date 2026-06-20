"""Tests for the quantization module."""

import math
import pytest

from ragforge.quantization.quantizer import QuantizedEmbedding, quantize_and_compare
from ragforge.pipeline.embeddings import DefaultEmbedder


class TestQuantizedEmbedding:
    def test_dimension_preserved(self):
        base = DefaultEmbedder(dim=64)
        quant = QuantizedEmbedding(base_model=base, bits=8)
        assert quant.dimension == 64

    def test_embed_returns_correct_size(self):
        quant = QuantizedEmbedding(bits=8)
        vec = quant.embed("hello world")
        assert len(vec) == quant.dimension

    def test_encode_batch(self):
        quant = QuantizedEmbedding(bits=8)
        vecs = quant.encode(["hello", "world"])
        assert len(vecs) == 2
        assert len(vecs[0]) == quant.dimension

    def test_embed_is_normalized(self):
        quant = QuantizedEmbedding(bits=8)
        vec = quant.embed("some text content here")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-5

    def test_name(self):
        quant = QuantizedEmbedding(bits=8)
        assert "quantized" in quant.name
        assert "8bit" in quant.name

    def test_compression_ratio(self):
        quant = QuantizedEmbedding(bits=8)
        assert quant.compression_ratio == 4.0  # 32/8

        quant4 = QuantizedEmbedding(bits=4)
        assert quant4.compression_ratio == 8.0  # 32/4

    def test_quantized_similar_to_original(self):
        base = DefaultEmbedder()
        quant = QuantizedEmbedding(base_model=base, bits=8)

        text = "the quick brown fox"
        v_base = base.encode_single(text)
        v_quant = quant.embed(text)

        # Should be similar (high cosine similarity)
        dot = sum(a * b for a, b in zip(v_base, v_quant))
        assert dot > 0.9  # Very similar


class TestQuantizeAndCompare:
    def test_basic(self):
        result = quantize_and_compare(target="default", options={"bits": 8})
        assert result["status"] == "quantized"
        assert result["target"] == "default"
        assert "report" in result
        report = result["report"]
        assert "before" in report
        assert "after" in report
        assert report["before"]["bits"] == 32
        assert report["after"]["bits"] == 8
        assert report["cost_reduction"] == 0.75  # 1 - 8/32
