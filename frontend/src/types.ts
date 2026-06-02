export interface AudioFeatures {
  danceability:     number  // 0-1
  energy:           number  // 0-1
  valence:          number  // 0-1
  acousticness:     number  // 0-1
  liveness:         number  // 0-1
  speechiness:      number  // 0-1
}

export type TierNumber = 1 | 2 | 3

export interface InsightSignal {
  tier:          TierNumber
  score:         number        // 0-1
  label:         string        // short UI label
  description:   string        // 1-2 sentences
  contradiction?: string       // present when audio/lyric tension detected
}

export interface Track {
  id:           string
  rank:         number
  previousRank: number
  name:         string
  artists:      string
  clusterLabel: string
  tiers:        TierNumber[]
  audioFeatures: AudioFeatures
  insights:     InsightSignal[]
  narrative:    string         // LLM-generated paragraph
}

export interface CountryData {
  code:          string  // ISO2C
  name:          string
  numericCode:   string  // for world-atlas GeoJSON matching
  dominantTier:  TierNumber | null
  insightCount:  number
  topInsight:    string
}

export interface DayData {
  date:         string          // YYYY-MM-DD
  tier:         TierNumber | null
  insightCount: number
}
