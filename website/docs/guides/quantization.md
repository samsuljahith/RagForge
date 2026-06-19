---
sidebar_position: 5
---

# Quantization & Cost/Quality Comparison

Quantization reduces embedding model size and cost. The key insight: savings are meaningless without measuring quality impact on YOUR data. This module quantizes and compares before vs after.

## Quick Start

```python
from ragforge.quantization import quantize_and_compare

result = quantize_and_compare(
    target="default",
    knowledge="my-kb",
    options={"bits": 8},
)

report = result["report"]
print(f"Compression: {report['after']['compression_ratio']}x")
print(f"Cost reduction: {report['cost_reduction']:.0%}")
print(f"Quality delta: {report['quality_delta']}")
```

## How It Works

1. Take your current embedding model (full float32 precision)
2. Create a quantized version (e.g., int8 = 4x smaller)
3. Embed the same content both ways
4. Compare retrieval quality on your data
5. Report the tradeoff: how much quality do you lose for how much cost savings?

## API

```bash
curl -X POST http://localhost:8000/quantize \
  -H "Content-Type: application/json" \
  -d '{
    "target": "default",
    "knowledge": "my-kb",
    "options": {"bits": 8}
  }'
```

### Response

```json
{
  "target": "default",
  "status": "quantized",
  "report": {
    "before": {"model": "default", "bits": 32, "dimension": 128},
    "after": {"model": "default_quantized_8bit", "bits": 8, "compression_ratio": 4.0},
    "quality_delta": -0.02,
    "cost_reduction": 0.75
  }
}
```

## Quantization Levels

| Bits | Compression | Typical Quality Impact |
|------|-------------|----------------------|
| 16 (float16) | 2x | Negligible |
| 8 (int8) | 4x | Minimal (less than 2%) |
| 4 (int4) | 8x | Noticeable (5-10%) |
| 1 (binary) | 32x | Significant (varies) |

## When to Use

- **Scaling up**: Need to serve more vectors at lower cost
- **Edge deployment**: Running on limited hardware
- **Cost optimization**: Embeddings API bills getting large
- **Always**: Run this BEFORE committing to a smaller model to see the real impact on your data
