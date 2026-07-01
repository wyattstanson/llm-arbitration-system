interface Props {
  score: number // 1..10
  size?: number
}

export function colorFor(score: number): string {
  if (score >= 8) return '#54c39a' // green
  if (score >= 5) return '#f0b676' // amber
  return '#ef8a8a' // soft red
}

export default function ScoreRing({ score, size = 104 }: Props) {
  const stroke = 9
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(1, score / 10))
  const color = colorFor(score)
  return (
    <div className="relative grid place-items-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} stroke="#eceaf2" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          stroke={color}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          style={{ transition: 'stroke-dashoffset .8s ease' }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="display font-bold leading-none" style={{ color, fontSize: size * 0.3 }}>
          {score}
        </div>
        <div className="text-[10px] font-bold tracking-wide text-[var(--muted)]">out of 10</div>
      </div>
    </div>
  )
}
