import { DIM, SEV_BG, type CritiqueReport, type Dimension } from '../api'

const ORDER: Dimension[] = ['accuracy', 'logic', 'completeness']

export default function CriticColumns({ reports }: { reports: CritiqueReport[] }) {
  const byDim = new Map(reports.map((r) => [r.dimension, r]))
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {ORDER.map((dim) => {
        const r = byDim.get(dim)
        const meta = DIM[dim]
        return (
          <div key={dim} className="rounded-2xl border border-[var(--line)] bg-[#fbfbfd] p-4">
            <div className="flex items-center gap-2">
              <span className="h-7 w-7 rounded-xl grid place-items-center text-white text-xs font-bold"
                style={{ background: meta.color }}>
                {meta.label[0]}
              </span>
              <div className="leading-tight">
                <div className="font-bold text-sm text-[var(--ink)]">{meta.label}</div>
                <div className="text-[11px] text-[var(--muted)]">{meta.hint}</div>
              </div>
              {r && (
                <span className="ml-auto display text-lg font-bold" style={{ color: meta.color }}>
                  {r.score}<span className="text-[var(--muted)] text-xs font-semibold">/5</span>
                </span>
              )}
            </div>

            {!r ? (
              <p className="mt-3 text-sm font-semibold text-[var(--high)]">This critic could not be reached, so this dimension was skipped.</p>
            ) : (
              <>
                <div className="mt-2 text-[11px] text-[var(--muted)]">
                  {r.critic_model} · {Math.round(r.confidence * 100)}% sure
                </div>
                <div className="mt-3 space-y-2.5">
                  {r.issues.length === 0 && (
                    <p className="text-sm font-semibold text-[var(--green)]">Nothing flagged here. Looks good.</p>
                  )}
                  {r.issues.map((iss, i) => (
                    <div key={i} className="text-sm">
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[var(--muted)]">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEV_BG[iss.severity] }} />
                        {iss.severity}
                      </span>
                      <p className="text-[var(--ink)] leading-snug mt-0.5">{iss.problem}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
