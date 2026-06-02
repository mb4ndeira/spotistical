import { useRef, useEffect, useState } from "react"
import type { DayData } from "../types"

const TIER_HEX: Record<number, string> = { 1: "#1db954", 2: "#57e38a", 3: "#0a7a38" }
const DAY_ABB  = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const MON_LONG = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]
const MON_SHORT = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]

/** Build a list of items to render — either a month-divider or a day cell */
type Item =
  | { kind: "month"; label: string; key: string }
  | { kind: "day";   day: DayData;  key: string }

function buildItems(days: DayData[]): Item[] {
  const items: Item[] = []
  let lastMonth = -1
  for (const day of days) {
    const d     = new Date(day.date)
    const month = d.getMonth()
    const year  = d.getFullYear()
    if (month !== lastMonth) {
      items.push({ kind: "month", label: `${MON_SHORT[month]} ${year}`, key: `m-${year}-${month}` })
      lastMonth = month
    }
    items.push({ kind: "day", day, key: day.date })
  }
  return items
}

export function DateHeatmap({ days, selectedDate, onSelect }: {
  days:         DayData[]
  selectedDate: string
  onSelect:     (d: string) => void
}) {
  const scrollRef   = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLButtonElement>(null)
  const [activeMonth, setActiveMonth] = useState(() => {
    const d = days.find(d => d.date === selectedDate) ?? days[0]
    if (!d) return ""
    const dt = new Date(d.date)
    return `${MON_LONG[dt.getMonth()]} ${dt.getFullYear()}`
  })

  const items = buildItems(days)

  /* ── Center the selected cell on mount ──────────────────────── */
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ behavior: "instant", block: "nearest", inline: "center" })
  }, [])

  /* ── Smooth-scroll to center on selection change ────────────── */
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" })
  }, [selectedDate])

  /* ── Update floating month badge on scroll ───────────────────── */
  function handleScroll(e: React.UIEvent<HTMLDivElement>) {
    const container = e.currentTarget
    const left      = container.scrollLeft
    const dayEls    = container.querySelectorAll<HTMLElement>("[data-date]")
    for (const el of Array.from(dayEls)) {
      if (el.offsetLeft >= left) {
        const dt = new Date(el.dataset.date!)
        setActiveMonth(`${MON_LONG[dt.getMonth()]} ${dt.getFullYear()}`)
        break
      }
    }
  }

  return (
    <div className="section" style={{ paddingBottom: "1.75rem" }}>

      {/* ── Header row: label + floating month ─────────────────── */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem" }}>
        <p className="section-label" style={{ marginBottom: 0 }}>Daily activity</p>
        <span style={{
          fontSize: "0.8rem",
          fontWeight: 600,
          color: "var(--text2)",
          letterSpacing: "-0.01em",
          transition: "opacity 0.2s",
        }}>
          {activeMonth}
        </span>
      </div>

      {/* ── Scroll container with fade masks ────────────────────── */}
      <div style={{ position: "relative" }}>
        {/* Left fade */}
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 12,
          width: 48, zIndex: 2, pointerEvents: "none",
          background: "linear-gradient(to right, var(--bg), transparent)",
        }} />
        {/* Right fade */}
        <div style={{
          position: "absolute", right: 0, top: 0, bottom: 12,
          width: 48, zIndex: 2, pointerEvents: "none",
          background: "linear-gradient(to left, var(--bg), transparent)",
        }} />

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 0,
            overflowX: "auto",
            paddingBottom: "6px",
            paddingLeft: "1rem",
            paddingRight: "1rem",
            scrollbarWidth: "none",
          }}
        >
          {items.map((item, idx) => {
            if (item.kind === "month") {
              const isFirst = idx === 0
              return (
                <div
                  key={item.key}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                    justifyContent: "flex-end",
                    flexShrink: 0,
                    width: isFirst ? 8 : 32,
                    marginRight: 4,
                    paddingBottom: 8,
                    height: 88,
                  }}
                >
                  {!isFirst && (
                    <>
                      {/* vertical tick */}
                      <div style={{
                        width: 1,
                        height: 24,
                        background: "var(--border)",
                        marginBottom: 6,
                        marginLeft: 12,
                      }} />
                      {/* month label rotated vertical */}
                      <span style={{
                        fontSize: "0.68rem",
                        fontWeight: 700,
                        color: "var(--text3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        writingMode: "vertical-rl",
                        transform: "rotate(180deg)",
                        lineHeight: 1,
                        marginLeft: 6,
                      }}>
                        {item.label.split(" ")[0]}
                      </span>
                    </>
                  )}
                </div>
              )
            }

            /* ── Day cell ──────────────────────────────────────── */
            const { day } = item
            const d          = new Date(day.date)
            const dow        = d.getDay()
            const dayNum     = d.getDate()
            const isSelected = day.date === selectedDate
            const isSunday   = dow === 0
            const isMonday   = dow === 1
            const hasTier    = !!day.tier

            const bgAlpha = hasTier
              ? Math.round((0.12 + Math.min(0.35, day.insightCount / 20)) * 255)
                  .toString(16).padStart(2, "0")
              : ""
            const cellBg = hasTier ? `${TIER_HEX[day.tier!]}${bgAlpha}` : "#161616"

            return (
              <button
                key={day.date}
                ref={isSelected ? selectedRef : undefined}
                data-date={day.date}
                onClick={() => onSelect(day.date)}
                style={{
                  flexShrink: 0,
                  width: 48,
                  height: isSelected ? 84 : 76,
                  marginLeft: isMonday && idx > 0 ? 8 : 3,
                  marginRight: isSunday ? 8 : 0,
                  borderRadius: 12,
                  background: isSelected
                    ? hasTier ? `${TIER_HEX[day.tier!]}33` : "#252525"
                    : cellBg,
                  border: isSelected
                    ? `2px solid rgba(255,255,255,0.75)`
                    : "1px solid transparent",
                  boxShadow: isSelected ? "0 0 0 1px rgba(255,255,255,0.08)" : "none",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 5,
                  padding: 0,
                  outline: "none",
                  transition: "height 0.18s ease, background 0.15s ease, border-color 0.15s ease",
                  alignSelf: "flex-end",
                }}
              >
                {/* Day number */}
                <span style={{
                  fontSize: isSelected ? "1.1rem" : "0.95rem",
                  fontWeight: 700,
                  color: isSelected ? "#ffffff" : hasTier ? "var(--text)" : "var(--text2)",
                  lineHeight: 1,
                  transition: "font-size 0.18s ease",
                }}>
                  {dayNum}
                </span>

                {/* Day abbreviation */}
                <span style={{
                  fontSize: "0.62rem",
                  fontWeight: 600,
                  color: isSelected ? "var(--text2)" : "var(--text3)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  lineHeight: 1,
                }}>
                  {DAY_ABB[dow]}
                </span>

                {/* Signal dot */}
                <div style={{
                  width: hasTier ? 5 : 3,
                  height: hasTier ? 5 : 3,
                  borderRadius: "50%",
                  background: hasTier ? TIER_HEX[day.tier!] : "var(--border)",
                  opacity: isSelected ? 1 : hasTier ? 0.85 : 0.4,
                  transition: "background 0.15s",
                }} />
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Legend ──────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: "1.5rem", marginTop: "1rem", paddingLeft: "1rem" }}>
        {([1, 2, 3] as const).map(t => (
          <div key={t} style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", fontWeight: 500, color: "var(--text3)" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: TIER_HEX[t] }} />
            {t === 1 ? "Entity" : t === 2 ? "Thematic" : "Macro"}
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", fontWeight: 500, color: "var(--text3)" }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--border)" }} />
          No signal
        </div>
      </div>
    </div>
  )
}
