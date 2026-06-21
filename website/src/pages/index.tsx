/**
 * RAGForge Homepage — Bright SaaS-style with interactive feature explorer.
 *
 * Layout:
 *   1. Hero (tagline, install, buttons)
 *   2. Feature Explorer (left list + right interactive demo panel)
 *   3. "Any Language" code examples
 *   4. "What's Inside" overview grid linking to docs
 */

import React, {useState} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import CodeBlock from '@theme/CodeBlock';
import {featureDemos, FeatureDemo, MetricData, ChunkResult, TimelineStep} from '../data/featureDemos';

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="rf-hero">
      <div className="rf-hero__content">
        <h1 className="rf-hero__title rf-animate rf-animate--d1">
          Build, evaluate, and<br/>optimize <em>RAG</em>
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
        {/* Left: feature list */}
        <nav className="rf-feature-list" aria-label="Feature list">
          {featureDemos.map(f => (
            <button
              key={f.id}
              className={`rf-feature-item ${activeId === f.id ? 'rf-feature-item--active' : ''}`}
              onClick={() => handleSelect(f.id)}
              aria-pressed={activeId === f.id}
            >
              <span
                className="rf-feature-item__icon"
                style={{background: `${f.color}15`}}
              >
                {f.icon}
              </span>
              {f.name}
            </button>
          ))}
        </nav>

        {/* Right: demo panel */}
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

  return (
    <div className="rf-demo-panel">
      <p className="rf-demo-panel__desc">{feature.description}</p>

      {/* Input */}
      {feature.input && (
        <div className="rf-demo-panel__section">
          <div className="rf-demo-panel__section-label">Input</div>
          <div className="rf-demo-panel__input">{feature.input}</div>
        </div>
      )}

      {/* Config toggle */}
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

      {/* Output */}
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

// ─── Any Language ─────────────────────────────────────────────────────────────

function AnyLanguage() {
  const py = `import requests
resp = requests.post("http://localhost:8000/query", json={
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "mode": "hybrid", "top_k": 5,
    "generate": True, "llm": "ollama",
})
print(resp.json()["answer"])`;

  const js = `const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "How do refunds work?",
    mode: "hybrid", top_k: 5,
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

// ─── What's Inside (overview grid) ───────────────────────────────────────────

const overviewItems = [
  { title: 'Quickstart', desc: 'Up and running in 5 minutes — CLI, Python, and API.', link: '/docs/getting-started/quickstart' },
  { title: 'Architecture', desc: 'How modules connect. Plugin registry, shared core.', link: '/docs/core-concepts/architecture' },
  { title: 'Pipeline & Answers', desc: 'Embed, retrieve, rerank, generate grounded answers.', link: '/docs/guides/pipeline' },
  { title: 'Evaluation', desc: 'Measure retrieval quality. A/B compare configs.', link: '/docs/guides/evaluation' },
  { title: 'Multi-Agent Coordination', desc: 'Blackboard-based agents. Cheaper than direct messaging.', link: '/docs/guides/coordination' },
  { title: 'HTTP API Reference', desc: 'Every endpoint documented with request/response examples.', link: '/docs/reference/http-api' },
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
        <FeatureExplorer />
        <AnyLanguage />
        <WhatsInside />
      </main>
    </Layout>
  );
}
