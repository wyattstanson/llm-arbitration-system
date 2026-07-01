import { useEffect, useState } from 'react'
import { api, type ArbitrationDetail, type ArbitrationSummary } from '../api'
import { colorFor } from './ScoreRing'
import VerdictPanel from './VerdictPanel'

export default function HistoryView({ refreshKey, onAudit }: { refreshKey: number; onAudit: () => void }) {
  const [items, setItems] = useState<ArbitrationSummary[]>([])
  const [selected, setSelected] = useState<ArbitrationDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.list().then(setItems).catch((e) => setError(String(e)))
  }, [refreshKey])

  async function open(id: string) {
    setSelected(null)
    try { setSelected(await api.get(id)) } catch (e) { setError(String(e)) }
  }

  if (!error && items.length === 0) {
    return (
      <div className="card p-10 text-center">
        <div className="text-4xl mb-3">📂</div>
        <h2 className="display text-xl text-[var(--ink)]">Nothing here yet</h2>
        <p className="text-[var(--muted)] mt-1 text-sm">Run your first check and it will show up here.</p>
        <button onClick={onAudit} className="btn-primary text-sm mt-4">Check an answer</button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[330px_1fr] gap-4">
      <div className="space-y-2">
        <div className="text-xs font-bold uppercase tracking-wide text-[var(--muted)] px-1">
          {items.length} past {items.length === 1 ? 'check' : 'checks'}
        </div>
        {error && <p className="text-sm font-semibold text-[var(--high)] px-1">{error}</p>}
        <div className="space-y-2 max-h-[74vh] overflow-auto pr-1">
          {items.map((it) => (
            <button
              key={it.id}
              onClick={() => open(it.id)}
              className={`w-full text-left card p-3 transition ${
                selected?.id === it.id ? 'ring-2 ring-[var(--primary)]/40' : 'hover:-translate-y-0.5'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="display font-bold text-lg" style={{ color: colorFor(it.overall_score) }}>
                  {it.overall_score}<span className="text-xs text-[var(--muted)]">/10</span>
                </span>
                <span className="text-[11px] text-[var(--muted)] ml-auto">{it.created_at.slice(0, 10)}</span>
              </div>
              <p className="text-[13px] text-[var(--ink)]/80 mt-1 line-clamp-2">{it.output_excerpt}</p>
              <div className="text-[11px] text-[var(--muted)] mt-1.5">
                {it.confirmed_issue_count} {it.confirmed_issue_count === 1 ? 'issue' : 'issues'} · {it.adjudicated ? 'adjudicated' : 'passed cleanly'}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        {selected ? (
          <VerdictPanel rec={selected} />
        ) : (
          <div className="card p-10 text-center text-[var(--muted)]">
            <div className="text-3xl mb-2">👈</div>
            <p className="text-sm">Pick a check on the left to see the full verdict.</p>
          </div>
        )}
      </div>
    </div>
  )
}
