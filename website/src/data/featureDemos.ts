/**
 * Feature demo data for the interactive homepage explorer.
 *
 * NOTE: These are ILLUSTRATIVE example outputs — curated to show what each
 * feature does in a convincing way. The site is static and cannot call the
 * real backend. Each feature has prepared input/output variants that the
 * interactive toggles swap between.
 */

export interface FeatureDemo {
  id: string;
  name: string;
  icon: string;
  color: string;         // CSS color for the icon background
  description: string;
  docsLink: string;
  input?: string;
  variants: DemoVariant[];
}

export interface DemoVariant {
  label: string;
  output: string | MetricData[] | ChunkResult[] | TimelineStep[];
  outputType: 'code' | 'metrics' | 'chunks' | 'timeline' | 'comparison';
}

export interface MetricData {
  label: string;
  value: number;
  color: string;
}

export interface ChunkResult {
  score: number;
  text: string;
  section?: string;
}

export interface TimelineStep {
  agent: string;
  action: string;
  tokens?: number;
}

export const featureDemos: FeatureDemo[] = [
  {
    id: 'parsing',
    name: 'Parsing',
    icon: 'FileText',
    color: '#f97316',
    description: 'Turn any file into clean, structured text. Auto-detects format. Supports txt, md, html, pdf — plus Docling for complex layouts.',
    docsLink: '/docs/guides/parsing',
    input: `<html><body>
<h1>Refund Policy</h1>
<script>var x = 1;</script>
<p>Returns accepted within <b>30 days</b>.</p>
<table><tr><td>Electronics</td><td>14 days</td></tr></table>
</body></html>`,
    variants: [
      {
        label: 'Default',
        outputType: 'code',
        output: `Document(source="policy.html", doc_type="html", ~18 tokens)

Refund Policy
Returns accepted within 30 days.
Electronics  14 days`,
      },
      {
        label: 'Docling',
        outputType: 'code',
        output: `Document(source="policy.html", doc_type="html", ~22 tokens)

# Refund Policy

Returns accepted within **30 days**.

| Product     | Window  |
|-------------|---------|
| Electronics | 14 days |

metadata: {parser: "docling", has_tables: true}`,
      },
    ],
  },
  {
    id: 'chunking',
    name: 'Chunking',
    icon: 'LayoutGrid',
    color: '#10b981',
    description: 'Split documents into retrievable pieces. Structure-aware mode keeps tables and code blocks intact — never cuts them in half.',
    docsLink: '/docs/guides/chunking',
    input: `# API Reference

Our API uses REST over HTTPS.

## Rate Limits

| Tier    | Requests/min |
|---------|-------------|
| Free    | 60          |
| Pro     | 1000        |
| Enterprise | Unlimited |

## Authentication

\`\`\`python
headers = {"Authorization": f"Bearer {token}"}
\`\`\``,
    variants: [
      {
        label: 'Fixed',
        outputType: 'code',
        output: `Chunk 0: "# API Reference\\nOur API uses REST over HTTPS.\\n## Rate Limits\\n| Tier    |"
Chunk 1: "| Requests/min |\\n|---------|-------------|\\n| Free    | 60          |"
Chunk 2: "| Pro     | 1000        |\\n| Enterprise | Unlimited |\\n## Auth"
Chunk 3: "entication\\n\`\`\`python\\nheaders = {"

⚠️ Table split across chunks 0-2. Code block cut at chunk 3.`,
      },
      {
        label: 'Structure',
        outputType: 'code',
        output: `Chunk 0 [section: API Reference]
  "Our API uses REST over HTTPS."

Chunk 1 [section: Rate Limits]
  "| Tier    | Requests/min |\\n|---------|---..."
  (complete table — all 3 rows intact)

Chunk 2 [section: Authentication]
  "\`\`\`python\\nheaders = {...}\\n\`\`\`"
  (complete code block)

✓ Table intact. Code intact. Each chunk tagged with section.`,
      },
    ],
  },
  {
    id: 'retrieval',
    name: 'Retrieval',
    icon: 'Search',
    color: '#6366f1',
    description: 'Hybrid search: dense vectors + BM25 keyword matching, fused via Reciprocal Rank Fusion. Optional cross-encoder reranking for precision.',
    docsLink: '/docs/guides/pipeline',
    input: 'Query: "What are the rate limits for the Pro tier?"',
    variants: [
      {
        label: 'Dense only',
        outputType: 'chunks',
        output: [
          { score: 0.72, text: 'Our API uses REST over HTTPS with rate limiting per tier.', section: 'API Reference' },
          { score: 0.68, text: 'Pro tier includes priority support and higher quotas.', section: 'Pricing' },
          { score: 0.61, text: 'Rate limits are applied per API key.', section: 'Rate Limits' },
        ] as ChunkResult[],
      },
      {
        label: 'Hybrid + rerank',
        outputType: 'chunks',
        output: [
          { score: 0.94, text: '| Pro | 1000 requests/min | Priority support |', section: 'Rate Limits' },
          { score: 0.81, text: 'Rate limits are applied per API key, per minute.', section: 'Rate Limits' },
          { score: 0.73, text: 'Pro tier includes priority support and higher quotas.', section: 'Pricing' },
        ] as ChunkResult[],
      },
    ],
  },
  {
    id: 'generation',
    name: 'Answer Generation',
    icon: 'MessageSquare',
    color: '#8b5cf6',
    description: 'Generate grounded answers from retrieved chunks. Cites sources, refuses when evidence is insufficient. Supports OpenAI, Anthropic, and Ollama.',
    docsLink: '/docs/guides/pipeline',
    input: 'Question: "What is the rate limit for Pro users?"',
    variants: [
      {
        label: 'With sources',
        outputType: 'code',
        output: `Answer:
  Pro tier users have a rate limit of 1,000 requests per minute.
  This includes priority support. [Source: Rate Limits table]

Sources:
  [0.94] "| Pro | 1000 requests/min | Priority support |"
  [0.81] "Rate limits are applied per API key, per minute."

LLM: ollama/llama3.2 | Tokens: 142`,
      },
      {
        label: 'Insufficient evidence',
        outputType: 'code',
        output: `Answer:
  I cannot answer this question based on the available documents.
  The retrieved chunks do not contain information about Pro tier
  rate limits in the indexed knowledge base.

  (No hallucination — answer refused when evidence is lacking)

Sources: 0 relevant chunks found`,
      },
    ],
  },
  {
    id: 'evaluation',
    name: 'Evaluation',
    icon: 'BarChart3',
    color: '#06b6d4',
    description: 'Measure retrieval quality with concrete numbers. Hit rate, MRR, precision@k, plus LLM-as-judge for faithfulness. A/B compare configurations.',
    docsLink: '/docs/guides/evaluation',
    variants: [
      {
        label: 'Structure chunking',
        outputType: 'metrics',
        output: [
          { label: 'Hit Rate', value: 0.85, color: '#10b981' },
          { label: 'MRR', value: 0.73, color: '#6366f1' },
          { label: 'Precision@5', value: 0.62, color: '#f97316' },
          { label: 'Recall@5', value: 0.78, color: '#06b6d4' },
        ] as MetricData[],
      },
      {
        label: 'Fixed chunking',
        outputType: 'metrics',
        output: [
          { label: 'Hit Rate', value: 0.71, color: '#10b981' },
          { label: 'MRR', value: 0.58, color: '#6366f1' },
          { label: 'Precision@5', value: 0.44, color: '#f97316' },
          { label: 'Recall@5', value: 0.61, color: '#06b6d4' },
        ] as MetricData[],
      },
    ],
  },
  {
    id: 'quantization',
    name: 'Quantization',
    icon: 'Minimize2',
    color: '#f59e0b',
    description: 'Compress embeddings and measure the real cost/quality tradeoff on YOUR data before committing. See exactly how much quality you lose for how much cost savings.',
    docsLink: '/docs/guides/quantization',
    variants: [
      {
        label: 'float32 (baseline)',
        outputType: 'code',
        output: `Model: default (float32)
Dimension: 128
Size per vector: 512 bytes
Quality score: 1.000 (baseline)
Cost: $1.00/month per 100k vectors`,
      },
      {
        label: 'int8 (4x smaller)',
        outputType: 'code',
        output: `Model: default_quantized_8bit
Dimension: 128
Size per vector: 128 bytes  (4x compression)
Quality score: 0.982  (-1.8% vs baseline)
Cost: $0.25/month per 100k vectors

Verdict: 75% cost reduction for <2% quality loss ✓`,
      },
    ],
  },
  {
    id: 'coordination',
    name: 'Coordination',
    icon: 'Network',
    color: '#ec4899',
    description: 'Multi-agent blackboard coordination. Agents share a workspace instead of messaging each other — measurably cheaper. Includes a cost benchmark.',
    docsLink: '/docs/guides/coordination',
    variants: [
      {
        label: 'Blackboard',
        outputType: 'timeline',
        output: [
          { agent: 'Researcher', action: 'wrote "findings" (confidence: 0.85)', tokens: 203 },
          { agent: 'Critic', action: 'wrote "review" (status: approved)', tokens: 172 },
          { agent: 'Writer', action: 'wrote "final_answer"', tokens: 346 },
        ] as TimelineStep[],
      },
      {
        label: 'Cost comparison',
        outputType: 'comparison',
        output: `Direct messaging:  802 tokens  ($0.0072)
Blackboard:        721 tokens  ($0.0068)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Savings:           10.1% fewer tokens

(Savings grow with task complexity —
 10-step tasks often save 40-70%)`,
      },
    ],
  },
  {
    id: 'tracing',
    name: 'Tracing & UI',
    icon: 'Activity',
    color: '#14b8a6',
    description: 'Every query is traced: what was searched, what was found, what was sent to the LLM. Launch a local dashboard with `ragforge ui` to inspect, debug, and chat.',
    docsLink: '/docs/guides/ui',
    variants: [
      {
        label: 'Trace view',
        outputType: 'code',
        output: `Run: abc12def | "How do refunds work?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: retrieval    12ms  mode=hybrid k=5
Step 2: rerank       8ms   kept 3/5 chunks
Step 3: generation   340ms tokens=186
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 360ms | Status: completed`,
      },
      {
        label: 'Dashboard',
        outputType: 'code',
        output: `ragforge ui
  → Dashboard:  http://localhost:8000/ui
  → API docs:   http://localhost:8000/docs

Three views:
  📋 Traces   — timeline of all queries + step breakdown
  📊 Evaluate — run evals, view metric charts
  💬 Chat     — interactive RAG Q&A with source display`,
      },
    ],
  },
  {
    id: 'migration',
    name: 'Migration',
    icon: 'RefreshCw',
    color: '#0ea5e9',
    description: 'Safely swap embedding models. Re-embeds all chunks in a shadow index, validates quality with evaluation, then performs an atomic cutover.',
    docsLink: '/docs/guides/migration',
    variants: [
      {
        label: 'Migration steps',
        outputType: 'code',
        output: `migrate_knowledge_base("my-kb", from="default", to="openai")

Step 1: Load KB (23 chunks)           ✓
Step 2: Re-embed with new model       ✓  [shadow index]
Step 3: Validate quality              ✓  (0.95 vs 1.00)
Step 4: Atomic swap                   ✓
Step 5: Backup old index              ✓

Status: migrated
Quality before: 1.00 → after: 0.95 (acceptable)`,
      },
      {
        label: 'Safety features',
        outputType: 'code',
        output: `Safety guarantees:
  • Shadow indexing — old index untouched during migration
  • Quality gate — auto-aborts if quality drops too much
  • Atomic swap — either new is live or old is, never half
  • Backup kept — old vectors preserved until you delete

If validation fails:
  Status: aborted (quality below threshold)
  Old index: still active, unchanged`,
      },
    ],
  },
];
