import { SEV_BG, type ArbitrationDetail } from '../api'
import { highlightOutput } from '../lib/highlight'
import CriticColumns from './CriticColumns'
import ScoreRing, { colorFor } from './ScoreRing'

const DIS_LABEL: Record<string, string> = {
  presence_mismatch: 'one critic saw something the others missed',
  severity_gap: 'critics disagreed on how serious it is',
  unique_find: 'only one critic caught this',
}

function headline(score: number): string {
  if (score >= 8) return 'This answer looks solid.'
  if (score >= 5) return 'This answer is a mixed bag.'
  return 'This answer has real problems.'
}

export default function VerdictPanel({ rec }: { rec: ArbitrationDetail }) {
  const v = rec.verdict
  const color = colorFor(v.overall_score)
  return (
    <div className="space-y-4">
      {/* headline card */}
      <div className="card p-5 sm:p-6 flex flex-wrap items-center gap-6">
        <ScoreRing score={v.overall_score} />
        <div className="flex-1 min-w-[240px]">
          <h3 className="display text-2xl text-[var(--ink)]" style={{ color }}>{headline(v.overall_score)}</h3>
          <div className="flex flex-wrap gap-2 my-2.5">
            <Chip>{Math.round(v.confidence * 100)}% confident</Chip>
            <Chip>{v.confirmed_issues.length} confirmed {v.confirmed_issues.length === 1 ? 'issue' : 'issues'}</Chip>
            <Chip>{v.adjudicated ? 'Adjudicated' : 'Passed cleanly'}</Chip>
          </div>
          <p className="text-[15px] text-[var(--ink)]/80 leading-relaxed">{v.summary}</p>
        </div>
      </div>

      {/* output with markers */}
      <Section title="The answer, marked up" hint="Highlights show what a critic flagged. Hover any one to see who flagged it and why.">
        <div className="text-[15px] leading-8 text-[var(--ink)]/90">
          {highlightOutput(rec.llm_output, v.critic_reports)}
        </div>
      </Section>

      {/* confirmed + dismissed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Section title="What the adjudicator confirmed" hint={`${v.confirmed_issues.length} real ${v.confirmed_issues.length === 1 ? 'issue' : 'issues'}`}>
          {v.confirmed_issues.length === 0 && <Empty>No issues were upheld. Nice.</Empty>}
          <div className="space-y-2">
            {v.confirmed_issues.map((ci, i) => (
              <div key={i} className="rounded-xl border border-[var(--line)] bg-[#fbfbfd] p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEV_BG[ci.severity] }} />
                  <span className="text-[11px] font-bold uppercase tracking-wide text-[var(--muted)]">{ci.severity}</span>
                  <span className="ml-auto text-[11px] text-[var(--muted)]">found by {ci.source_critics.join(', ')}</span>
                </div>
                <p className="text-sm font-semibold text-[var(--ink)]">{ci.description}</p>
                <p className="text-[13px] text-[var(--muted)] mt-1">{ci.evidence}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="What it waved off" hint="Flags a critic raised that the adjudicator decided were not a real problem.">
          {v.dismissed_flags.length === 0 && <Empty>Nothing was waved off this time.</Empty>}
          <div className="space-y-2">
            {v.dismissed_flags.map((df, i) => (
              <div key={i} className="rounded-xl border border-[var(--line)] bg-[#fffaf3] p-3">
                <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--medium)] mb-1">
                  raised by {df.raised_by}, then overruled
                </div>
                <p className="text-sm font-semibold text-[var(--ink)]">{df.description}</p>
                <p className="text-[13px] text-[var(--muted)] mt-1">Why it was waved off: {df.reasoning}</p>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* critics */}
      <Section title="What each critic thought" hint="Three different models, each looking at one thing.">
        <CriticColumns reports={v.critic_reports} />
      </Section>

      {/* disagreements */}
      {v.disagreements.length > 0 && (
        <Section title="Where the critics disagreed" hint="Disagreement is the useful part. It is what a single reviewer would miss.">
          <div className="space-y-2">
            {v.disagreements.map((d, i) => (
              <div key={i} className="flex gap-3 items-start text-sm">
                <span className="text-[11px] font-bold px-2.5 py-1 rounded-full whitespace-nowrap"
                  style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
                  {DIS_LABEL[d.type] ?? d.type}
                </span>
                <p className="text-[var(--ink)]/80">{d.description}</p>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="chip">{children}</span>
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <div className="mb-3">
        <h3 className="display text-lg text-[var(--ink)]">{title}</h3>
        {hint && <p className="text-[13px] text-[var(--muted)] mt-0.5">{hint}</p>}
      </div>
      {children}
    </div>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-[var(--muted)]">{children}</p>
}
