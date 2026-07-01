import type { ReactNode } from 'react'
import { SEV_BG, type CritiqueReport } from '../api'

interface Span {
  start: number
  end: number
  color: string
  tip: string
}

// Map each critic's verbatim quote back onto the output as a colored span.
// Overlaps resolved by keeping earliest-start, then longest, so no nested wraps.
export function highlightOutput(text: string, reports: CritiqueReport[]): ReactNode[] {
  const lowered = text.toLowerCase()
  const spans: Span[] = []
  for (const r of reports || []) {
    for (const iss of r.issues) {
      const q = (iss.quote || '').toLowerCase()
      if (!q) continue
      const start = lowered.indexOf(q)
      if (start === -1) continue
      spans.push({
        start,
        end: start + q.length,
        color: SEV_BG[iss.severity],
        tip: `${r.dimension} · ${iss.severity}: ${iss.problem}`,
      })
    }
  }
  spans.sort((a, b) => a.start - b.start || b.end - b.start - (a.end - a.start))

  const chosen: Span[] = []
  let lastEnd = -1
  for (const s of spans) {
    if (s.start >= lastEnd) {
      chosen.push(s)
      lastEnd = s.end
    }
  }

  const out: ReactNode[] = []
  let cursor = 0
  chosen.forEach((s, i) => {
    if (cursor < s.start) out.push(<span key={`t${i}`}>{text.slice(cursor, s.start)}</span>)
    out.push(
      <span key={`h${i}`} className="hl" style={{ background: s.color }} title={s.tip}>
        {text.slice(s.start, s.end)}
      </span>,
    )
    cursor = s.end
  })
  if (cursor < text.length) out.push(<span key="end">{text.slice(cursor)}</span>)
  return out
}
