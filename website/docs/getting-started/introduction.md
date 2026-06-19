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

| Module | Status | Description |
|--------|--------|-------------|
| Core | Available | Document/Chunk data models + plugin registry |
| Parsing | Available | txt, md, html, pdf → Document |
| Chunking | Available | Fixed + structure-aware → Chunks |
| Pipeline | Available | Embed + store + hybrid search + rerank |
| Evaluation | Available | Precision, recall, faithfulness metrics |
| Quantization | Available | Quantize + compare cost/quality |
| Migration | Available | Re-embed + validate + safe model swap |
| API | Available | HTTP/JSON endpoints for all features |

## Next Steps

- [Install RAGForge](./installation)
- [Quick start guide](./quickstart)
- [Architecture overview](../core-concepts/architecture)
