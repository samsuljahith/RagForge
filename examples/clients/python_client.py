#!/usr/bin/env python3
"""
RAGForge Python client example.

Demonstrates calling the RAGForge API from Python using only the standard library
(urllib / http.client) — no external dependencies needed. This proves that even in
Python you can use RAGForge purely over HTTP without installing ragforge as a library.

Usage:
    1. Start the server:  ragforge serve
    2. Run this script:   python examples/clients/python_client.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def get(path: str) -> dict:
    """GET request using stdlib urllib."""
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read())


def post(path: str, body: dict) -> dict:
    """POST request using stdlib urllib."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    # 1. Health check
    print("=== Health Check ===")
    print(get("/health"))

    # 2. List capabilities
    print("\n=== Capabilities ===")
    print(get("/capabilities"))

    # 3. Parse text
    print("\n=== Parse ===")
    doc = post("/parse", {
        "text": "# Welcome\n\nThis is a test document.\n\n## Section 2\n\nMore content here.",
        "doc_type": "md",
        "source": "example.md",
    })
    print(f"Document ID: {doc['id']}, Tokens: {doc['token_count']}")

    # 4. Chunk the document
    print("\n=== Chunk (structure-aware) ===")
    result = post("/chunk", {
        "doc": doc,
        "strategy": "structure",
        "options": {"max_tokens": 128},
    })
    print(f"Strategy: {result['strategy']}, Chunks: {result['count']}")
    for chunk in result["chunks"]:
        section = chunk["metadata"].get("section", "")
        print(f"  [{chunk['index']}] ~{chunk['token_count']} tok | {section}")

    # 5. Query a knowledge base (if one exists)
    print("\n=== Query (will 404 if no KB built yet) ===")
    try:
        result = post("/query", {
            "knowledge": "my-kb",
            "question": "How do refunds work?",
            "top_k": 3,
        })
        for chunk in result["chunks"]:
            print(f"  score={chunk['score']:.4f}: {chunk['text'][:80]}...")
    except urllib.error.HTTPError as e:
        detail = json.loads(e.read()).get("detail", "")
        print(f"  (expected) {e.code}: {detail}")


if __name__ == "__main__":
    main()
