/**
 * Shared API client for the RAGForge UI.
 * All sections use this to talk to the backend.
 */

const BASE = ''  // Same origin (served by FastAPI)

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ─── Traces ───────────────────────────────────────────────────────────────────

export interface TraceSummary {
  run_id: string
  query: string
  knowledge: string
  started_at: number
  total_duration_ms: number
  status: string
}

export interface TraceStep {
  name: string
  started_at: number
  ended_at: number
  duration_ms: number
  data: Record<string, any>
}

export interface TraceDetail extends TraceSummary {
  ended_at: number
  steps: TraceStep[]
  metadata: Record<string, any>
}

export const api = {
  traces: {
    list: (limit = 50) => request<{ traces: TraceSummary[] }>(`/traces?limit=${limit}`),
    get: (runId: string) => request<TraceDetail>(`/traces/${runId}`),
  },

  eval: {
    run: (body: any) => request<any>('/ui/eval/run', { method: 'POST', body: JSON.stringify(body) }),
    compare: (body: any) => request<any>('/ui/eval/compare', { method: 'POST', body: JSON.stringify(body) }),
    history: (knowledge?: string) =>
      request<any[]>(`/ui/eval/history${knowledge ? `?knowledge=${knowledge}` : ''}`),
  },

  chat: {
    message: (body: any) => request<any>('/ui/chat/message', { method: 'POST', body: JSON.stringify(body) }),
  },

  knowledge: {
    list: () => request<{ capabilities: Record<string, string[]> }>('/capabilities'),
  },

  health: () => request<{ status: string; version: string }>('/health'),
}
