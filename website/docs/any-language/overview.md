---
sidebar_position: 1
---

# Using from Any Language

This is RAGForge's key differentiator: **every feature is reachable over an HTTP/JSON API**. Your agent can be written in Python, JavaScript, Go, Java, C++, Rust, or anything else that can make HTTP requests.

## How It Works

RAGForge runs as a server (or Docker container). Your agent talks to it over plain HTTP:

<div style={{background: '#14141e', borderRadius: '14px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem'}}>
<svg width="100%" height="100" viewBox="0 0 500 100">
  <rect x="20" y="25" width="130" height="50" rx="8" fill="none" stroke="#7c6ff8" strokeWidth="1.5" strokeDasharray="4,3"/>
  <text x="85" y="18" textAnchor="middle" fontSize="8" fill="#7c6ff8" fontWeight="600">Your Agent (any language)</text>
  <rect x="35" y="35" width="100" height="30" rx="6" fill="#1a1a24" stroke="#7c6ff8" strokeWidth="1.5"><animate attributeName="opacity" values="1;0.7;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="85" y="54" textAnchor="middle" fontSize="8" fontWeight="600" fill="#7c6ff8">Your Code</text>
  <rect x="280" y="20" width="170" height="60" rx="8" fill="none" stroke="#ff6b2c" strokeWidth="1.5" strokeDasharray="4,3"/>
  <text x="365" y="14" textAnchor="middle" fontSize="8" fill="#ff6b2c" fontWeight="600">RAGForge Server</text>
  <rect x="295" y="30" width="80" height="30" rx="6" fill="#1a1a24" stroke="#ff6b2c" strokeWidth="1.5"><animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/></rect>
  <text x="335" y="49" textAnchor="middle" fontSize="8" fontWeight="600" fill="#ff6b2c">HTTP API</text>
  <rect x="385" y="30" width="55" height="30" rx="6" fill="#1a1a24" stroke="#34d399" strokeWidth="1"/>
  <text x="412" y="49" textAnchor="middle" fontSize="7" fill="#34d399">/docs</text>
  <text x="250" y="40" textAnchor="middle" fontSize="7" fill="#a0a0b8">POST →</text>
  <text x="250" y="60" textAnchor="middle" fontSize="7" fill="#a0a0b8">← JSON</text>
  <circle r="4" fill="#ff6b2c"><animateMotion dur="1.5s" repeatCount="indefinite" path="M137,50 L293,45"/></circle>
  <circle r="4" fill="#34d399"><animateMotion dur="1.8s" repeatCount="indefinite" path="M293,55 L137,55"/></circle>
  <text x="250" y="90" textAnchor="middle" fontSize="7" fill="#6a6a80">Any language with an HTTP client → full RAGForge functionality</text>
</svg>
</div>

## Starting the Server

```bash
# Install with API dependencies
pip install ragforge[api]

# Start the server
ragforge serve --host 0.0.0.0 --port 8000

# Or with Docker
docker run -p 8000:8000 ragforge
```

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server status + version |
| `/capabilities` | GET | List registered parsers, chunkers, etc. |
| `/parse` | POST | Parse text/file into a Document |
| `/chunk` | POST | Chunk a Document |
| `/knowledge` | POST | Build a knowledge base |
| `/query` | POST | Query a knowledge base |
| `/evaluate` | POST | Evaluate retrieval quality |
| `/quantize` | POST | Quantize and compare |
| `/migrate` | POST | Migrate between models |

## Interactive Documentation

FastAPI auto-generates interactive docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

You can try every endpoint directly from your browser — send requests and see responses without writing any code.

## The Pattern

Every endpoint follows the same pattern:

1. Send a JSON POST request
2. Get a JSON response
3. Use standard HTTP status codes for errors

```
POST /query
Content-Type: application/json

{"knowledge": "my-kb", "question": "...", "top_k": 5}

→ 200 OK
{"question": "...", "chunks": [...], "answer": null}
```

## Language Examples

See the [client examples](./clients) page for working code in Python, JavaScript, and curl. The same HTTP calls work from Go, Java, C++, Rust, Ruby, PHP — any language with an HTTP client.

## Why Not a Python SDK for Other Languages?

Because you don't need one. The API is simple enough that a few lines of HTTP calls in your language are clearer than learning a wrapper library. And you get:

- No dependency on a Python-specific SDK
- No version compatibility issues
- No build toolchain requirements
- Debugging with standard HTTP tools (curl, Postman, browser dev tools)

If you want a typed client in your language, you can auto-generate one from the OpenAPI schema at `/openapi.json`.
