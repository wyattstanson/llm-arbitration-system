import { useEffect, useState } from 'react'
import { api, DIM, type Dimension } from '../api'

export default function AnalyticsView({ refreshKey }: { refreshKey: number }) {
  const [stats, setStats] = useState<Record<string, any> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.analytics().then(setStats).catch((e) => setError(String(e)))
  }, [refreshKey])

  if (error) return <div className="card p-6 text-[var(--high)] text-sm font-semibold">{error}</div>
  if (!stats) return <div className="card p-6 text-[var(--muted)] text-sm">Loading...</div>
  if (!stats.total_arbitrations) {
    return (
      <div className="card p-10 text-center">
        <div className="text-4xl mb-3">📊</div>
        <h2 className="display text-xl text-[var(--ink)]">No insights yet</h2>
        <p className="text-[var(--muted)] mt-1 text-sm">Run a few checks and patterns will appear here.</p>
      </div>
    )
  }

  const issuesByCritic = stats.avg_issues_per_run_by_critic ?? {}
  const maxIssues = Math.max(1, ...Object.values(issuesByCritic).map((n) => Number(n)))

  return (
    <div className="space-y-4">
      <div>
        <h1 className="display text-3xl text-[var(--ink)]">Insights</h1>
        <p className="text-[var(--muted)] text-sm mt-1">A live look at every check you have run.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric value={stats.total_arbitrations} label="Answers checked" />
        <Metric value={`${stats.avg_overall_score}/10`} label="Average score" />
        <Metric value={`${Math.round(stats.disagreement_rate * 100)}%`} label="Had a disagreement" />
        <Metric value={`${Math.round(stats.short_circuit_rate * 100)}%`} label="Passed cleanly" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="card p-5">
          <h3 className="display text-lg text-[var(--ink)] mb-4">Who flags the most</h3>
          <div className="space-y-3.5">
            {(['accuracy', 'logic', 'completeness'] as Dimension[]).map((dim) => {
              const val = Number(issuesByCritic[dim] ?? 0)
              return (
                <div key={dim}>
                  <div className="flex justify-between text-[13px] mb-1">
                    <span className="font-bold" style={{ color: DIM[dim].color }}>{DIM[dim].label}</span>
                    <span className="text-[var(--muted)]">{val.toFixed(2)} per check</span>
                  </div>
                  <div className="h-3 rounded-full bg-[#f0eef6] overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${(val / maxIssues) * 100}%`, background: DIM[dim].color, transition: 'width .6s ease' }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="card p-5">
          <h3 className="display text-lg text-[var(--ink)] mb-4">Disagreement patterns</h3>
          <KV label="Most often overruled" value={stats.most_overruled_critic ?? 'none yet'} />
          <KV label="Disagreements per check" value={String(stats.avg_disagreements_per_run)} />
          <div className="mt-3">
            <p className="text-[13px] text-[var(--muted)] mb-2">Kinds of disagreement</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.disagreement_type_counts ?? {}).map(([k, n]) => (
                <span key={k} className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
                  {k.replace(/_/g, ' ')}: {String(n)}
                </span>
              ))}
              {Object.keys(stats.disagreement_type_counts ?? {}).length === 0 && (
                <span className="text-xs text-[var(--muted)]">none yet</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Metric({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="card p-4">
      <div className="display text-3xl text-[var(--ink)]">{value}</div>
      <div className="text-[12px] font-semibold text-[var(--muted)] mt-1">{label}</div>
    </div>
  )
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-2 border-b border-[var(--line)] text-sm">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="font-bold text-[var(--ink)]">{value}</span>
    </div>
  )
}
