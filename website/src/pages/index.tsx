/**
 * RAGForge Homepage — Mascot-centered bright SaaS landing page.
 *
 * Layout:
 *   1. Hero (mascot + video background + sparks + tagline)
 *   2. Feature Explorer (left list + right interactive demo panel)
 *   3. "Any Language" code examples
 *   4. "What's Inside" overview grid
 *   5. Footer with small mascot accent
 */

import React, {useState} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import CodeBlock from '@theme/CodeBlock';
import {featureDemos, FeatureDemo, MetricData, ChunkResult, TimelineStep} from '../data/featureDemos';
import {flowMap} from '../components/AnimatedFlows';
import {featureFlowMap} from '../components/FeatureFlows';
import {
  FileText, LayoutGrid, Search, MessageSquare, BarChart3,
  Minimize2, Network, Activity, RefreshCw,
} from 'lucide-react';

// Map icon names to Lucide components
const iconComponents: Record<string, React.FC<{size?: number; color?: string}>> = {
  FileText, LayoutGrid, Search, MessageSquare, BarChart3,
  Minimize2, Network, Activity, RefreshCw,
};

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="rf-hero">
      {/* Background video — Vid1 fight scene */}
      <div className="rf-hero__video-wrap">
        <video
          className="rf-hero__video rf-hero__video--1"
          autoPlay
          loop
          muted
          playsInline
          src="/videos/Vid1.mp4"
        />
        <div className="rf-hero__video-overlay" />
      </div>

      <div className="rf-hero__content">
        {/* Left: text */}
        <div className="rf-hero__text">
          <h1 className="rf-hero__title rf-animate rf-animate--d1">
            Build, evaluate &<br/>optimize <em>RAG</em>
          </h1>
          <p className="rf-hero__subtitle rf-animate rf-animate--d2">
            One toolkit for parsing, chunking, retrieval, evaluation, and multi-agent coordination — exposed as HTTP/JSON so any language can use it.
          </p>
          <div className="rf-install rf-animate rf-animate--d3" onClick={() => navigator.clipboard?.writeText('pip install ragforge')} role="button" tabIndex={0} aria-label="Copy install command">
            <span className="rf-install__dollar">$</span>
            <code>pip install ragforge</code>
          </div>
          <div className="rf-btn-group rf-animate rf-animate--d4">
            <Link className="rf-btn rf-btn--primary" to="/docs/getting-started/quickstart">
              Get Started →
            </Link>
            <Link className="rf-btn rf-btn--ghost" href="https://github.com/samsuljahith/RagForge">
              GitHub ↗
            </Link>
          </div>
        </div>

        {/* Right: mascot with sparks */}
        <div className="rf-hero__mascot-wrap rf-animate rf-animate--d2">
          <img
            className="rf-hero__mascot"
            src="/img/ragforge-mascot.png"
            alt="RAGForge mascot — a cute robot blacksmith forging an AI cube"
            width={280}
            height={280}
          />
          <div className="rf-hero__sparks" aria-hidden="true">
            <span className="rf-hero__spark" />
            <span className="rf-hero__spark" />
            <span className="rf-hero__spark" />
            <span className="rf-hero__spark" />
            <span className="rf-hero__spark" />
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Selling Points (Why RAGForge) ────────────────────────────────────────────

const sellingPoints = [
  {
    id: 'any-language',
    icon: '🌐',
    title: 'Any Language, One API',
    text: 'HTTP/JSON API so Python, JavaScript, Go, Rust, C++ agents all connect the same way. Your agent doesn\'t need to be written in Python.',
    stat: 'HTTP/JSON',
  },
  {
    id: 'zero-deps',
    icon: '📦',
    title: 'Zero Dependencies to Start',
    text: 'Core install has no required dependencies — no numpy, no torch, no Docker. pip install ragforge gives you parsing, chunking, and the CLI instantly.',
    stat: '0 required deps',
  },
  {
    id: 'tables-intact',
    icon: '🧩',
    title: 'Tables & Code Stay Intact',
    text: 'The structure-aware chunker splits on section boundaries, never inside a fenced code block or table. Each chunk is tagged with its section heading.',
    stat: 'Structure-aware',
  },
  {
    id: 'coordination',
    icon: '💰',
    title: 'Cheaper Multi-Agent Coordination',
    text: 'Agents share state via a blackboard instead of messaging each other directly — cutting repeated context-passing. Savings grow with the number of agents and shared context size.',
    stat: '~10% on 3-agent demo',
  },
  {
    id: 'evaluation',
    icon: '📊',
    title: 'Prove Changes Help (Don\'t Guess)',
    text: 'Built-in evaluation with A/B comparison. Measure hit_rate, MRR, precision@k, recall@k, faithfulness, and answer_relevance on your own golden dataset.',
    stat: '6 metrics built in',
  },
  {
    id: 'grounded',
    icon: '🛡️',
    title: 'Grounded Answers, Not Hallucinations',
    text: 'The generation prompt instructs the LLM to answer only from retrieved chunks, cite which chunks it used, and explicitly refuse if evidence is insufficient.',
    stat: 'Source citations',
  },
  {
    id: 'model-swap',
    icon: '🔄',
    title: 'Safer Model Swaps',
    text: 'When upgrading embedding models, RAGForge re-embeds into a shadow index, runs evaluation to compare quality, then swaps if acceptable. Old index kept as backup.',
    stat: 'Shadow-index + validate',
  },
  {
    id: 'migration-scale',
    icon: '🏗️',
    title: 'Migration Without Re-embedding Blind',
    text: 'Instead of re-embedding your entire knowledge base and hoping quality holds, the migration module validates before cutting over — and auto-aborts if quality drops below threshold.',
    stat: 'Validate before swap',
  },
  {
    id: 'context-chunking',
    icon: '🧠',
    title: 'Chunk After Understanding Context',
    text: 'Structure-aware chunking parses the document structure first — headers, sections, code fences, tables — then splits at natural boundaries. Not blind character counting.',
    stat: 'Context-aware splits',
  },
  {
    id: 'one-tool',
    icon: '⚡',
    title: 'One Tool, Not Six',
    text: 'Parsing, chunking, retrieval, evaluation, quantization, migration, coordination, tracing — all in one pip install with a unified CLI and HTTP API.',
    stat: '9 modules',
  },
];

function SellingPoints() {
  return (
    <section className="rf-selling">
      <div className="container">
        <div className="rf-explorer__header">
          <div className="rf-explorer__label">Why RAGForge</div>
          <h2 className="rf-explorer__title">Built for the pains developers actually have</h2>
        </div>
        <div className="rf-selling__grid">
          {sellingPoints.map((sp, i) => {
            const FlowComponent = flowMap[sp.id];
            return (
              <div key={i} className="rf-selling__card">
                <div className="rf-selling__header">
                  <div className="rf-selling__icon">{sp.icon}</div>
                  <div className="rf-selling__content">
                    <div className="rf-selling__title">{sp.title}</div>
                    <div className="rf-selling__text">{sp.text}</div>
                    <div className="rf-selling__stat">{sp.stat}</div>
                  </div>
                </div>
                {FlowComponent && <FlowComponent />}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── Feature Explorer ─────────────────────────────────────────────────────────

function FeatureExplorer() {
  const [activeId, setActiveId] = useState(featureDemos[0].id);
  const active = featureDemos.find(f => f.id === activeId) || featureDemos[0];
  const [variantIdx, setVariantIdx] = useState(0);

  const handleSelect = (id: string) => {
    setActiveId(id);
    setVariantIdx(0);
  };

  return (
    <section className="rf-explorer">
      <div className="rf-explorer__header">
        <div className="rf-explorer__label">Explore the features</div>
        <h2 className="rf-explorer__title">See it in action</h2>
      </div>
      <div className="rf-explorer__layout">
        <nav className="rf-feature-list" aria-label="Feature list">
          {featureDemos.map(f => {
            const IconComp = iconComponents[f.icon];
            return (
              <button
                key={f.id}
                className={`rf-feature-item ${activeId === f.id ? 'rf-feature-item--active' : ''}`}
                onClick={() => handleSelect(f.id)}
                aria-pressed={activeId === f.id}
              >
                <span
                  className="rf-feature-item__icon"
                  style={{background: `${f.color}12`}}
                >
                  {IconComp ? <IconComp size={16} color={f.color} /> : f.icon}
                </span>
                {f.name}
              </button>
            );
          })}
        </nav>

        <DemoPanel feature={active} variantIdx={variantIdx} setVariantIdx={setVariantIdx} />
      </div>
    </section>
  );
}

function DemoPanel({feature, variantIdx, setVariantIdx}: {
  feature: FeatureDemo;
  variantIdx: number;
  setVariantIdx: (i: number) => void;
}) {
  const variant = feature.variants[variantIdx] || feature.variants[0];
  const FlowComponent = featureFlowMap[feature.id];

  return (
    <div className="rf-demo-panel">
      <p className="rf-demo-panel__desc">{feature.description}</p>

      {/* Animated flow diagram */}
      {FlowComponent && <FlowComponent />}

      {feature.input && (
        <div className="rf-demo-panel__section">
          <div className="rf-demo-panel__section-label">Input</div>
          <div className="rf-demo-panel__input">{feature.input}</div>
        </div>
      )}

      {feature.variants.length > 1 && (
        <div className="rf-demo-toggle">
          {feature.variants.map((v, i) => (
            <button
              key={i}
              className={`rf-demo-toggle__btn ${i === variantIdx ? 'rf-demo-toggle__btn--active' : ''}`}
              onClick={() => setVariantIdx(i)}
            >
              {v.label}
            </button>
          ))}
        </div>
      )}

      <div className="rf-demo-panel__section">
        <div className="rf-demo-panel__section-label">Output</div>
        <DemoOutput variant={variant} />
      </div>

      <Link className="rf-demo-panel__link" to={feature.docsLink}>
        See full docs →
      </Link>
    </div>
  );
}

function DemoOutput({variant}: {variant: any}) {
  if (variant.outputType === 'code' || variant.outputType === 'comparison') {
    return <div className="rf-demo-panel__output">{variant.output as string}</div>;
  }

  if (variant.outputType === 'metrics') {
    const metrics = variant.output as MetricData[];
    return (
      <div>
        {metrics.map((m, i) => (
          <div key={i} className="rf-metric-bar">
            <span className="rf-metric-bar__label">{m.label}</span>
            <div className="rf-metric-bar__track">
              <div
                className="rf-metric-bar__fill"
                style={{width: `${m.value * 100}%`, background: m.color}}
              />
            </div>
            <span className="rf-metric-bar__value">{(m.value * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    );
  }

  if (variant.outputType === 'chunks') {
    const chunks = variant.output as ChunkResult[];
    return (
      <div>
        {chunks.map((c, i) => (
          <div key={i} className="rf-result-chunk">
            <div className="rf-result-chunk__score">score: {c.score.toFixed(2)}{c.section && ` · ${c.section}`}</div>
            <div className="rf-result-chunk__text">{c.text}</div>
          </div>
        ))}
      </div>
    );
  }

  if (variant.outputType === 'timeline') {
    const steps = variant.output as TimelineStep[];
    return (
      <div>
        {steps.map((s, i) => (
          <div key={i} className="rf-result-chunk">
            <div className="rf-result-chunk__score">{s.agent}{s.tokens ? ` · ${s.tokens} tokens` : ''}</div>
            <div className="rf-result-chunk__text">{s.action}</div>
          </div>
        ))}
      </div>
    );
  }

  return <div className="rf-demo-panel__output">{String(variant.output)}</div>;
}

// ─── Architecture Visual ──────────────────────────────────────────────────────

function Architecture() {
  return (
    <section className="rf-architecture">
      <div className="container">
        <div className="rf-explorer__header">
          <div className="rf-explorer__label">How it works</div>
          <h2 className="rf-explorer__title">Architecture</h2>
        </div>
        <div className="rf-arch__flow">
          {/* Visual pipeline flow */}
          <div className="rf-arch__row">
            <div className="rf-arch__node rf-arch__node--source">
              <div className="rf-arch__node-icon">📄</div>
              <div className="rf-arch__node-label">Source Files</div>
              <div className="rf-arch__node-sub">PDF, MD, HTML, DOCX</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--parse">
              <div className="rf-arch__node-icon">⚡</div>
              <div className="rf-arch__node-label">Parsing</div>
              <div className="rf-arch__node-sub">Clean text extraction</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--chunk">
              <div className="rf-arch__node-icon">🧩</div>
              <div className="rf-arch__node-label">Chunking</div>
              <div className="rf-arch__node-sub">Structure-aware splits</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--embed">
              <div className="rf-arch__node-icon">🔍</div>
              <div className="rf-arch__node-label">Embed + Store</div>
              <div className="rf-arch__node-sub">Vectors + BM25 index</div>
            </div>
          </div>

          <div className="rf-arch__divider">
            <span className="rf-arch__divider-text">Query Time</span>
          </div>

          <div className="rf-arch__row">
            <div className="rf-arch__node rf-arch__node--query">
              <div className="rf-arch__node-icon">❓</div>
              <div className="rf-arch__node-label">Question</div>
              <div className="rf-arch__node-sub">From any language</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--search">
              <div className="rf-arch__node-icon">🔎</div>
              <div className="rf-arch__node-label">Hybrid Search</div>
              <div className="rf-arch__node-sub">Dense + BM25 + RRF</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--rerank">
              <div className="rf-arch__node-icon">🎯</div>
              <div className="rf-arch__node-label">Rerank</div>
              <div className="rf-arch__node-sub">Cross-encoder precision</div>
            </div>
            <div className="rf-arch__arrow">→</div>
            <div className="rf-arch__node rf-arch__node--answer">
              <div className="rf-arch__node-icon">💬</div>
              <div className="rf-arch__node-label">Answer</div>
              <div className="rf-arch__node-sub">Grounded + cited</div>
            </div>
          </div>

          {/* Bottom: supporting modules */}
          <div className="rf-arch__support">
            <div className="rf-arch__support-item">
              <span>📊</span> Evaluation
            </div>
            <div className="rf-arch__support-item">
              <span>📦</span> Quantization
            </div>
            <div className="rf-arch__support-item">
              <span>🔄</span> Migration
            </div>
            <div className="rf-arch__support-item">
              <span>🤖</span> Coordination
            </div>
            <div className="rf-arch__support-item">
              <span>👁️</span> Tracing
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Vid2 Section (between architecture and any-language) ────────────────────

function Vid2Section() {
  return (
    <section className="rf-vid2-section">
      <div className="rf-vid2-section__video-wrap">
        <video
          className="rf-vid2-section__video"
          autoPlay
          loop
          muted
          playsInline
          src="/videos/Vid2.mp4"
        />
        <div className="rf-vid2-section__overlay" />
      </div>
      <div className="rf-vid2-section__content">
        <h2 className="rf-vid2-section__title">Forge your RAG pipeline</h2>
        <p className="rf-vid2-section__text">
          From raw documents to grounded answers — every step observable, measurable, and controllable. One tool, one API, any language.
        </p>
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
    "generate": True, "llm": "ollama",
})
print(resp.json()["answer"])`;

  const js = `const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "How do refunds work?",
    generate: true, llm: "ollama",
  }),
});
const { answer, chunks } = await resp.json();`;

  const curl = `curl -s -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"knowledge":"my-kb","question":"How do refunds work?","generate":true,"llm":"ollama"}' \\
  | jq '.answer'`;

  return (
    <section className="rf-section">
      <div className="container">
        <span className="rf-section__label">any language</span>
        <h2 className="rf-section__title">Plain HTTP. Any Client.</h2>
        <p className="rf-section__subtitle">
          Python, JavaScript, Go, Rust, curl — anything with an HTTP client connects to the same API.
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

// ─── What's Inside ────────────────────────────────────────────────────────────

const overviewItems = [
  { title: 'Quickstart', desc: 'CLI, Python library, and API — up and running in 5 minutes.', link: '/docs/getting-started/quickstart' },
  { title: 'Architecture', desc: 'How modules connect via the plugin registry.', link: '/docs/core-concepts/architecture' },
  { title: 'Pipeline & Answers', desc: 'Embed, retrieve, rerank, generate grounded answers.', link: '/docs/guides/pipeline' },
  { title: 'Evaluation', desc: 'Concrete metrics. A/B compare. Prove changes help.', link: '/docs/guides/evaluation' },
  { title: 'Multi-Agent Coordination', desc: 'Blackboard-based agents. Cheaper than direct messaging.', link: '/docs/guides/coordination' },
  { title: 'HTTP API Reference', desc: 'Every endpoint with request/response examples.', link: '/docs/reference/http-api' },
];

function WhatsInside() {
  return (
    <section className="rf-overview">
      <div className="container">
        <div className="rf-explorer__header">
          <div className="rf-explorer__label">Documentation</div>
          <h2 className="rf-explorer__title">What's inside</h2>
        </div>
        <div className="rf-overview__grid">
          {overviewItems.map((item, i) => (
            <Link key={i} className="rf-overview__card" to={item.link}>
              <div className="rf-overview__card-title">{item.title}</div>
              <div className="rf-overview__card-desc">{item.desc}</div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home(): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();

  return (
    <Layout title="RAGForge" description={siteConfig.tagline}>
      <main>
        <Hero />
        <SellingPoints />
        <FeatureExplorer />
        <Architecture />
        <Vid2Section />
        <AnyLanguage />
        <WhatsInside />
      </main>
    </Layout>
  );
}
