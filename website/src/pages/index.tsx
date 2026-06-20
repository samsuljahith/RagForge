/**
 * RAGForge — Colorful Neubrutalism Landing Page
 *
 * Bold saturated colors, thick black borders, chunky shapes, hard shadows.
 * Purple background, lime/yellow/coral cards, retro-playful energy.
 */

import React from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import CodeBlock from '@theme/CodeBlock';

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="nb-hero">
      {/* Floating decorations */}
      <div className="nb-deco nb-deco--1" style={{'--r': '12deg'} as React.CSSProperties} />
      <div className="nb-deco nb-deco--2" />
      <div className="nb-deco nb-deco--3" style={{'--r': '-3deg'} as React.CSSProperties} />
      <div className="nb-deco nb-deco--4" style={{'--r': '-8deg'} as React.CSSProperties} />

      <div className="nb-hero__inner">
        <div className="nb-hero__card nb-animate">
          <img
            src="/RagForge/img/logo-lockup-dark.svg"
            alt="RAGForge"
            className="nb-hero__logo"
            width="220"
            height="44"
          />

          <h1 className="nb-hero__title nb-animate nb-animate--d1">
            Build RAG<br />That Works.
          </h1>

          <p className="nb-hero__tagline nb-animate nb-animate--d2">
            One workshop for building, evaluating, and optimizing RAG — usable
            from any language. Parse, chunk, embed, retrieve. All over HTTP/JSON.
          </p>

          <div
            className="nb-install nb-animate nb-animate--d3"
            onClick={() => navigator.clipboard?.writeText('pip install ragforge')}
            title="Click to copy"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigator.clipboard?.writeText('pip install ragforge')}
          >
            <span className="nb-install__dollar">$</span>
            <code>pip install ragforge</code>
          </div>

          <div className="nb-btn-group nb-animate nb-animate--d4">
            <Link className="nb-btn nb-btn--primary" to="/docs/getting-started/quickstart">
              Get Started →
            </Link>
            <Link className="nb-btn nb-btn--secondary" href="https://github.com/samsuljahith/RagForge">
              ★ GitHub
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Features ─────────────────────────────────────────────────────────────────

const features = [
  {
    name: 'Parsing',
    desc: 'txt, md, html, pdf → Document. Auto-detects format. Zero config.',
    available: true,
  },
  {
    name: 'Chunking',
    desc: 'Structure-aware: keeps tables and code blocks intact. Tags sections.',
    available: true,
  },
  {
    name: 'Pipeline',
    desc: 'Embed → store → dense + BM25 hybrid search (RRF) → reranking. Pluggable.',
    available: true,
  },
  {
    name: 'Evaluation',
    desc: 'Precision, recall, faithfulness vs golden datasets.',
    available: false,
  },
  {
    name: 'Quantization',
    desc: 'Compress embeddings. Measure cost vs quality on your data.',
    available: false,
  },
  {
    name: 'Migration',
    desc: 'Swap embedding models. Shadow index + quality validation.',
    available: false,
  },
];

function Features() {
  return (
    <section className="nb-section nb-section--white">
      <div className="container">
        <span className="nb-section__label">Capabilities</span>
        <h2 className="nb-section__title">What's Built</h2>
        <p className="nb-section__subtitle">
          Independent modules, shared core. Each one registers itself — add features by adding one file.
        </p>
        <div className="nb-features">
          {features.map((f, i) => (
            <div key={i} className="nb-feature">
              <div className="nb-feature__name">{f.name}</div>
              <div className="nb-feature__desc">{f.desc}</div>
              <span className={`nb-badge ${f.available ? 'nb-badge--available' : 'nb-badge--soon'}`}>
                {f.available ? '✓ Available' : '◌ Coming soon'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Code Example ─────────────────────────────────────────────────────────────

function CodeExample() {
  const code = `from ragforge.pipeline import KnowledgeBase

# Parse → structure-aware chunk → embed → store
kb = KnowledgeBase.build(
    name="my-kb",
    sources=["./docs/"],
    chunk_strategy="structure",  # keeps tables + code intact
)

# Hybrid search: dense + BM25 fused via RRF
results = kb.query("How do refunds work?", mode="hybrid", top_k=5)

for chunk, score in results:
    print(f"  [{score:.3f}] {chunk.text[:80]}...")`;

  return (
    <section className="nb-section nb-section--yellow">
      <div className="container">
        <span className="nb-section__label">Example</span>
        <h2 className="nb-section__title">End-to-End in 6 Lines</h2>
        <p className="nb-section__subtitle">
          Parse, chunk, embed, and retrieve. Structure-aware chunking keeps your tables intact.
        </p>
        <div className="nb-code-card">
          <div className="nb-code-card__header">
            <span className="nb-code-card__dot nb-code-card__dot--red" />
            <span className="nb-code-card__dot nb-code-card__dot--yellow" />
            <span className="nb-code-card__dot nb-code-card__dot--green" />
          </div>
          <CodeBlock language="python">{code}</CodeBlock>
        </div>
      </div>
    </section>
  );
}

// ─── Any Language ─────────────────────────────────────────────────────────────

function AnyLanguage() {
  const py = `import requests

resp = requests.post("http://localhost:8000/query", json={
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "mode": "hybrid",
    "top_k": 5,
})
for chunk in resp.json()["chunks"]:
    print(f"  [{chunk['score']:.3f}] {chunk['text'][:80]}")`;

  const js = `const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "How do refunds work?",
    mode: "hybrid",
    top_k: 5,
  }),
});
const { chunks } = await resp.json();`;

  const curl = `curl -s -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "mode": "hybrid",
    "top_k": 5
  }' | jq '.chunks[:3]'`;

  return (
    <section className="nb-section nb-section--lime">
      <div className="container">
        <span className="nb-section__label">Any Language</span>
        <h2 className="nb-section__title">Plain HTTP. Any Client.</h2>
        <p className="nb-section__subtitle">
          Python, JavaScript, Go, Rust, curl — anything with an HTTP client works.
          Interactive docs at <code>/docs</code>.
        </p>
        <div className="nb-code-card">
          <div className="nb-code-card__header">
            <span className="nb-code-card__dot nb-code-card__dot--red" />
            <span className="nb-code-card__dot nb-code-card__dot--yellow" />
            <span className="nb-code-card__dot nb-code-card__dot--green" />
          </div>
          <Tabs>
            <TabItem value="python" label="Python" default>
              <CodeBlock language="python">{py}</CodeBlock>
            </TabItem>
            <TabItem value="js" label="JavaScript">
              <CodeBlock language="javascript">{js}</CodeBlock>
            </TabItem>
            <TabItem value="curl" label="curl">
              <CodeBlock language="bash">{curl}</CodeBlock>
            </TabItem>
          </Tabs>
        </div>
      </div>
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="RAGForge — Build RAG That Works"
      description={siteConfig.tagline}>
      <main>
        <Hero />
        <Features />
        <CodeExample />
        <AnyLanguage />
      </main>
    </Layout>
  );
}
