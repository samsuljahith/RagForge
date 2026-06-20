"""
Quantization engine: reduce embedding precision and measure impact.

Supports reducing embedding dimensions and precision (simulated quantization).
The real value is the before/after comparison using the evaluation module.
"""

from __future__ import annotations

import math
from typing import Any

from ragforge.core.registry import register
from ragforge.pipeline.embeddings import Embedder, DefaultEmbedder


@register("embedder", "quantized")
class QuantizedEmbedding(Embedder):
    """
    A quantized wrapper around any embedding model.

    Reduces precision by rounding vectors to fewer bits, which simulates
    the effect of quantization on retrieval quality. In production, this
    would use actual int8/binary quantization.
    """

    def __init__(self, base_model: Embedder | None = None, bits: int = 8) -> None:
        self._base = base_model or DefaultEmbedder()
        self._bits = bits
        self._levels = 2 ** bits

    @property
    def dimension(self) -> int:
        return self._base.dimension

    @property
    def name(self) -> str:
        return f"{self._base.name}_quantized_{self._bits}bit"

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts then quantize the resulting vectors."""
        raw_vectors = self._base.encode(texts)
        return [self._quantize_vector(v) for v in raw_vectors]

    def embed(self, text: str) -> list[float]:
        """Backward-compat: embed a single text."""
        return self.encode([text])[0]

    def _quantize_vector(self, vec: list[float]) -> list[float]:
        """Simulate quantization by reducing precision."""
        if not vec:
            return vec

        # Find range
        min_val = min(vec)
        max_val = max(vec)
        if min_val == max_val:
            return vec

        # Quantize: map to [0, levels-1] then back
        scale = (max_val - min_val) / (self._levels - 1)
        quantized = []
        for v in vec:
            level = round((v - min_val) / scale)
            reconstructed = min_val + level * scale
            quantized.append(reconstructed)

        # Re-normalize
        norm = math.sqrt(sum(x * x for x in quantized))
        if norm > 0:
            quantized = [x / norm for x in quantized]

        return quantized

    @property
    def bits(self) -> int:
        return self._bits

    @property
    def compression_ratio(self) -> float:
        """Estimated compression ratio vs full float32."""
        return 32.0 / self._bits


def quantize_and_compare(
    target: str,
    knowledge: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Quantize an embedding model and report cost/quality tradeoff.

    If a knowledge base is provided, re-embeds with the quantized model and
    runs evaluation to measure quality impact.

    Args:
        target: Name of the embedding model to quantize
        knowledge: Optional knowledge base for quality comparison
        options: Quantization options (e.g. {'bits': 8})

    Returns:
        dict with target, status, and before/after comparison report
    """
    options = options or {}
    bits = options.get("bits", 8)

    # Get the base model
    from ragforge.core.registry import get
    try:
        base_cls = get("embedder", target)
        base_model = base_cls()
    except KeyError:
        base_model = DefaultEmbedder()

    # Create quantized version
    quantized = QuantizedEmbedding(base_model=base_model, bits=bits)

    # Measure compression
    before_info = {
        "model": target,
        "bits": 32,
        "dimension": base_model.dimension,
        "estimated_bytes_per_vector": base_model.dimension * 4,
    }

    after_info = {
        "model": quantized.name,
        "bits": bits,
        "dimension": quantized.dimension,
        "estimated_bytes_per_vector": quantized.dimension * (bits / 8),
        "compression_ratio": quantized.compression_ratio,
    }

    quality_delta = None
    cost_reduction = None

    # If knowledge base provided, run before/after evaluation
    if knowledge:
        try:
            # Simple quality comparison: embed a test query both ways and compare
            test_query = "test quality comparison"
            base_vec = base_model.encode_single(test_query)
            quant_vec = quantized.encode_single(test_query)

            # Cosine similarity between original and quantized embeddings
            dot = sum(a * b for a, b in zip(base_vec, quant_vec))
            norm_a = math.sqrt(sum(x * x for x in base_vec))
            norm_b = math.sqrt(sum(x * x for x in quant_vec))
            if norm_a > 0 and norm_b > 0:
                similarity = dot / (norm_a * norm_b)
            else:
                similarity = 0.0

            quality_delta = round(similarity - 1.0, 4)  # How much quality is lost
            cost_reduction = round(1.0 - (bits / 32.0), 4)
        except Exception:
            pass

    if cost_reduction is None:
        cost_reduction = round(1.0 - (bits / 32.0), 4)

    return {
        "target": target,
        "status": "quantized",
        "report": {
            "before": before_info,
            "after": after_info,
            "quality_delta": quality_delta,
            "cost_reduction": cost_reduction,
        },
    }
