import { useState } from 'react'
import { api } from '../api'

interface Message {
  role: 'user' | 'assistant'
  text: string
  sources?: any[]
  runId?: string
}

export default function Chat() {
  const [knowledge, setKnowledge] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [llm, setLlm] = useState('')
  const [rerank, setRerank] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim() || !knowledge) return
    const question = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: question }])
    setLoading(true)

    try {
      const res = await api.chat.message({
        knowledge,
        question,
        top_k: 5,
        mode,
        rerank,
        generate: !!llm,
        llm: llm || null,
      })
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: res.answer || '(Retrieval only — no answer generated. Set an LLM to get answers.)',
        sources: res.sources,
        runId: res.run_id,
      }])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${e.message}` }])
    }
    setLoading(false)
  }

  return (
    <div>
      <h1 className="page-title">Chat</h1>
      
      {/* Settings bar */}
      <div className="card flex gap-md" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 150 }}>
          <label className="label">Knowledge Base</label>
          <input className="input" value={knowledge} onChange={e => setKnowledge(e.target.value)} placeholder="my-kb" />
        </div>
        <div style={{ width: 120 }}>
          <label className="label">Mode</label>
          <select className="select" value={mode} onChange={e => setMode(e.target.value)}>
            <option value="hybrid">hybrid</option>
            <option value="dense">dense</option>
            <option value="bm25">bm25</option>
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 150 }}>
          <label className="label">LLM (optional)</label>
          <input className="input" value={llm} onChange={e => setLlm(e.target.value)} placeholder="ollama / openai / anthropic" />
        </div>
        <label className="text-sm" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} /> Rerank
        </label>
      </div>

      {/* Messages */}
      <div className="chat-messages mt-md">
        {messages.length === 0 && (
          <div className="card text-muted text-sm">Ask a question about your knowledge base.</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg--${msg.role}`}>
            <div className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="chat-sources">
                <div className="text-sm" style={{ fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-muted)' }}>
                  Sources ({msg.sources.length})
                </div>
                {msg.sources.map((s: any, j: number) => (
                  <div key={j} className="chat-source">
                    [{j+1}] score={s.score.toFixed(3)} {s.section && `[${s.section}]`} — {s.text.slice(0, 100)}...
                  </div>
                ))}
              </div>
            )}
            {msg.runId && (
              <div className="text-sm mt-md">
                <a href={`/?trace=${msg.runId}`} style={{ color: 'var(--accent)', fontSize: '0.7rem' }}>
                  View trace: {msg.runId}
                </a>
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm text-muted">Thinking...</div>}
      </div>

      {/* Input */}
      <div className="flex gap-sm">
        <input
          className="input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder={knowledge ? "Ask a question..." : "Set a knowledge base first"}
          disabled={!knowledge || loading}
        />
        <button className="btn btn--primary" onClick={send} disabled={!knowledge || !input.trim() || loading}>
          Send
        </button>
      </div>
    </div>
  )
}
