---
sidebar_position: 2
---

# Client Examples

Working examples of calling the RAGForge API from different languages. All examples do the same thing: parse text, chunk it, and query a knowledge base.

## Python

```python
import requests

BASE = "http://localhost:8000"

# Parse
doc = requests.post(f"{BASE}/parse", json={
    "text": "# Refunds\n\nRefunds within 30 days.",
    "doc_type": "md",
}).json()

# Chunk
chunks = requests.post(f"{BASE}/chunk", json={
    "doc": doc,
    "strategy": "structure",
}).json()

print(f"Got {chunks['count']} chunks")

# Query (if KB exists)
result = requests.post(f"{BASE}/query", json={
    "knowledge": "my-kb",
    "question": "Refund policy?",
    "top_k": 3,
}).json()

for chunk in result["chunks"]:
    print(f"  [{chunk['score']:.3f}] {chunk['text'][:80]}")
```

## JavaScript / Node.js

```javascript
const BASE = "http://localhost:8000";

// Parse
const doc = await fetch(`${BASE}/parse`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "# Refunds\n\nRefunds within 30 days.",
    doc_type: "md",
  }),
}).then(r => r.json());

// Chunk
const chunks = await fetch(`${BASE}/chunk`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ doc, strategy: "structure" }),
}).then(r => r.json());

console.log(`Got ${chunks.count} chunks`);

// Query
const result = await fetch(`${BASE}/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "Refund policy?",
    top_k: 3,
  }),
}).then(r => r.json());

result.chunks.forEach(c =>
  console.log(`  [${c.score.toFixed(3)}] ${c.text.slice(0, 80)}`)
);
```

## curl

```bash
BASE="http://localhost:8000"

# Parse
DOC=$(curl -s -X POST "$BASE/parse" \
  -H "Content-Type: application/json" \
  -d '{"text": "# Refunds\n\nRefunds within 30 days.", "doc_type": "md"}')

# Chunk
echo "$DOC" | curl -s -X POST "$BASE/chunk" \
  -H "Content-Type: application/json" \
  -d "{\"doc\": $DOC, \"strategy\": \"structure\"}" | jq .count

# Query
curl -s -X POST "$BASE/query" \
  -H "Content-Type: application/json" \
  -d '{"knowledge": "my-kb", "question": "Refund policy?", "top_k": 3}' | jq .chunks
```

## Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

func main() {
    body, _ := json.Marshal(map[string]interface{}{
        "knowledge": "my-kb",
        "question":  "Refund policy?",
        "top_k":     3,
    })

    resp, _ := http.Post(
        "http://localhost:8000/query",
        "application/json",
        bytes.NewBuffer(body),
    )
    defer resp.Body.Close()

    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    fmt.Printf("Got %v chunks\n", len(result["chunks"].([]interface{})))
}
```

## Java

```java
import java.net.http.*;
import java.net.URI;

var client = HttpClient.newHttpClient();
var request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:8000/query"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString("""
        {"knowledge": "my-kb", "question": "Refund policy?", "top_k": 3}
        """))
    .build();

var response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body());
```

## Auto-Generated Clients

For typed client SDKs, use the OpenAPI schema:

```bash
# Get the schema
curl http://localhost:8000/openapi.json > openapi.json

# Generate a TypeScript client
npx openapi-typescript-codegen --input openapi.json --output ./client

# Generate a Go client
oapi-codegen -package ragforge openapi.json > client.go
```

## Notes

- **Any language works** — if it can make HTTP requests, it can use RAGForge
- **No SDK required** — the API is simple enough that raw HTTP calls are clear
- **Standard errors** — HTTP status codes (400, 404, 500) with JSON error details
- **Interactive docs** — try everything at `http://localhost:8000/docs` first
