/** Clusters page — stub that previews the audio K-Means / UMAP view */

const TIER_HEX = { 1: "#1db954", 2: "#57e38a", 3: "#0a7a38" }

/* Deterministic pseudo-random scatter — same every render */
function seededRand(seed: number) {
  let s = seed
  return () => { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646 }
}

interface DotData {
  x: number; y: number; r: number
  tier: 1 | 2 | 3; label?: string
}

function buildDots(): DotData[] {
  const rand = seededRand(42)
  const clusters: { cx: number; cy: number; tier: 1 | 2 | 3; label: string; count: number }[] = [
    { cx: 0.18, cy: 0.28, tier: 1, label: "Carnaval / festa",   count: 18 },
    { cx: 0.44, cy: 0.60, tier: 1, label: "Sertanejo nostálgico", count: 14 },
    { cx: 0.70, cy: 0.22, tier: 2, label: "Pop dançante",        count: 22 },
    { cx: 0.82, cy: 0.68, tier: 2, label: "Indie melancólico",   count: 11 },
    { cx: 0.55, cy: 0.38, tier: 3, label: "Funk carioca",        count: 16 },
    { cx: 0.30, cy: 0.72, tier: 3, label: "Balada eletrônica",   count: 9  },
  ]

  const dots: DotData[] = []
  for (const c of clusters) {
    for (let i = 0; i < c.count; i++) {
      const angle = rand() * Math.PI * 2
      const dist  = rand() * 0.1
      dots.push({
        x:     c.cx + Math.cos(angle) * dist,
        y:     c.cy + Math.sin(angle) * dist,
        r:     2.5 + rand() * 2.5,
        tier:  c.tier,
        label: i === 0 ? c.label : undefined,
      })
    }
  }
  return dots
}

const DOTS = buildDots()

const CLUSTER_CARDS = [
  { id: 1, tier: 1 as const, name: "Carnaval / festa",    features: "High energy · High danceability · Major key",   size: 18, countries: 7  },
  { id: 2, tier: 2 as const, name: "Pop dançante",         features: "High valence · Mid energy · Electronic",        size: 22, countries: 31 },
  { id: 3, tier: 3 as const, name: "Funk carioca",         features: "High speechiness · Strong beat · Low acousticness", size: 16, countries: 3 },
  { id: 4, tier: 1 as const, name: "Sertanejo nostálgico", features: "High acousticness · Mid valence · Slow tempo",   size: 14, countries: 4  },
  { id: 5, tier: 2 as const, name: "Indie melancólico",    features: "Low valence · Low energy · Minor key",           size: 11, countries: 19 },
  { id: 6, tier: 3 as const, name: "Balada eletrônica",    features: "Max energy · Low acousticness · High liveness",  size:  9, countries: 14 },
]

export function ClustersPage() {
  return (
    <div className="content-section">

      {/* Page header */}
      <div className="content-header">
        <h1 className="content-country">Audio Clusters</h1>
        <p className="content-meta">
          K-Means on 12 audio features · UMAP dimensionality reduction · 73 countries
        </p>
      </div>

      {/* Layout: scatter left, cards right */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "2.5rem", alignItems: "start" }}>

        {/* UMAP scatter */}
        <div style={{ background: "var(--s1)", borderRadius: "var(--r-lg)", overflow: "hidden", border: "1px solid var(--border2)" }}>
          <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border2)" }}>
            <p className="section-label" style={{ marginBottom: 0 }}>UMAP projection — audio feature space</p>
          </div>
          <div style={{ padding: "1.5rem", position: "relative" }}>
            <svg viewBox="0 0 400 280" width="100%" style={{ display: "block" }}>
              {/* Axis ticks — purely decorative */}
              {[0.2, 0.4, 0.6, 0.8].map(v => (
                <line key={`h${v}`} x1={0} y1={v * 280} x2={400} y2={v * 280}
                  stroke="var(--border2)" strokeWidth={1} />
              ))}
              {[0.25, 0.5, 0.75].map(v => (
                <line key={`v${v}`} x1={v * 400} y1={0} x2={v * 400} y2={280}
                  stroke="var(--border2)" strokeWidth={1} />
              ))}

              {/* Dots */}
              {DOTS.map((d, i) => (
                <circle
                  key={i}
                  cx={d.x * 400} cy={d.y * 280} r={d.r}
                  fill={TIER_HEX[d.tier]}
                  opacity={0.7}
                />
              ))}

              {/* Cluster labels */}
              {DOTS.filter(d => d.label).map((d, i) => (
                <text
                  key={i}
                  x={d.x * 400 + 8} y={d.y * 280 - 6}
                  fontSize={9} fill="var(--text3)"
                  fontFamily="DM Sans, sans-serif"
                  fontWeight={600}
                >
                  {d.label}
                </text>
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
                Task 1
              </p>
              <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: "0.4rem" }}>
                Audio clustering pipeline
              </p>
              <p style={{ fontSize: "0.82rem", color: "var(--text2)", textAlign: "center", maxWidth: 260, lineHeight: 1.5 }}>
                K-Means on Spotify audio features + UMAP for 2D projection. Preview above is illustrative.
              </p>
            </div>
          </div>
        </div>

        {/* Cluster cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          <p className="section-label">Identified clusters</p>
          {CLUSTER_CARDS.map(c => (
            <div
              key={c.id}
              style={{
                background: "var(--s1)",
                border: `1px solid var(--t${c.tier}-dim, var(--border2))`,
                borderRadius: "var(--r)",
                padding: "1rem 1.1rem",
                opacity: 0.65,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                <span style={{ fontSize: "0.9rem", fontWeight: 700 }}>{c.name}</span>
                <span className={`chip chip-t${c.tier}`}>T{c.tier}</span>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--text2)", marginBottom: "0.5rem" }}>{c.features}</p>
              <div style={{ display: "flex", gap: "1rem" }}>
                <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{c.size} tracks</span>
                <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{c.countries} countries</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
