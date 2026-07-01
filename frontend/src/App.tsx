import { useEffect, useState } from 'react'
import { api, type Health } from './api'
import ArbitrateView from './components/ArbitrateView'
import HistoryView from './components/HistoryView'
import AnalyticsView from './components/AnalyticsView'

type Tab = 'audit' | 'history' | 'insights'

const TABS: [Tab, string][] = [
  ['audit', 'Audit'],
  ['history', 'History'],
  ['insights', 'Insights'],
]

const MARQUEE = ['accuracy', 'logic', 'completeness', 'evidence', 'verdict', 'second opinion', 'audit', 'no blind spots']

export default function App() {
  const [tab, setTab] = useState<Tab>('audit')
  const [health, setHealth] = useState<Health | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setApiDown(true))
  }, [refreshKey])

  return (
    <div className="page-bg min-h-screen">
      <header className="sticky top-0 z-20 backdrop-blur bg-[#f6f5f1]/85 border-b border-[var(--line)]">
        <div className="max-w-5xl mx-auto px-5 py-3 flex items-center gap-4">
          <button onClick={() => setTab('audit')} className="flex items-center gap-2.5">
            <span className="h-9 w-9 rounded-2xl grid place-items-center text-lg"
              style={{ background: 'linear-gradient(135deg,#efedfb,#e7f0fd)', color: 'var(--primary)' }}>
              ⚖
            </span>
            <span className="display text-xl text-[var(--ink)]">Arbiter</span>
          </button>

          <nav className="ml-4 flex items-center gap-1">
            {TABS.map(([id, label]) => (
              <button key={id} onClick={() => setTab(id)} className={`btn-ghost text-sm ${tab === id ? 'active' : ''}`}>
                {label}
              </button>
            ))}
          </nav>

          <div className="ml-auto">
            {apiDown ? (
              <span className="text-xs font-bold text-[var(--high)]">API offline. Start the server on port 8000.</span>
            ) : (
              health && (
                <span className="flex items-center gap-1.5 text-xs font-bold text-[var(--green)]">
                  <span className="live-dot h-2 w-2 rounded-full bg-[var(--green)]" /> connected
                </span>
              )
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-5 py-7">
        {tab === 'audit' && <ArbitrateView onStored={() => setRefreshKey((k) => k + 1)} />}
        {tab === 'history' && <HistoryView refreshKey={refreshKey} onAudit={() => setTab('audit')} />}
        {tab === 'insights' && <AnalyticsView refreshKey={refreshKey} />}
      </main>

      <div className="marquee py-4 border-t border-[var(--line)] mt-6">
        <div className="marquee-track px-5">
          {[...MARQUEE, ...MARQUEE].map((w, i) => (
            <span key={i} className="display text-2xl text-[var(--muted)]/70 flex items-center gap-10">
              {w} <span className="text-[var(--primary)]/40">✦</span>
            </span>
          ))}
        </div>
      </div>

      <footer className="max-w-5xl mx-auto px-5 py-8 text-center text-xs text-[var(--muted)]">
        Three independent critics review every answer. An adjudicator gives you one clear verdict.
      </footer>
    </div>
  )
}
