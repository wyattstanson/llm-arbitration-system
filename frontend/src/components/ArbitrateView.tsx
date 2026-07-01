import { useState } from 'react'
import { api, type ArbitrationDetail } from '../api'
import VerdictPanel from './VerdictPanel'

const EXAMPLES: { name: string; emoji: string; prompt: string; output: string }[] = [
  {
    name: 'A wrong fact',
    emoji: '🪐',
    prompt: 'Give me a quick factual briefing on the planet Mars for a school report.',
    output:
      'Mars is the fourth planet from the Sun and is often called the Red Planet because of its blue iron-oxide surface. It has three moons: Phobos, Deimos, and Triton. Mars is larger than Earth, with a thick, oxygen-rich atmosphere that humans could breathe unaided. A day on Mars lasts exactly 10 hours, and the planet has no seasons because its axis is not tilted.',
  },
  {
    name: 'Shaky reasoning',
    emoji: '🧩',
    prompt: 'Should our startup switch from monthly to annual billing? Walk me through the reasoning.',
    output:
      'Yes, switch to annual billing immediately. Our biggest competitor uses annual billing and they are profitable, so annual billing causes profitability. Since churn happens monthly, and annual plans only renew once a year, annual billing mathematically eliminates 11 out of every 12 churn events, guaranteeing an 11x improvement in retention.',
  },
  {
    name: 'Misses the point',
    emoji: '🎯',
    prompt: 'Compare two laptops for 4K video editing under $1500: which is better for 4K, how much RAM each has, and which has a better warranty.',
    output:
      'Both laptops are great for everyday use. The first has a sleek aluminum design in three colors, while the second has a slightly larger screen that is great for movies. Both have comfortable keyboards and good battery life for browsing. You really cannot go wrong with either for general productivity.',
  },
  {
    name: 'A good answer',
    emoji: '✅',
    prompt: 'In two or three sentences, explain why ice floats on water.',
    output:
      'Ice floats because water is unusual: when it freezes, its molecules arrange into a crystal lattice that holds them slightly farther apart than in liquid water. This makes ice about 9% less dense than the liquid, so it floats. That same expansion is why water pipes can burst in winter.',
  },
]

const STEPS = [
  { n: 1, title: 'Paste an answer', body: 'Drop in any AI generated answer. Add the original question if you have it.' },
  { n: 2, title: 'Three critics review it', body: 'Accuracy, logic, and completeness each get checked by a different model.' },
  { n: 3, title: 'Get one clear verdict', body: 'An adjudicator weighs them up and explains its decision with evidence.' },
]

export default function ArbitrateView({ onStored }: { onStored: () => void }) {
  const [prompt, setPrompt] = useState('')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ArbitrationDetail | null>(null)

  async function run() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.arbitrate(output, prompt || null)
      setResult({ id: res.id, created_at: res.created_at, original_prompt: prompt || null, llm_output: output, verdict: res.verdict })
      onStored()
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-7">
      {/* hero */}
      <div className="text-center pt-2">
        <span className="chip">AI that checks AI</span>
        <h1 className="display text-4xl sm:text-5xl text-[var(--ink)] mt-3 leading-tight">
          Let's check that answer.
        </h1>
        <p className="text-[var(--muted)] max-w-xl mx-auto mt-3 text-[15px] leading-relaxed">
          Paste any AI generated answer below. Three independent critics review it, then one adjudicator
          gives you a single, clear verdict you can trust.
        </p>
      </div>

      {/* how it works */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {STEPS.map((s) => (
          <div key={s.n} className="card p-4 flex gap-3 items-start">
            <span className="step-num shrink-0">{s.n}</span>
            <div>
              <div className="font-bold text-[var(--ink)] text-sm">{s.title}</div>
              <p className="text-[13px] text-[var(--muted)] leading-snug mt-0.5">{s.body}</p>
            </div>
          </div>
        ))}
      </div>

      {/* input */}
      <div className="card p-5 sm:p-6 space-y-4">
        <div>
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <label className="font-bold text-[var(--ink)] text-sm">New here? Try an example</label>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.name}
                onClick={() => { setPrompt(ex.prompt); setOutput(ex.output); setResult(null) }}
                className="text-sm font-semibold rounded-full px-3 py-1.5 border border-[var(--line)] bg-white hover:border-[var(--primary)] hover:text-[var(--primary)] transition"
              >
                <span className="mr-1">{ex.emoji}</span>{ex.name}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--muted)] uppercase tracking-wide">The question (optional)</label>
          <input className="input" placeholder="What was the AI asked to do?" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--muted)] uppercase tracking-wide">The answer to check</label>
          <textarea className="input h-44 resize-y" placeholder="Paste the AI generated answer here..." value={output} onChange={(e) => setOutput(e.target.value)} />
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={run} disabled={loading || !output.trim()} className="btn-primary text-sm">
            {loading ? 'Reviewing...' : 'Check this answer'}
          </button>
          {!output.trim() && !loading && (
            <span className="text-sm text-[var(--muted)]">Paste an answer, or pick an example above to begin.</span>
          )}
          {loading && (
            <span className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <span className="live-dot h-2 w-2 rounded-full bg-[var(--primary)]" />
              Three critics are reviewing, then the adjudicator decides.
            </span>
          )}
        </div>
        {error && <p className="text-sm font-semibold text-[var(--high)]">Something went wrong: {error}</p>}
      </div>

      {result && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">✨</span>
            <h2 className="display text-2xl text-[var(--ink)]">Here is your verdict</h2>
          </div>
          <VerdictPanel rec={result} />
        </div>
      )}
    </div>
  )
}
