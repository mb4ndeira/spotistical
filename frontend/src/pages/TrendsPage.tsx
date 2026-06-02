/** Trends page — stub previewing Granger causality / signal time-series */

const TIER_HEX = { 1: "#1db954", 2: "#57e38a", 3: "#0a7a38" }
const W = 560
const H = 160

/* Generate a deterministic wavy line for each tier */
function makePath(seed: number, amplitude: number, phase: number, base: number): string {
  const points: string[] = []
  for (let x = 0; x <= W; x += 6) {
    const t = x / W
    const y = base
      - Math.sin(t * Math.PI * 3.5 + phase) * amplitude
      - Math.sin(t * Math.PI * 1.2 + seed) * (amplitude * 0.4)
    points.push(`${x},${y.toFixed(1)}`)
  }
  return "M " + points.join(" L ")
}

const LINES = [
  { tier: 1 as const, label: "T1 · Entity signals",  path: makePath(0.3, 32, 0.0, 110), spikes: [0.21, 0.54, 0.77] },
  { tier: 2 as const, label: "T2 · Thematic signals", path: makePath(1.1, 22, 1.4,  80), spikes: [0.35, 0.68] },
  { tier: 3 as const, label: "T3 · Macro signals",    path: makePath(2.7, 14, 2.8,  50), spikes: [0.48] },
]

const STAT_CARDS = [
  { label: "Avg lag",          value: "3.2 days",  sub: "between news event and chart movement", tier: 1 as const },
  { label: "Strongest signal", value: "T1",        sub: "entity signals lead chart changes most consistently", tier: 1 as const },
  { label: "Granger p-value",  value: "< 0.05",   sub: "causal link confirmed for 61% of T1 events", tier: 2 as const },
  { label: "Contradiction rate", value: "18%",    sub: "of songs show audio / lyric signal tension", tier: 3 as const },
]

export function TrendsPage() {
  return (
    <div className="content-section">

      {/* Page header */}
      <div className="content-header">
        <h1 className="content-country">Signal Trends</h1>
        <p className="content-meta">
          Granger causality · lagged correlations · emotion circumplex over time
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2.5rem" }}>
        {STAT_CARDS.map((s, i) => (
          <div key={i} style={{
            background: "var(--s1)",
            border: "1px solid var(--border2)",
            borderRadius: "var(--r)",
            padding: "1.25rem",
            opacity: 0.6,
          }}>
            <p style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text3)", marginBottom: "0.5rem" }}>
              {s.label}
            </p>
            <p style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em", color: TIER_HEX[s.tier], lineHeight: 1, marginBottom: "0.4rem" }}>
              {s.value}
            </p>
            <p style={{ fontSize: "0.78rem", color: "var(--text2)", lineHeight: 1.5 }}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Time-series chart */}
      <div style={{ background: "var(--s1)", borderRadius: "var(--r-lg)", border: "1px solid var(--border2)", overflow: "hidden" }}>
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border2)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <p className="section-label" style={{ marginBottom: 0 }}>Signal intensity over time — Brazil 2024</p>
          <div style={{ display: "flex", gap: "1.25rem" }}>
            {LINES.map(l => (
              <div key={l.tier} style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem", color: "var(--text3)", fontWeight: 500 }}>
                <div style={{ width: 20, height: 2, background: TIER_HEX[l.tier], borderRadius: 1 }} />
                {l.label}
              </div>
            ))}
          </div>
        </div>

        <div style={{ padding: "1.5rem", position: "relative" }}>
          <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block", overflow: "visible" }}>
            {/* Grid lines */}
            {[0.25, 0.5, 0.75].map(v => (
              <line key={v} x1={0} y1={v * H} x2={W} y2={v * H}
                stroke="var(--border2)" strokeWidth={1} />
            ))}

            {/* Month labels */}
            {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map((m, i) => (
              <text key={m} x={(i / 11) * W} y={H + 18}
                fontSize={9} fill="var(--text3)" textAnchor="middle"
                fontFamily="DM Sans, sans-serif" fontWeight={600}>
                {m}
              </text>
            ))}

            {/* Spike markers */}
            {LINES.flatMap(l =>
              l.spikes.map((x, i) => (
                <line key={`${l.tier}-${i}`}
                  x1={x * W} y1={0} x2={x * W} y2={H}
                  stroke={TIER_HEX[l.tier]} strokeWidth={1} strokeDasharray="3 3" opacity={0.35}
                />
              ))
            )}

            {/* Signal lines */}
            {LINES.map(l => (
              <path key={l.tier} d={l.path}
                fill="none"
                stroke={TIER_HEX[l.tier]}
                strokeWidth={1.5}
                strokeLinejoin="round"
                strokeLinecap="round"
                opacity={0.8}
              />
            ))}
          </svg>

          {/* Coming-soon overlay */}
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            background: "rgba(10,10,10,0.72)",
            backdropFilter: "blur(2px)",
            borderRadius: "0 0 var(--r-lg) var(--r-lg)",
          }}>
            <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text3)", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: "0.5rem" }}>
              Tasks 6 – 7
            </p>
            <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: "0.4rem" }}>
              Granger causality + emotion circumplex
            </p>
            <p style={{ fontSize: "0.82rem", color: "var(--text2)", textAlign: "center", maxWidth: 300, lineHeight: 1.5 }}>
              Lagged correlations between news signals and chart movement, plus Russell's valence × arousal mapping. Preview above is illustrative.
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
