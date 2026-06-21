---
sidebar_position: 1
---

# Architecture

RAGForge is designed as independent modules under a shared core, connected by a plugin registry. This keeps each piece testable and replaceable while the whole system feels like one tool.

## System Overview

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '2rem'}}>
<svg width="100%" height="200" viewBox="0 0 700 200">
  <rect x="40" y="10" width="300" height="45" rx="8" fill="none" stroke="#ff6b2c" strokeWidth="1.5" strokeDasharray="4,3"/>
  <text x="190" y="22" textAnchor="middle" fontSize="9" fill="#ff6b2c" fontWeight="700">Clients (Any Language)</text>
  <rect x="55" y="30" width="60" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="85" y="43" textAnchor="middle" fontSize="7" fill="#a0a0b8">Python</text>
  <rect x="125" y="30" width="60" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
  <text x="155" y="43" textAnchor="middle" fontSize="7" fill="#a0a0b8">JS / Go</text>
  <rect x="195" y="30" width="60" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"><animate attributeName="opacity" values="1;0.7;1" dur="2.5s" repeatCount="indefinite"/></rect>
  <text x="225" y="43" textAnchor="middle" fontSize="7" fill="#a0a0b8">Rust / C++</text>
  <rect x="265" y="30" width="60" height="20" rx="4" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1"/>
  <text x="295" y="43" textAnchor="middle" fontSize="7" fill="#a0a0b8">curl</text>

  <rect x="130" y="70" width="120" height="35" rx="8" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="190" y="88" textAnchor="middle" fontSize="9" fontWeight="700" fill="#ff6b2c">HTTP API</text>
  <text x="190" y="99" textAnchor="middle" fontSize="7" fill="#6a6a80">FastAPI + /docs</text>

  <rect x="100" y="125" width="180" height="35" rx="8" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="2"/>
  <text x="190" y="143" textAnchor="middle" fontSize="9" fontWeight="700" fill="#7c6ff8">Core: Models + Registry</text>
  <text x="190" y="154" textAnchor="middle" fontSize="7" fill="#6a6a80">Document, Chunk, @register</text>

  <g>
    <rect x="50" y="175" width="55" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="77" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Parsing</text>
    <rect x="112" y="175" width="55" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="139" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Chunking</text>
    <rect x="174" y="175" width="75" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="211" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Pipeline+Gen</text>
    <rect x="256" y="175" width="55" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="283" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Evaluation</text>
    <rect x="318" y="175" width="65" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="350" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Quantization</text>
    <rect x="390" y="175" width="55" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="417" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Migration</text>
    <rect x="452" y="175" width="70" height="20" rx="4" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
    <text x="487" y="188" textAnchor="middle" fontSize="6" fill="#34d399">Coordination</text>
  </g>

  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M190,52 L190,68"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.8s" repeatCount="indefinite" path="M190,107 L190,123"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="2s" repeatCount="indefinite" path="M190,162 L190,173"/></circle>
</svg>
</div>

## Design Principles

### 1. Shared Core, Independent Modules

Every module depends on `core/` (the data models and registry) but never on each other unless there's a real dependency (e.g., evaluation depends on pipeline for querying).

### 2. Plugin Registry

The registry is the trick that keeps RAGForge extensible:

```python
from ragforge.core.registry import register

@register("chunker", "my-custom")
class MyChunker(Chunker):
    def chunk(self, document: Document) -> list[Chunk]:
        ...
```

Adding a new parser, chunker, or embedding model = adding one file. No giant central file to edit.

### 3. Dual Interface

Every feature works both ways:
- **Python library**: `import ragforge; rf.parse_file("x.md")`
- **HTTP API**: `POST /parse {"path": "x.md"}`

The API layer is a thin translation between HTTP/JSON and the Python modules.

### 4. Zero-Dep Core

The core install requires nothing. Heavy dependencies (FastAPI, ML models, vector DBs) live in optional extras so `pip install ragforge` is instant.

## Data Flow

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '2rem'}}>
<svg width="100%" height="100" viewBox="0 0 700 100">
  <rect x="10" y="35" width="60" height="30" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"/>
  <text x="40" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#ff6b2c">Source Files</text>
  <rect x="95" y="35" width="50" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"/>
  <text x="120" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">Parser</text>
  <rect x="170" y="35" width="55" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1.5"/>
  <text x="197" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#34d399">Chunker</text>
  <rect x="250" y="35" width="55" height="30" rx="6" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1.5"/>
  <text x="277" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#7c6ff8">Embed</text>
  <rect x="330" y="35" width="65" height="30" rx="6" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1.5"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="362" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#7c6ff8">Hybrid Search</text>
  <rect x="420" y="35" width="50" height="30" rx="6" fill="#1a1a24" stroke="#22d3ee" strokeWidth="1.5"/>
  <text x="445" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#22d3ee">Rerank</text>
  <rect x="495" y="35" width="45" height="30" rx="6" fill="#1a1a24" stroke="#a78bfa" strokeWidth="1.5"/>
  <text x="517" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#a78bfa">LLM</text>
  <rect x="565" y="35" width="60" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="2"/>
  <text x="595" y="50" textAnchor="middle" fontSize="7" fontWeight="700" fill="#34d399">Answer</text>
  <text x="595" y="60" textAnchor="middle" fontSize="6" fill="#6a6a80">+ sources</text>

  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.2s" repeatCount="indefinite" path="M72,50 L93,50"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.2s" repeatCount="indefinite" path="M147,50 L168,50"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.2s" repeatCount="indefinite" path="M227,50 L248,50"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.2s" repeatCount="indefinite" path="M307,50 L328,50"/></circle>
  <circle r="3" fill="#22d3ee"><animateMotion dur="1s" repeatCount="indefinite" path="M397,50 L418,50"/></circle>
  <circle r="3" fill="#a78bfa"><animateMotion dur="1s" repeatCount="indefinite" path="M472,50 L493,50"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1s" repeatCount="indefinite" path="M542,50 L563,50"/></circle>

  <text x="350" y="85" textAnchor="middle" fontSize="7" fill="#6a6a80">Data flows left to right: files → clean text → chunks → vectors → search → answer</text>
</svg>
</div>

## Directory Structure

```
ragforge/
├── core/            # Shared models (Document, Chunk) + plugin registry
├── parsing/         # File → Document (txt, md, html, pdf, docling)
├── chunking/        # Document → Chunks (fixed, structure, docling)
├── pipeline/        # Embed + store + retrieve + generate answers
├── evaluation/      # Measure retrieval + generation quality
├── quantization/    # Compress embeddings + measure tradeoff
├── migration/       # Swap embedding models safely
├── coordination/    # Multi-agent blackboard + orchestrator + benchmark
├── api/             # HTTP/JSON endpoints (FastAPI)
├── tracing.py       # SQLite-backed trace store for observability
├── ui_static/       # Pre-built frontend for ragforge ui
└── cli.py           # Command-line interface
```
