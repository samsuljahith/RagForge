import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import CodeBlock from '@theme/CodeBlock';

import styles from './index.module.css';

function HeroSection() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started/quickstart">
            Get Started
          </Link>
          <Link
            className="button button--outline button--lg"
            href="https://github.com/ragforge/ragforge"
            style={{marginLeft: '1rem'}}>
            GitHub
          </Link>
        </div>
        <div className={styles.installCommand}>
          <code>pip install ragforge</code>
        </div>
      </div>
    </header>
  );
}

type FeatureItem = {
  title: string;
  description: string;
  available: boolean;
};

const features: FeatureItem[] = [
  {
    title: 'Parsing',
    description: 'Turn any file (txt, md, html, pdf) into clean Documents. Auto-detects format by extension.',
    available: true,
  },
  {
    title: 'Chunking',
    description: 'Structure-aware splitting that keeps tables and code blocks intact. Tags each chunk with its section.',
    available: true,
  },
  {
    title: 'Pipeline',
    description: 'Embed, store, and retrieve with hybrid search (dense + BM25) and reranking.',
    available: true,
  },
  {
    title: 'Evaluation',
    description: 'Measure precision, recall, and faithfulness against a golden dataset. Stop flying blind.',
    available: true,
  },
  {
    title: 'Quantization',
    description: 'Quantize models and compare cost vs quality tradeoff on your own data.',
    available: true,
  },
  {
    title: 'Migration',
    description: 'Safely move between embedding models with shadow indexing and quality validation.',
    available: true,
  },
];

function FeatureCards() {
  return (
    <section className={styles.features}>
      <div className="container">
        <h2 style={{textAlign: 'center', marginBottom: '2rem'}}>Capabilities</h2>
        <div className="row">
          {features.map((feature, idx) => (
            <div key={idx} className={clsx('col col--4')} style={{marginBottom: '1.5rem'}}>
              <div className="feature-card">
                <h3>
                  {feature.title}{' '}
                  <span className={feature.available ? 'badge--available' : 'badge--coming-soon'}>
                    {feature.available ? 'Available' : 'Coming soon'}
                  </span>
                </h3>
                <p>{feature.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function QuickExample() {
  const parseChunkExample = `import ragforge as rf

# Parse any file into a clean Document
doc = rf.parse_file("knowledge-base/refund-policy.md")

# Structure-aware chunking: keeps tables and code intact
chunks = rf.chunk_document(doc, strategy="structure")

for chunk in chunks:
    print(f"[{chunk.metadata.get('section')}] ~{chunk.token_count} tokens")`;

  return (
    <section className={styles.example}>
      <div className="container">
        <h2 style={{textAlign: 'center'}}>Parse + Chunk in 4 Lines</h2>
        <CodeBlock language="python">{parseChunkExample}</CodeBlock>
      </div>
    </section>
  );
}

function AnyLanguageSection() {
  const pythonExample = `import requests

resp = requests.post("http://localhost:8000/query", json={
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "top_k": 3,
})
chunks = resp.json()["chunks"]`;

  const jsExample = `const resp = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    knowledge: "my-kb",
    question: "How do refunds work?",
    top_k: 3,
  }),
});
const { chunks } = await resp.json();`;

  const curlExample = `curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "knowledge": "my-kb",
    "question": "How do refunds work?",
    "top_k": 3
  }'`;

  return (
    <section className={styles.anyLanguage}>
      <div className="container">
        <h2 style={{textAlign: 'center'}}>Works with Any Language</h2>
        <p style={{textAlign: 'center', marginBottom: '2rem', opacity: 0.8}}>
          The same HTTP/JSON API — call it from Python, JavaScript, Go, Java, C++, or anything with an HTTP client.
        </p>
        <Tabs>
          <TabItem value="python" label="Python" default>
            <CodeBlock language="python">{pythonExample}</CodeBlock>
          </TabItem>
          <TabItem value="javascript" label="JavaScript">
            <CodeBlock language="javascript">{jsExample}</CodeBlock>
          </TabItem>
          <TabItem value="curl" label="curl">
            <CodeBlock language="bash">{curlExample}</CodeBlock>
          </TabItem>
        </Tabs>
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="One workshop for building, evaluating, and optimizing RAG — usable from any language">
      <HeroSection />
      <main>
        <FeatureCards />
        <QuickExample />
        <AnyLanguageSection />
      </main>
    </Layout>
  );
}
