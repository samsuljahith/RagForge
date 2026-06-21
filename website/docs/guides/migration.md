---
sidebar_position: 6
---

# Embedding Model Migration

Safely move a knowledge base from embedding model A to model B. The hardest module — it re-embeds all chunks, validates quality with evaluation, and performs a safe cutover.

## Quick Start

```python
from ragforge.migration import migrate_knowledge_base

result = migrate_knowledge_base(
    knowledge="my-kb",
    from_model="default",
    to_model="quantized",
    validate=True,
)

print(f"Status: {result['status']}")
print(f"Chunks migrated: {result['num_chunks_migrated']}")
print(f"Quality before: {result['quality_before']}")
print(f"Quality after:  {result['quality_after']}")
```

## How It Works

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="130" viewBox="0 0 600 130">
  <rect x="10" y="40" width="70" height="40" rx="6" fill="#1a1a24" stroke="#fbbf24" strokeWidth="1.5"/>
  <text x="45" y="58" textAnchor="middle" fontSize="7" fontWeight="600" fill="#fbbf24">Load KB</text>
  <text x="45" y="70" textAnchor="middle" fontSize="6" fill="#6a6a80">existing</text>

  <rect x="110" y="40" width="80" height="40" rx="6" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1.5"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="150" y="56" textAnchor="middle" fontSize="7" fontWeight="600" fill="#7c6ff8">Shadow</text>
  <text x="150" y="68" textAnchor="middle" fontSize="6" fill="#a78bfa">re-embed all</text>

  <rect x="220" y="40" width="75" height="40" rx="6" fill="#1a1a24" stroke="#22d3ee" strokeWidth="1.5"/>
  <text x="257" y="56" textAnchor="middle" fontSize="7" fontWeight="600" fill="#22d3ee">Validate</text>
  <text x="257" y="68" textAnchor="middle" fontSize="6" fill="#6a6a80">quality OK?</text>

  <rect x="325" y="15" width="60" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="2"><animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="1.5s" repeatCount="indefinite"/></rect>
  <text x="355" y="34" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Swap ✓</text>

  <rect x="325" y="70" width="60" height="30" rx="6" fill="#1a1a24" stroke="#f87171" strokeWidth="1.5"/>
  <text x="355" y="89" textAnchor="middle" fontSize="7" fontWeight="600" fill="#f87171">Abort ✗</text>

  <rect x="420" y="15" width="65" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"/>
  <text x="452" y="34" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">Backup</text>

  <rect x="515" y="15" width="70" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="2"/>
  <text x="550" y="34" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Done ✓</text>

  <text x="297" y="28" fontSize="6" fill="#34d399">yes →</text>
  <text x="297" y="82" fontSize="6" fill="#f87171">no →</text>

  <circle r="3" fill="#fbbf24"><animateMotion dur="1.5s" repeatCount="indefinite" path="M82,60 L108,60"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.8s" repeatCount="indefinite" path="M192,60 L218,60"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.5s" repeatCount="indefinite" path="M387,30 L418,30"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.3s" repeatCount="indefinite" path="M487,30 L513,30"/></circle>

  <text x="300" y="115" textAnchor="middle" fontSize="7" fill="#6a6a80">Old index stays live during migration. Auto-aborts if quality drops below threshold.</text>
</svg>
</div>

1. **Load**: Read all chunks from the existing knowledge base
2. **Shadow index**: Re-embed everything with the new model (builds alongside, doesn't touch the old)
3. **Validate**: Run retrieval comparisons to ensure quality is maintained
4. **Cutover**: Swap the new index into place, keep the old as backup

## API

```bash
curl -X POST http://localhost:8000/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge": "my-kb",
    "from_model": "default",
    "to_model": "quantized",
    "run_validation": true
  }'
```

## Safety Features

- **Shadow indexing**: The new index is built alongside the old one. Nothing is lost during migration.
- **Quality validation**: Automatic before/after comparison ensures retrieval quality isn't degraded.
- **Backup**: The old vectors are kept as a backup file until you explicitly delete them.
- **Atomic swap**: The cutover happens in one step — either the new index is live or the old one is.

## When to Migrate

- Upgrading to a better embedding model
- Moving from a general model to a domain-specific one
- Switching providers (e.g., OpenAI → open-source)
- Downgrading to a cheaper model after confirming quality is acceptable (use quantization module first to check)
