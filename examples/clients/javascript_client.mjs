#!/usr/bin/env node
/**
 * RAGForge JavaScript/Node.js client example.
 *
 * Demonstrates calling the RAGForge API from JavaScript using only the
 * built-in `fetch` API (Node 18+). No Python required on the client side.
 *
 * Usage:
 *   1. Start the server:  ragforge serve
 *   2. Run this script:   node javascript_client.mjs
 */

const BASE_URL = "http://127.0.0.1:8000";

async function main() {
  // 1. Health check
  console.log("=== Health Check ===");
  const healthResp = await fetch(`${BASE_URL}/health`);
  console.log(await healthResp.json());

  // 2. List capabilities
  console.log("\n=== Capabilities ===");
  const capsResp = await fetch(`${BASE_URL}/capabilities`);
  console.log(JSON.stringify(await capsResp.json(), null, 2));

  // 3. Parse some text
  console.log("\n=== Parse ===");
  const parseResp = await fetch(`${BASE_URL}/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: "# Welcome\n\nThis is a test document.\n\n## Section 2\n\nMore content here.",
      doc_type: "md",
      source: "example.md",
    }),
  });
  const doc = await parseResp.json();
  console.log(`Document ID: ${doc.id}, Tokens: ${doc.token_count}`);

  // 4. Chunk the document
  console.log("\n=== Chunk (structure-aware) ===");
  const chunkResp = await fetch(`${BASE_URL}/chunk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doc: doc,
      strategy: "structure",
      options: { max_tokens: 128 },
    }),
  });
  const chunkResult = await chunkResp.json();
  console.log(`Strategy: ${chunkResult.strategy}, Chunks: ${chunkResult.count}`);
  for (const chunk of chunkResult.chunks) {
    const section = chunk.metadata.section || "";
    console.log(`  [${chunk.index}] ~${chunk.token_count} tok | ${section}`);
  }

  // 5. Query a knowledge base
  console.log("\n=== Query ===");
  const queryResp = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      knowledge: "my-kb",
      question: "How do refunds work?",
      top_k: 3,
    }),
  });
  if (queryResp.ok) {
    const result = await queryResp.json();
    for (const chunk of result.chunks) {
      console.log(`  score=${chunk.score.toFixed(4)}: ${chunk.text.slice(0, 80)}...`);
    }
  } else {
    const err = await queryResp.json();
    console.log(`  (expected) ${queryResp.status}: ${err.detail || ""}`);
  }
}

main().catch(console.error);
