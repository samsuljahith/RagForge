#!/usr/bin/env bash
# RAGForge curl client example.
#
# Demonstrates calling the RAGForge API using only curl + jq.
# Any language that can make HTTP requests can use RAGForge the same way.
#
# Usage:
#   1. Start the server:  ragforge serve
#   2. Run this script:   bash curl_example.sh

BASE_URL="http://127.0.0.1:8000"

echo "=== Health Check ==="
curl -s "$BASE_URL/health" | jq .

echo ""
echo "=== Capabilities ==="
curl -s "$BASE_URL/capabilities" | jq .

echo ""
echo "=== Parse ==="
DOC=$(curl -s -X POST "$BASE_URL/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "# Welcome\n\nThis is a test document.\n\n## Section 2\n\nMore content here.",
    "doc_type": "md",
    "source": "example.md"
  }')
echo "$DOC" | jq '{id: .id, tokens: .token_count, source: .source}'

echo ""
echo "=== Chunk (structure-aware) ==="
CHUNKS=$(curl -s -X POST "$BASE_URL/chunk" \
  -H "Content-Type: application/json" \
  -d "{
    \"doc\": $DOC,
    \"strategy\": \"structure\",
    \"options\": {\"max_tokens\": 128}
  }")
echo "$CHUNKS" | jq '{strategy: .strategy, count: .count, chunks: [.chunks[] | {index, token_count, section: .metadata.section}]}'

echo ""
echo "=== Query (will 404 if no KB built) ==="
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "top_k": 3
  }' | jq .
