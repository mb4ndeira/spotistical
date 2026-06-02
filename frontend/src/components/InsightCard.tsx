import type { InsightSignal } from "../types"

const LABELS: Record<number, string> = { 1: "T1 · Entity", 2: "T2 · Thematic", 3: "T3 · Macro" }
const COLORS: Record<number, string> = { 1: "var(--t1)", 2: "var(--t2)", 3: "var(--t3)" }

export function InsightCard({ signal }: { signal: InsightSignal }) {
  return (
    <div className={`insight-card insight-card-t${signal.tier}`}>
      <div className="insight-top">
        <span className="insight-tier-label" style={{ color: COLORS[signal.tier] }}>
          {LABELS[signal.tier]} · {signal.label}
        </span>
        <div className="insight-score-wrap">
          <div className="score-bar">
            <div className="score-fill" style={{ width: `${signal.score * 100}%`, background: COLORS[signal.tier] }} />
          </div>
          {signal.score.toFixed(2)}
        </div>
      </div>
      <p className="insight-desc">{signal.description}</p>
      {signal.contradiction && (
        <p className="insight-contradiction">{signal.contradiction}</p>
      )}
    </div>
  )
}
