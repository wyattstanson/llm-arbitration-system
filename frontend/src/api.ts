// Typed client for the FastAPI arbitration backend.
// Types mirror src/schemas/{critique,verdict}.py and src/api/schemas.py.

export const API_BASE = 'http://127.0.0.1:8000'

export type Severity = 'low' | 'medium' | 'high'
export type Dimension = 'accuracy' | 'logic' | 'completeness'

export interface Issue {
  quote: string
  problem: string
  severity: Severity
}

export interface CritiqueReport {
  dimension: Dimension
  score: number
  issues: Issue[]
  confidence: number
  critic_model: string
}

export interface Disagreement {
  type: 'presence_mismatch' | 'severity_gap' | 'unique_find'
  description: string
  critics_involved: string[]
  details: string
}

export interface ConfirmedIssue {
  description: string
  severity: Severity
  evidence: string
  source_critics: string[]
}

export interface DismissedFlag {
  description: string
  raised_by: string
  reasoning: string
}

export interface Verdict {
  overall_score: number
  confidence: number
  confirmed_issues: ConfirmedIssue[]
  dismissed_flags: DismissedFlag[]
  summary: string
  critic_reports: CritiqueReport[]
  disagreements: Disagreement[]
  adjudicated: boolean
}

export interface ArbitrationDetail {
  id: string
  created_at: string
  original_prompt: string | null
  llm_output: string
  verdict: Verdict
}

export interface ArbitrationSummary {
  id: string
  created_at: string
  overall_score: number
  confidence: number
  adjudicated: boolean
  output_excerpt: string
  confirmed_issue_count: number
  disagreement_count: number
}

export interface Health {
  status: string
  providers: Record<string, string>
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}. ${text.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => http<Health>('/health'),
  arbitrate: (llm_output: string, original_prompt: string | null) =>
    http<{ id: string; verdict: Verdict; created_at: string }>('/v1/arbitrate', {
      method: 'POST',
      body: JSON.stringify({ llm_output, original_prompt }),
    }),
  list: () => http<ArbitrationSummary[]>('/v1/arbitrations'),
  get: (id: string) => http<ArbitrationDetail>(`/v1/arbitrations/${id}`),
  analytics: () => http<Record<string, any>>('/v1/analytics'),
}

export const SEV_BG: Record<Severity, string> = {
  high: '#f4a8a8',
  medium: '#f1c894',
  low: '#ecd98a',
}

export const DIM: Record<Dimension, { label: string; color: string; hint: string }> = {
  accuracy: { label: 'Accuracy', color: '#5e9df0', hint: 'Are the facts correct?' },
  logic: { label: 'Logic', color: '#9b87f5', hint: 'Does the reasoning hold up?' },
  completeness: { label: 'Completeness', color: '#54c39a', hint: 'Did it answer everything?' },
}
