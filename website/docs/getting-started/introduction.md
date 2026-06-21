---
sidebar_position: 1
---

# Introduction

**RAGForge** is a Python-based, language-agnostic platform that brings all RAG (Retrieval-Augmented Generation) engineering tasks into one tool.

## The Problem

Building a real RAG system today means juggling separate tools for:

- Parsing documents into clean text
- Chunking text into retrievable pieces
- Embedding and storing vectors
- Retrieval with search and reranking
- Evaluating retrieval quality
- Quantizing models for cost savings
- Migrating between embedding models

Each tool has its own API, its own data format, and its own way of doing things. You spend more time gluing tools together than building your actual application.

## The Solution

RAGForge brings these tasks into one place — built as clean, independent modules under a shared core, so it feels like one tool without becoming a tangled mess.

### Key Design Principles

- **Language-agnostic**: Everything is reachable over an HTTP/JSON API. Your agent can be written in Python, JavaScript, Go, C++, or any language that can make HTTP requests.
- **Modular**: Each capability is its own module that registers itself. Adding a new parser or chunker means writing one file — never editing a giant central one.
- **Dual interface**: Every feature works both as an importable Python library AND through the API.
- **Lightweight core**: The core install has zero dependencies. Heavy/optional features (PDF, ML models, vector DBs) are opt-in via extras.

## What's Built

| Module | Description |
|--------|-------------|
| Core | Document/Chunk data models + plugin registry |
| Parsing | txt, md, html, pdf → Document (+ optional Docling backend for complex docs) |
| Chunking | Fixed + structure-aware + Docling → Chunks |
| Pipeline | Embed + store + hybrid search (dense + BM25) + reranking |
| Answer Generation | Grounded answers with source citations (OpenAI / Anthropic / Ollama) |
| Evaluation | Hit rate, MRR, precision@k, faithfulness. A/B comparison |
| Quantization | Compress embeddings + measure cost/quality tradeoff |
| Migration | Re-embed + validate + safe model swap |
| Coordination | Multi-agent blackboard — cheaper than direct messaging |
| Local UI | Tracing dashboard, evaluation viewer, chat interface |
| API | HTTP/JSON endpoints for all features |

## Next Steps

- [Install RAGForge](./installation)
- [Quick start guide](./quickstart)
- [Architecture overview](../core-concepts/architecture)
