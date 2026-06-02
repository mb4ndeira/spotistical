import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts"
import type { AudioFeatures } from "../types"

const LABELS: Record<keyof AudioFeatures, string> = {
  danceability: "Dance",
  energy:       "Energy",
  valence:      "Mood",
  acousticness: "Acoustic",
  liveness:     "Live",
  speechiness:  "Speech",
}

export function AudioRadar({ features, color = "var(--t3)" }: { features: AudioFeatures; color?: string }) {
  const data = (Object.keys(features) as (keyof AudioFeatures)[]).map(k => ({
    f: LABELS[k],
    v: Math.round(features[k] * 100),
  }))

  return (
    <div className="radar-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="68%">
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="f"
            tick={{ fill: "var(--text3)", fontSize: 10, fontFamily: "Inter" }}
          />
          <Radar
            dataKey="v"
            fill={color}
            fillOpacity={0.15}
            stroke={color}
            strokeWidth={1.5}
            dot={{ fill: color, r: 2 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
