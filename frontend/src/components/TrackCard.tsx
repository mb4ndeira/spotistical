import { motion, AnimatePresence } from "motion/react"
import { Disclosure, DisclosureButton, DisclosurePanel } from "@headlessui/react"
import { ChevronDown, ArrowUp, ArrowDown, Minus } from "lucide-react"
import type { Track } from "../types"
import { AudioRadar } from "./AudioRadar"
import { AudioStrip } from "./AudioStrip"
import { InsightCard } from "./InsightCard"

function coverGradient(seed: string): string {
  let h = 0
  for (let i = 0; i < seed.length; i++) { h = ((h << 5) - h) + seed.charCodeAt(i); h |= 0 }
  const h1 = Math.abs(h) % 360
  const h2 = (h1 + 137) % 360
  return `linear-gradient(135deg, hsl(${h1},55%,15%), hsl(${h2},65%,22%))`
}

const TIER_COLORS: Record<number, string> = { 1: "var(--t1)", 2: "var(--t2)", 3: "var(--t3)" }

function Movement({ cur, prev }: { cur: number; prev: number }) {
  const d = prev - cur
  if (d > 0) return (
    <span className="track-move move-up flex items-center justify-center gap-0.5">
      <ArrowUp size={12} strokeWidth={2.5} />{d}
    </span>
  )
  if (d < 0) return (
    <span className="track-move move-down flex items-center justify-center gap-0.5">
      <ArrowDown size={12} strokeWidth={2.5} />{Math.abs(d)}
    </span>
  )
  return (
    <span className="track-move move-same flex items-center justify-center">
      <Minus size={12} strokeWidth={2.5} />
    </span>
  )
}

export function TrackCard({ track, expanded, onToggle }: {
  track: Track
  expanded: boolean
  onToggle: () => void
}) {
  const radarColor = track.tiers[0] ? TIER_COLORS[track.tiers[0]] : "var(--text3)"

  return (
    <Disclosure as="div" className={`track-row${expanded ? " expanded" : ""}`}>
      <DisclosureButton
        as="div"
        className="track-row-main"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        {/* Rank */}
        <div className="track-num">{track.rank}</div>

        {/* Movement */}
        <Movement cur={track.rank} prev={track.previousRank} />

        {/* Identity */}
        <div className="track-id">
          <div
            className="track-cover"
            style={{ background: coverGradient(track.id + track.name) }}
          />
          <div className="track-name-row">
            <div className="track-name">{track.name}</div>
            <div className="track-artist">{track.artists}</div>
          </div>
        </div>

        {/* Chips */}
        <div className="track-chips">
          {track.tiers.map(t => (
            <span key={t} className={`chip chip-t${t}`}>T{t}</span>
          ))}
          <span className="chip chip-cluster">{track.clusterLabel}</span>
        </div>

        {/* Expand chevron */}
        <motion.span
          className="track-expand-icon"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          style={{ display: "flex", alignItems: "center" }}
        >
          <ChevronDown size={16} strokeWidth={2} />
        </motion.span>
      </DisclosureButton>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <DisclosurePanel static>
              <div className="track-detail">
                {/* Left col: radar + audio strip */}
                <div>
                  <p className="detail-col-label">Audio fingerprint</p>
                  <AudioRadar features={track.audioFeatures} color={radarColor} />
                  <AudioStrip features={track.audioFeatures} />
                </div>

                {/* Right col: signals */}
                <div className="signals-col">
                  <p className="detail-col-label">{track.insights.length} signal{track.insights.length !== 1 ? "s" : ""} fired</p>
                  {track.insights.map((s, i) => <InsightCard key={i} signal={s} />)}
                  {track.insights.length === 0 && (
                    <p className="text-sm" style={{ color: "var(--text3)" }}>
                      No explainable signal found for this song this week.
                    </p>
                  )}
                </div>

                {/* Full-width narrative */}
                <div className="narrative">
                  <p className="narrative-label">AI interpretation</p>
                  <p className="narrative-text">{track.narrative}</p>
                </div>
              </div>
            </DisclosurePanel>
          </motion.div>
        )}
      </AnimatePresence>
    </Disclosure>
  )
}
