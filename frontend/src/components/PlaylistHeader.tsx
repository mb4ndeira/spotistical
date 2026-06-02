import { Play } from "lucide-react"
import type { Track } from "../types"

function coverGradient(seed: string): string {
  let h = 0
  for (let i = 0; i < seed.length; i++) { h = ((h << 5) - h) + seed.charCodeAt(i); h |= 0 }
  const h1 = Math.abs(h) % 360
  const h2 = (h1 + 137) % 360
  return `linear-gradient(135deg, hsl(${h1},55%,15%), hsl(${h2},65%,22%))`
}

export function PlaylistHeader({ tracks, country, date }: {
  tracks: Track[]
  country: string
  date: string
}) {
  const featured = tracks.slice(0, 8)

  return (
    <div style={{ marginBottom: "2.5rem" }}>
      <p className="section-label">Top 50 · {country} · {date}</p>
      <div className="playlist-scroll">
        {featured.map(track => (
          <div key={track.id} className="playlist-card">
            <div
              className="playlist-cover"
              style={{ background: coverGradient(track.id + track.name) }}
            >
              <button className="play-btn" aria-label={`Play ${track.name}`}>
                <Play size={18} fill="currentColor" strokeWidth={0} />
              </button>
            </div>
            <div className="playlist-rank">#{track.rank}</div>
            <div className="playlist-title">{track.name}</div>
            <div className="playlist-artist">{track.artists}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
