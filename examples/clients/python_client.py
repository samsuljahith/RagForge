#!/usr/bin/env python3
"""
RAGForge Python client example.

Demonstrates calling the RAGForge API from Python using only the `requests` library.
This proves that even in Python, you can use RAGForge purely over HTTP without
importing ragforge as a library.

Usage:
    1. Start the server:  ragforge serve
    2. Run this script:   python python_client.py
"""

import requests

BASE_URL = "http://127.0.0.1:8000"


def main():
    # 1. Health check
    print("=== Health Check ===")
    resp = requests.get(f"{BASE_URL}/health")
    resp.raise_for_status()
    print(resp.json())

    # 2. List capabilities
    print("\n=== Capabilities ===")
    resp = requests.get(f"{BASE_URL}/capabilities")
    resp.raise_for_status()
    print(resp.json())

    # 3. Parse text
    print("\n=== Parse ===")
    resp = requests.post(f"{BASE_URL}/parse", json={
        "text": "# Welcome\n\nThis is a test document.\n\n## Section 2\n\nMore content here.",
        "doc_type": "md",
        "source": "example.md",
    })
    resp.raise_for_status()
    doc = resp.json()
    print(f"Document ID: {doc['id']}, Tokens: {doc['token_count']}")

    # 4. Chunk the document
    print("\n=== Chunk (structure-aware) ===")
    resp = requests.post(f"{BASE_URL}/chunk", json={
        "doc": doc,
        "strategy": "structure",
        "options": {"max_tokens": 128},
    })
    resp.raise_for_status()
    result = resp.json()
    print(f"Strategy: {result['strategy']}, Chunks: {result['count']}")
    for chunk in result["chunks"]:
        section = chunk["metadata"].get("section", "")
        print(f"  [{chunk['index']}] ~{chunk['token_count']} tok | {section}")

    # 5. Query a knowledge base (if one exists)
    print("\n=== Query (will 404 if no KB built yet) ===")
    resp = requests.post(f"{BASE_URL}/query", json={
        "knowledge": "my-kb",
        "question": "How do refunds work?",
        "top_k": 3,
    })
    if resp.status_code == 200:
        result = resp.json()
        for chunk in result["chunks"]:
            print(f"  score={chunk['score']:.4f}: {chunk['text'][:80]}...")
    else:
        print(f"  (expected) {resp.status_code}: {resp.json().get('detail', '')}")


if __name__ == "__main__":
    main()
