"""
Quantization module: reduce model/embedding size and measure the tradeoff.

The key insight: quantization savings are meaningless without measuring quality impact
on YOUR data. This module quantizes embeddings and uses the evaluation module to
report the real cost/quality tradeoff — before vs after — so you make informed decisions.

Quick start:
    from ragforge.quantization import quantize_and_compare

    result = quantize_and_compare(
        target="default",
        knowledge="my-kb",
        options={"bits": 8},
    )
"""

from ragforge.quantization.quantizer import quantize_and_compare, QuantizedEmbedding

__all__ = ["quantize_and_compare", "QuantizedEmbedding"]
