import React, { useState } from "react"
import { ComposableMap, Geographies, Geography } from "react-simple-maps"
import type { CountryData } from "../types"

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
const TIER_HEX: Record<number, string> = { 1: "#1db954", 2: "#57e38a", 3: "#0a7a38" }

export function WorldMap({ countries, selected, onSelect }: {
  countries: CountryData[]
  selected: string
  onSelect: (code: string) => void
}) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; c: CountryData } | null>(null)
  const byNum = Object.fromEntries(countries.map(c => [c.numericCode, c]))

  function fill(id: string): string {
    const c = byNum[id]
    if (!c) return "#161616"
    if (c.code === selected) return c.dominantTier ? TIER_HEX[c.dominantTier] : "#ffffff"
    return c.dominantTier ? TIER_HEX[c.dominantTier] : "#252525"
  }

  function opacity(id: string): number {
    const c = byNum[id]
    if (!c) return 1
    if (c.code === selected) return 1
    if (!c.dominantTier) return 1
    return 0.5
  }

  return (
    <div
      className="map-section"
      onMouseLeave={() => setTooltip(null)}
    >
      <ComposableMap
        projection="geoNaturalEarth1"
        projectionConfig={{ rotate: [-10, 0, 0], scale: 185 }}
        style={{ width: "100%", height: "100%" }}
      >
          {/* eslint-disable-next-line */}
          <Geographies geography={GEO_URL}>
            {({ geographies }: { geographies: any[] }) =>
              geographies.map((geo: any) => {
                const id = String(+geo.id)
                const c = byNum[id]
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fill(id)}
                    fillOpacity={opacity(id)}
                    stroke="#0a0a0a"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: "none" },
                      hover:   { outline: "none", fillOpacity: c ? 0.9 : 0.25, cursor: c ? "pointer" : "default" },
                      pressed: { outline: "none" },
                    }}
                    onClick={() => c && onSelect(c.code)}
                    onMouseEnter={(e: React.MouseEvent<SVGPathElement>) => {
                      if (!c) return
                      const rect = (e.target as SVGElement).closest(".map-section")!.getBoundingClientRect()
                      setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, c })
                    }}
                    onMouseMove={(e: React.MouseEvent<SVGPathElement>) => {
                      if (!c) return
                      const rect = (e.target as SVGElement).closest(".map-section")!.getBoundingClientRect()
                      setTooltip(t => t ? { ...t, x: e.clientX - rect.left, y: e.clientY - rect.top } : null)
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })}
          </Geographies>
      </ComposableMap>

      {tooltip && (
        <div className="map-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          <p className="map-tooltip-name">{tooltip.c.name}</p>
          <p className="map-tooltip-text">{tooltip.c.topInsight}</p>
        </div>
      )}
    </div>
  )
}
