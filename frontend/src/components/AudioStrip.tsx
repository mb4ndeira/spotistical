import type { AudioFeatures } from "../types"

const BARS: { key: keyof AudioFeatures; label: string }[] = [
  { key: "danceability", label: "Dance"   },
  { key: "energy",       label: "Energy"  },
  { key: "valence",      label: "Mood"    },
  { key: "acousticness", label: "Acoustic"},
  { key: "liveness",     label: "Live"    },
]

export function AudioStrip({ features }: { features: AudioFeatures }) {
  return (
    <div className="audio-strip">
      {BARS.map(b => (
        <div key={b.key} className="abar">
          <div className="abar-track">
            <div
              className="abar-fill"
              style={{
                height: `${features[b.key] * 100}%`,
                background: "rgba(255,255,255,0.55)",
              }}
            />
          </div>
          <div className="abar-label">{b.label}</div>
        </div>
      ))}
    </div>
  )
}
