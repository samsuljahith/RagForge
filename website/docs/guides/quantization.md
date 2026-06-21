---
sidebar_position: 5
---

# Quantization & Cost/Quality Comparison

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="100" viewBox="0 0 550 100">
  <rect x="10" y="25" width="80" height="50" rx="6" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1.5"/>
  <text x="50" y="43" textAnchor="middle" fontSize="7" fontWeight="600" fill="#fbbf24">float32</text>
  <text x="50" y="55" textAnchor="middle" fontSize="6" fill="#6a6a80">512 bytes/vec</text>
  <text x="50" y="67" textAnchor="middle" fontSize="6" fill="#fbbf24">quality: 1.00</text>
  <rect x="130" y="30" width="70" height="40" rx="8" fill="#1a1a24" stroke="#a78bfa" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite"/></rect>
  <text x="165" y="48" textAnchor="middle" fontSize="8" fontWeight="700" fill="#a78bfa">Quantize</text>
  <text x="165" y="60" textAnchor="middle" fontSize="6" fill="#6a6a80">compress</text>
  <rect x="240" y="25" width="80" height="50" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"/>
  <text x="280" y="43" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">int8</text>
  <text x="280" y="55" textAnchor="middle" fontSize="6" fill="#6a6a80">128 bytes/vec</text>
  <text x="280" y="67" textAnchor="middle" fontSize="6" fill="#34d399">quality: 0.98</text>
  <rect x="360" y="20" width="110" height="60" rx="8" fill="#1a1a24" stroke="#34d399" strokeWidth="2"/>
  <text x="415" y="38" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Tradeoff Report</text>
  <text x="415" y="52" textAnchor="middle" fontSize="6" fill="#34d399">4x smaller</text>
  <text x="415" y="64" textAnchor="middle" fontSize="6" fill="#34d399">-2% quality</text>
  <text x="415" y="76" textAnchor="middle" fontSize="6" fontWeight="600" fill="#fbbf24">on YOUR data</text>
  <circle r="3" fill="#fbbf24"><animateMotion dur="1.5s" repeatCount="indefinite" path="M92,50 L128,50"/></circle>
  <circle r="3" fill="#a78bfa"><animateMotion dur="1.5s" repeatCount="indefinite" path="M202,50 L238,50"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.3s" repeatCount="indefinite" path="M322,50 L358,50"/></circle>
  <text x="275" y="95" textAnchor="middle" fontSize="7" fill="#6a6a80">Compress embeddings → measure real quality impact → decide with data, not guesses</text>
</svg>
</div>

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
