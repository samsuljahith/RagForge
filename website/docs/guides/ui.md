---
sidebar_position: 8
---

# Local UI Dashboard

RAGForge includes a local web dashboard for observing, debugging, and interacting with your RAG system. Launch it with one command and get three views: traces, evaluation, and chat.

Think of it as the "developer tools" for your RAG pipeline — see what happened under the hood without digging through logs.

## Install & Launch

```bash
pip install ragforge[ui]
ragforge ui
```

This starts the API server with a web frontend mounted at `http://localhost:8000/ui`. A browser window opens automatically.

```bash
# Custom port, no auto-open browser
ragforge ui --port 9000 --no-browser
```

## Three Views

### 1. Traces

Every pipeline query is automatically traced and stored in SQLite (`~/.ragforge/traces.db`). The Traces view shows:

- **Timeline** of all queries with timestamps, duration, and status
- **Step-by-step breakdown** of each query: retrieval (what was searched, what was found), reranking, prompt construction, LLM response
- **Token counts and timing** per step
- **Coordination traces** — multi-agent runs also appear here, showing which agent fired and what it wrote

Use this to debug why a query returned bad results — was it retrieval (wrong chunks), reranking (good chunks filtered out), or generation (LLM hallucinated)?

### 2. Evaluation

Run evaluations from the UI and view results:

- Score dashboard showing retrieval metrics (hit rate, MRR, precision)
- Per-query drill-down: see which questions failed and why
- Historical comparison: track how metrics change over time

### 3. Chat

Interactive RAG chat interface:

- Ask questions against any loaded knowledge base
- See the retrieved chunks alongside the generated answer
- Source highlighting shows which chunks were used
- Useful for quick manual testing and demos

## Architecture

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="100" viewBox="0 0 500 100">
  <rect x="20" y="30" width="80" height="40" rx="8" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"><animate attributeName="stroke-opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="60" y="50" textAnchor="middle" fontSize="8" fontWeight="600" fill="#ff6b2c">Browser</text>
  <text x="60" y="62" textAnchor="middle" fontSize="6" fill="#6a6a80">React SPA</text>

  <rect x="160" y="25" width="90" height="50" rx="8" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="2"><animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.8s" repeatCount="indefinite"/></rect>
  <text x="205" y="47" textAnchor="middle" fontSize="8" fontWeight="700" fill="#7c6ff8">FastAPI</text>
  <text x="205" y="60" textAnchor="middle" fontSize="6" fill="#a78bfa">same server</text>

  <rect x="310" y="15" width="75" height="28" rx="6" fill="#1a1a24" stroke="#2dd4bf" strokeWidth="1"/>
  <text x="347" y="33" textAnchor="middle" fontSize="7" fill="#2dd4bf">Traces (SQLite)</text>

  <rect x="310" y="48" width="75" height="28" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
  <text x="347" y="66" textAnchor="middle" fontSize="7" fill="#34d399">Knowledge Bases</text>

  <rect x="400" y="30" width="75" height="28" rx="6" fill="#1a1a24" stroke="#22d3ee" strokeWidth="1"/>
  <text x="437" y="48" textAnchor="middle" fontSize="7" fill="#22d3ee">Evaluation</text>

  <circle r="3" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M102,50 L158,50"/></circle>
  <circle r="3" fill="#7c6ff8"><animateMotion dur="1.5s" repeatCount="indefinite" path="M252,35 L308,29"/></circle>
  <circle r="3" fill="#34d399"><animateMotion dur="1.8s" repeatCount="indefinite" path="M252,55 L308,62"/></circle>

  <text x="250" y="92" textAnchor="middle" fontSize="7" fill="#6a6a80">One server serves the UI, API, and docs — no separate process needed</text>
</svg>
</div>

The UI is a pre-built React+Vite single-page app served as static files from `ragforge/ui_static/`. The backend uses the same FastAPI app as the main API — no separate server needed.

## API Endpoints (used by the UI)

| Endpoint | Description |
|----------|-------------|
| `GET /traces` | List recent traces |
| `GET /traces/{run_id}` | Get full trace detail |
| `POST /ui/eval/run` | Run evaluation from UI |
| `GET /ui/eval/history` | Get evaluation history |
| `POST /ui/chat` | Send a chat message (query + generate) |

These endpoints are available when running `ragforge serve` or `ragforge ui`.

## When to Use

- **Debugging**: A query returns bad results → open traces, see what went wrong at each step
- **Demo**: Show stakeholders that your RAG system finds and cites correct sources
- **Evaluation**: Run evals without the CLI, compare results visually
- **Development**: Quick feedback loop while tweaking chunking/embedding strategies
