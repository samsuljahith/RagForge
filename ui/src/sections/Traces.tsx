import { useState, useEffect } from 'react'
import { api, TraceSummary, TraceDetail } from '../api'

export default function Traces() {
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [selected, setSelected] = useState<TraceDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.traces.list(50).then(r => { setTraces(r.traces); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const openTrace = async (runId: string) => {
    const detail = await api.traces.get(runId)
    setSelected(detail)
  }

  if (selected) {
    const maxMs = Math.max(...selected.steps.map(s => s.duration_ms), 1)
    return (
      <div>
        <button className="btn mb-md" onClick={() => setSelected(null)}>← Back to list</button>
        <h2 className="page-title">Trace: {selected.run_id}</h2>
        <div className="card">
          <div className="text-sm text-muted mb-md">
            Query: <strong>{selected.query}</strong> &nbsp;|&nbsp;
            KB: {selected.knowledge} &nbsp;|&nbsp;
            Total: <strong>{selected.total_duration_ms.toFixed(1)}ms</strong> &nbsp;|&nbsp;
            Status: <span className={`badge badge--${selected.status === 'completed' ? 'success' : 'error'}`}>{selected.status}</span>
          </div>
          <div className="timeline">
            {selected.steps.map((step, i) => (
              <div key={i} className="timeline-step">
                <span className="timeline-step__name">{step.name}</span>
                <div className="timeline-step__bar">
                  <div className="timeline-step__bar-fill" style={{ width: `${(step.duration_ms / maxMs) * 100}%` }} />
                </div>
                <span className="timeline-step__ms">{step.duration_ms.toFixed(1)}ms</span>
              </div>
            ))}
          </div>
        </div>
        {selected.steps.map((step, i) => (
          step.data && Object.keys(step.data).length > 0 && (
            <details key={i} className="card">
              <summary className="text-sm" style={{ cursor: 'pointer' }}>
                <strong>{step.name}</strong> — data
              </summary>
              <pre className="text-sm mono mt-md" style={{ whiteSpace: 'pre-wrap', color: 'var(--text-muted)' }}>
                {JSON.stringify(step.data, null, 2)}
              </pre>
            </details>
          )
        ))}
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Traces</h1>
      <p className="text-sm text-muted mb-md">Pipeline execution traces — see exactly what each query did.</p>
      {loading ? <p className="text-muted">Loading...</p> : traces.length === 0 ? (
        <div className="card">
          <p className="text-muted">No traces yet. Run a query (via Chat or CLI) to see traces here.</p>
        </div>
      ) : (
        traces.map(t => (
          <div key={t.run_id} className="card card--clickable" onClick={() => openTrace(t.run_id)}>
            <div className="flex gap-md" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="text-sm" style={{ fontWeight: 600 }}>{t.query || '(no query)'}</div>
                <div className="text-sm text-muted">{t.knowledge} &nbsp;·&nbsp; {new Date(t.started_at * 1000).toLocaleString()}</div>
              </div>
              <div className="flex gap-sm" style={{ alignItems: 'center' }}>
                <span className="mono text-sm">{t.total_duration_ms.toFixed(0)}ms</span>
                <span className={`badge badge--${t.status === 'completed' ? 'success' : t.status === 'error' ? 'error' : 'running'}`}>{t.status}</span>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
