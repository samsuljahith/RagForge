import { useState } from 'react'
import { api } from '../api'

export default function Evaluate() {
  const [knowledge, setKnowledge] = useState('')
  const [goldenText, setGoldenText] = useState('[\n  {"question": "What is the refund window?", "expected_answer": "30 days"}\n]')
  const [metrics, setMetrics] = useState('hit_rate,precision_at_k,recall_at_k,mrr')
  const [topK, setTopK] = useState(5)
  const [mode, setMode] = useState('hybrid')
  const [result, setResult] = useState<any>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  // Compare state
  const [knowledgeB, setKnowledgeB] = useState('')
  const [comparison, setComparison] = useState<any>(null)

  const runEval = async () => {
    setRunning(true); setError(''); setResult(null)
    try {
      const golden = JSON.parse(goldenText)
      const res = await api.eval.run({
        knowledge,
        golden_dataset: golden,
        metrics: metrics.split(',').map(m => m.trim()),
        top_k: topK,
        mode,
      })
      setResult(res)
    } catch (e: any) { setError(e.message) }
    setRunning(false)
  }

  const runCompare = async () => {
    setRunning(true); setError(''); setComparison(null)
    try {
      const golden = JSON.parse(goldenText)
      const res = await api.eval.compare({
        knowledge_a: knowledge,
        knowledge_b: knowledgeB,
        golden_dataset: golden,
        metrics: metrics.split(',').map(m => m.trim()),
        top_k: topK,
        mode,
      })
      setComparison(res)
    } catch (e: any) { setError(e.message) }
    setRunning(false)
  }

  return (
    <div>
      <h1 className="page-title">Evaluate</h1>
      <p className="text-sm text-muted mb-md">Run metrics against a golden dataset. A/B compare configs.</p>

      <div className="card">
        <div className="flex gap-md" style={{ flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label className="label">Knowledge Base</label>
            <input className="input" value={knowledge} onChange={e => setKnowledge(e.target.value)} placeholder="my-kb" />
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label className="label">Compare with (optional)</label>
            <input className="input" value={knowledgeB} onChange={e => setKnowledgeB(e.target.value)} placeholder="other-kb" />
          </div>
          <div style={{ flex: 0.5, minWidth: 100 }}>
            <label className="label">Top-K</label>
            <input className="input" type="number" value={topK} onChange={e => setTopK(+e.target.value)} min={1} max={50} />
          </div>
          <div style={{ flex: 0.5, minWidth: 100 }}>
            <label className="label">Mode</label>
            <select className="select" value={mode} onChange={e => setMode(e.target.value)}>
              <option value="hybrid">hybrid</option>
              <option value="dense">dense</option>
              <option value="bm25">bm25</option>
            </select>
          </div>
        </div>
        <div className="mt-md">
          <label className="label">Metrics (comma-separated)</label>
          <input className="input" value={metrics} onChange={e => setMetrics(e.target.value)} />
        </div>
        <div className="mt-md">
          <label className="label">Golden Dataset (JSON)</label>
          <textarea className="input" rows={6} value={goldenText} onChange={e => setGoldenText(e.target.value)} style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem' }} />
        </div>
        <div className="mt-md flex gap-sm">
          <button className="btn btn--primary" onClick={runEval} disabled={running || !knowledge}>
            {running ? 'Running...' : 'Run Evaluation'}
          </button>
          {knowledgeB && (
            <button className="btn" onClick={runCompare} disabled={running || !knowledge}>
              A/B Compare
            </button>
          )}
        </div>
        {error && <p className="text-sm mt-md" style={{ color: 'var(--error)' }}>{error}</p>}
      </div>

      {result && (
        <div className="card mt-md">
          <h3 className="text-sm mb-md" style={{ fontWeight: 700 }}>Results — {result.knowledge} ({result.num_questions} questions)</h3>
          {Object.entries(result.summary as Record<string, number>).map(([name, score]) => (
            <div key={name} className="metric-bar">
              <span className="metric-bar__label">{name}</span>
              <div className="metric-bar__track">
                <div className="metric-bar__fill" style={{ width: `${score * 100}%` }} />
              </div>
              <span className="metric-bar__value">{(score * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}

      {comparison && (
        <div className="card mt-md">
          <h3 className="text-sm mb-md" style={{ fontWeight: 700 }}>
            A/B: {comparison.label_a} vs {comparison.label_b} — Winner: <span style={{ color: 'var(--accent)' }}>{comparison.winner}</span>
          </h3>
          <table style={{ width: '100%', fontSize: '0.8rem', fontFamily: 'var(--mono)' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '0.3rem' }}>Metric</th>
                <th style={{ textAlign: 'right' }}>A</th>
                <th style={{ textAlign: 'right' }}>B</th>
                <th style={{ textAlign: 'right' }}>Δ</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(comparison.delta as Record<string, number>).map(([name, delta]) => (
                <tr key={name}>
                  <td style={{ padding: '0.3rem' }}>{name}</td>
                  <td style={{ textAlign: 'right' }}>{(comparison.report_a.summary[name] * 100).toFixed(1)}%</td>
                  <td style={{ textAlign: 'right' }}>{(comparison.report_b.summary[name] * 100).toFixed(1)}%</td>
                  <td style={{ textAlign: 'right', color: delta > 0 ? 'var(--success)' : delta < 0 ? 'var(--error)' : 'var(--text-muted)' }}>
                    {delta > 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
