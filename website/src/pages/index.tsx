/**
 * RAGForge — Anime Motion Graphic UI + Caveman Mode
 * 
 * Hammer-themed motion graphics, speed lines, 21st.dev-style glowing cards,
 * with a small caveman toggle in the header that switches all content to
 * simple caveman explanations.
 */

import React, {useState} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import CodeBlock from '@theme/CodeBlock';

// ─── Caveman Content ──────────────────────────────────────────────────────────

const cave = {
  tagline: "Me make computer find answers in big pile of documents. Any computer language can talk to me. Me simple. Me strong. 🦴",
  features: [
    { icon: "📄", name: "Parsing", desc: "Me take file. Me read file. Me turn into clean text. PDF, HTML, Markdown — me eat all. 🍖" },
    { icon: "🪓", name: "Chunking", desc: "Big text too big for brain. Me chop smart — no break table in half! Me keep code together!" },
    { icon: "🏆", name: "Pipeline", desc: "Me remember where each piece is. You ask question, me search TWO ways (like smell AND sight) then pick best!" },
    { icon: "📊", name: "Evaluation", desc: "Me test myself! Got list of right answers. Me check score. Like report card for robot!" },
    { icon: "🥜", name: "Quantization", desc: "Me brain too big, too expensive. Me shrink brain, check still smart. Smaller = cheaper!" },
    { icon: "🔄", name: "Migration", desc: "Me want new brain? Me carefully copy, check nothing broke, THEN switch. Safe!" },
  ],
  dictionary: [
    { term: "RAG", text: "🦕 Instead of AI making up answers (bad!), AI first FINDS documents, THEN answers from them. Open-book exam!" },
    { term: "Agent", text: "🤖 Computer that DO things on own. Reads, thinks, uses tools. Robot assistant that actually works!" },
    { term: "Tracing", text: "👁️ Watch AI brain step by step. Like security camera. See where it searched, what it found, what broke!" },
    { term: "LLM", text: "🗣️ Big computer brain trained on text. GPT, Claude, Llama. Good at words but sometimes lies (why need RAG!)." },
    { term: "Embedding", text: "🧲 Turn words into numbers. Similar words = similar numbers. How computer finds similar things!" },
    { term: "Quantization", text: "📦 Make AI brain SMALLER. 32 bits → 8 bits. Less precise but MUCH lighter. Like measuring in cm not mm." },
  ],
  code: `# CAVEMAN CODE — simple version!
# Step 1: Me eat documents
# Step 2: Me chop smart (keep tables whole!)
# Step 3: Human ask, me find answer FAST
# Step 4: Me show proof (which chunks me found)

from ragforge.pipeline import KnowledgeBase

kb = KnowledgeBase.build(name="my-kb", sources=["./docs/"])
results = kb.query("How refund work?", mode="hybrid")
for chunk, score in results:
    print(f"  Me found! [{score:.3f}] {chunk.text[:60]}...")`,
};

// ─── Normal Content ───────────────────────────────────────────────────────────

const normal = {
  features: [
    { icon: "⚡", name: "Parsing", desc: "txt, md, html, pdf → Document. Auto-detects format by extension. Zero config." },
    { icon: "🧩", name: "Chunking", desc: "Structure-aware splitting. Keeps tables and code blocks intact. Tags each chunk with its section." },
    { icon: "🔍", name: "Pipeline", desc: "Embed → store → hybrid search (dense + BM25 via RRF) → cross-encoder reranking. Fully pluggable." },
    { icon: "📊", name: "Evaluation", desc: "Hit rate, MRR, precision@k, faithfulness. A/B compare configs. Prove changes help." },
    { icon: "📦", name: "Quantization", desc: "Compress embeddings. Measure cost vs quality tradeoff on your own data before committing." },
    { icon: "🔄", name: "Migration", desc: "Safely move between embedding models. Shadow indexing + quality validation + atomic swap." },
  ],
};

// ─── Battle Animation (Video) ─────────────────────────────────────────────────

function BattleVideo({caveman}: {caveman: boolean}) {
  return (
    <div className="battle-video-wrap">
      <video
        className="battle-video"
        autoPlay
        loop
        muted
        playsInline
        key={caveman ? 'anime' : 'realistic'}
        src={caveman ? '/RagForge/videos/Vid2.mp4' : '/RagForge/videos/Vid1.mp4'}
      />
      <div className="battle-video__overlay" />
    </div>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero({caveman}: {caveman: boolean}) {
  return (
    <section className="rf-hero">
      {/* Video background */}
      <BattleVideo caveman={caveman} />

      <div className="rf-hero__content">
        <h1 className="rf-hero__title rf-animate rf-animate--d1">
          {caveman
            ? <>Me Build RAG.<br/>Me Find <em>Answers</em>. 🦴</>
            : <>Forge your RAG.<br/><em>Retrieve what matters.</em></>
          }
        </h1>

        <p className="rf-hero__subtitle rf-animate rf-animate--d2">
          {caveman ? cave.tagline : "One toolkit for parsing, chunking, retrieval, evaluation, and optimization — exposed as HTTP/JSON so any language can use it."}
        </p>

        <div className="rf-install rf-animate rf-animate--d3" onClick={() => navigator.clipboard?.writeText('pip install ragforge')} role="button" tabIndex={0}>
          <span className="rf-install__dollar">$</span>
          <code>pip install ragforge</code>
        </div>

        <div className="rf-btn-group rf-animate rf-animate--d4">
          <Link className="rf-btn rf-btn--primary" to="/docs/getting-started/quickstart">
            {caveman ? "Me Start! 🔥" : "Get Started →"}
          </Link>
          <Link className="rf-btn rf-btn--ghost" href="https://github.com/samsuljahith/RagForge">
            {caveman ? "🦴 Cave Drawings" : "GitHub ↗"}
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Features ─────────────────────────────────────────────────────────────────

function Features({caveman}: {caveman: boolean}) {
  const items = caveman ? cave.features : normal.features;
  return (
    <section className="rf-section rf-section--speed">
      <div className="container">
        <span className="rf-section__label">{caveman ? "🦴 me powers" : "capabilities"}</span>
        <h2 className="rf-section__title">{caveman ? "What Me Can Do" : "Everything RAG, One Toolkit"}</h2>
        <p className="rf-section__subtitle">
          {caveman ? "Each power = one file. Add new power easy!" : "Independent modules under a shared core. Add a new capability by adding one file."}
        </p>
        <div className="rf-cards">
          {items.map((f, i) => (
            <div key={i} className="rf-card">
              <span className="rf-card__icon">{f.icon}</span>
              <div className="rf-card__title">{f.name}</div>
              <div className="rf-card__desc">{f.desc}</div>
              <span className={`rf-card__badge ${i < 4 ? 'rf-card__badge--available' : 'rf-card__badge--soon'}`}>
                {i < 4 ? (caveman ? "🦴 ready!" : "available") : (caveman ? "coming..." : "coming soon")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Caveman Dictionary (only shown in caveman mode) ──────────────────────────

function CavemanDictionary() {
  return (
    <section className="rf-section rf-caveman-section">
      <div className="container">
        <span className="rf-section__label">🦕 caveman dictionary</span>
        <h2 className="rf-section__title">Big Words Made Simple</h2>
        <p className="rf-section__subtitle">Me explain all scary tech words. No PhD needed!</p>
        <div className="rf-cards">
          {cave.dictionary.map((item, i) => (
            <div key={i} className="rf-caveman-card">
              <div className="rf-caveman-card__term">{item.term}</div>
              <div className="rf-caveman-card__text">{item.text}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Code Example ─────────────────────────────────────────────────────────────

function CodeExample({caveman}: {caveman: boolean}) {
  const normalCode = `from ragforge.pipeline import KnowledgeBase

# Parse → structure-aware chunk → embed → store
kb = KnowledgeBase.build(
    name="my-kb",
    sources=["./docs/"],
    chunk_strategy="structure",
)

# Hybrid search: dense + BM25 fused via Reciprocal Rank Fusion
results = kb.query("How do refunds work?", mode="hybrid", top_k=5)

for chunk, score in results:
    print(f"  [{score:.3f}] {chunk.text[:80]}...")`;

  return (
    <section className="rf-section">
      <div className="container">
        <span className="rf-section__label">{caveman ? "🪨 cave painting" : "example"}</span>
        <h2 className="rf-section__title">{caveman ? "Me Show How" : "End-to-End in 6 Lines"}</h2>
        <div className="rf-code-card">
          <div className="rf-code-card__header">
            <span className="rf-code-card__dot rf-code-card__dot--red" />
            <span className="rf-code-card__dot rf-code-card__dot--yellow" />
            <span className="rf-code-card__dot rf-code-card__dot--green" />
            <span className="rf-code-card__title">Python</span>
          </div>
          <CodeBlock language="python">{caveman ? cave.code : normalCode}</CodeBlock>
        </div>
      </div>
    </section>
  );
}

// ─── Any Language ─────────────────────────────────────────────────────────────

function AnyLanguage({caveman}: {caveman: boolean}) {
  const py = `import requests
resp = requests.post("http://localhost:8000/query", json={
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "mode": "hybrid", "top_k": 5,
})
for c in resp.json()["chunks"]:
    print(f"  [{c['score']:.3f}] {c['text'][:80]}")`;

  const js = `const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "How do refunds work?",
    mode: "hybrid", top_k: 5,
  }),
});
const { chunks } = await resp.json();`;

  const curl = `curl -s -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"knowledge":"my-kb","question":"How do refunds work?","mode":"hybrid","top_k":5}' \\
  | jq '.chunks[:3]'`;

  return (
    <section className="rf-section rf-section--speed">
      <div className="container">
        <span className="rf-section__label">{caveman ? "🗣️ any tribe" : "any language"}</span>
        <h2 className="rf-section__title">{caveman ? "All Tribes Welcome!" : "Plain HTTP. Any Client."}</h2>
        <p className="rf-section__subtitle">
          {caveman ? "Python tribe, JavaScript tribe, curl tribe — ALL talk same HTTP!" : "Python, JavaScript, Go, Rust, curl — anything with an HTTP client."}
        </p>
        <div className="rf-code-cards">
          <div className="rf-code-card">
            <div className="rf-code-card__header">
              <span className="rf-code-card__dot rf-code-card__dot--red" />
              <span className="rf-code-card__dot rf-code-card__dot--yellow" />
              <span className="rf-code-card__dot rf-code-card__dot--green" />
              <span className="rf-code-card__title">Python</span>
            </div>
            <CodeBlock language="python">{py}</CodeBlock>
          </div>
          <div className="rf-code-card">
            <div className="rf-code-card__header">
              <span className="rf-code-card__dot rf-code-card__dot--red" />
              <span className="rf-code-card__dot rf-code-card__dot--yellow" />
              <span className="rf-code-card__dot rf-code-card__dot--green" />
              <span className="rf-code-card__title">JavaScript</span>
            </div>
            <CodeBlock language="javascript">{js}</CodeBlock>
          </div>
          <div className="rf-code-card">
            <div className="rf-code-card__header">
              <span className="rf-code-card__dot rf-code-card__dot--red" />
              <span className="rf-code-card__dot rf-code-card__dot--yellow" />
              <span className="rf-code-card__dot rf-code-card__dot--green" />
              <span className="rf-code-card__title">curl</span>
            </div>
            <CodeBlock language="bash">{curl}</CodeBlock>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  const [caveman, setCaveman] = useState(false);

  return (
    <Layout title="RAGForge" description={siteConfig.tagline}>
      {/* Caveman toggle — injected into navbar area via CSS positioning */}
      <button
        className={`caveman-nav-btn ${caveman ? 'caveman-nav-btn--active' : ''}`}
        onClick={() => setCaveman(!caveman)}
        aria-label="Toggle caveman mode"
      >
        <span className="caveman-nav-btn__icon">{caveman ? '🧠' : '🧌'}</span>
        <span className="caveman-nav-btn__label">{caveman ? 'Normal' : 'Caveman'}</span>
      </button>
      <main>
        <Hero caveman={caveman} />
        <Features caveman={caveman} />
        {caveman && <CavemanDictionary />}
        <CodeExample caveman={caveman} />
        <AnyLanguage caveman={caveman} />
      </main>
    </Layout>
  );
}
