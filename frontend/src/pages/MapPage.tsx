import { useState } from "react"
import { useAutoAnimate } from "@formkit/auto-animate/react"
import { COUNTRIES, HEATMAP_BRAZIL, TRACKS_BRAZIL } from "../data/placeholder"
import { WorldMap }       from "../components/WorldMap"
import { DateHeatmap }    from "../components/DateHeatmap"
import { TrackCard }      from "../components/TrackCard"
import { PlaylistHeader } from "../components/PlaylistHeader"

export function MapPage() {
  const [country, setCountry]   = useState("BR")
  const [date, setDate]         = useState("2024-02-10")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [trackListRef]          = useAutoAnimate<HTMLDivElement>()

  const countryData = COUNTRIES.find(c => c.code === country)

  function toggleTrack(id: string) {
    setExpanded(prev => prev === id ? null : id)
  }

  return (
    <>
      <WorldMap
        countries={COUNTRIES}
        selected={country}
        onSelect={setCountry}
      />

      <DateHeatmap
        days={HEATMAP_BRAZIL}
        selectedDate={date}
        onSelect={setDate}
      />

      {countryData && (
        <div className="content-section">
          <div className="content-header">
            <h1 className="content-country">{countryData.name}</h1>
            <p className="content-meta">
              {countryData.insightCount} insights this week
              {countryData.dominantTier && (
                <> · Dominant signal:{" "}
                  <span style={{ color: `var(--t${countryData.dominantTier})` }}>
                    Tier {countryData.dominantTier}
                  </span>
                </>
              )}
            </p>
          </div>

          <PlaylistHeader
            tracks={TRACKS_BRAZIL}
            country={countryData.name}
            date={date}
          />

          <div>
            <div className="track-list-header">
              <span>#</span>
              <span>±</span>
              <span>Track</span>
              <span style={{ textAlign: "right" }}>Signals</span>
              <span />
            </div>
            <div ref={trackListRef}>
              {TRACKS_BRAZIL.map(track => (
                <TrackCard
                  key={track.id}
                  track={track}
                  expanded={expanded === track.id}
                  onToggle={() => toggleTrack(track.id)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
