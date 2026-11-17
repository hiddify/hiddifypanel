import { ref, watch, type Ref } from 'vue'

/**
 * How a chart is drawn, chosen per tile in its style sheet and kept in this browser: the chart type (the same data as
 * lines, fills, bars or candles), the colour theme, and the grid / average-line switches.
 */
export const LINE_TYPES = ['line', 'smooth', 'step', 'markers'] as const
export const FILL_TYPES = ['area', 'baseline'] as const
export const BAR_TYPES = ['column', 'lollipop', 'dots'] as const
/** Candle types: each candle is a bucket of points (open, high, low, close) */
export const RANGE_TYPES = ['candles', 'hollow', 'heikin', 'highlow'] as const
export const CHART_TYPES = [...LINE_TYPES, ...FILL_TYPES, ...BAR_TYPES, ...RANGE_TYPES] as const
export type ChartType = (typeof CHART_TYPES)[number]

/** The faces of a top-of-page tile: a small chart, or a ring / a bar pair against the previous period */
export const TILE_TYPES = ['area', 'line', 'column', 'step', 'dots', 'ring', 'compare'] as const
export type TileType = (typeof TILE_TYPES)[number]

export const TYPE_GROUPS = [
  { key: 'lines', types: LINE_TYPES as readonly string[] },
  { key: 'fills', types: FILL_TYPES as readonly string[] },
  { key: 'bars', types: BAR_TYPES as readonly string[] },
  { key: 'ranges', types: RANGE_TYPES as readonly string[] },
  { key: 'faces', types: ['ring', 'compare'] as readonly string[] },
] as const

export const OHLC_TYPES: readonly string[] = RANGE_TYPES

/** Rising / falling candles and the two sides of a baseline chart (Apple's system green and red) */
export const RISE = '#30d158'
export const FALL = '#ff453a'

export interface Palette {
  id: string
  /** Empty: the chart's own colours (each series keeps its meaning: usage indigo, online green, …) */
  colors: readonly string[]
}

export const PALETTES: readonly Palette[] = [
  { id: 'auto', colors: [] },
  { id: 'ios', colors: ['#0a84ff', '#ff9f0a', '#30d158', '#bf5af2', '#ff375f', '#64d2ff'] },
  { id: 'ocean', colors: ['#0ea5e9', '#14b8a6', '#6366f1', '#22d3ee', '#3b82f6', '#2dd4bf'] },
  { id: 'sunset', colors: ['#f97316', '#e11d48', '#f59e0b', '#db2777', '#ef4444', '#fb923c'] },
  { id: 'forest', colors: ['#16a34a', '#65a30d', '#0d9488', '#22c55e', '#84cc16', '#14b8a6'] },
  { id: 'grape', colors: ['#8b5cf6', '#d946ef', '#6366f1', '#a855f7', '#ec4899', '#c084fc'] },
  { id: 'graphite', colors: ['#475569', '#0ea5e9', '#94a3b8', '#334155', '#38bdf8', '#64748b'] },
]

/** The swatch of the "auto" theme: the dashboard's own series colours */
export const AUTO_SWATCH = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4'] as const

export interface ChartStyle {
  type: string
  palette: string
  grid: boolean
  average: boolean
}

export function paletteColors(id: string): readonly string[] {
  return PALETTES.find((palette) => palette.id === id)?.colors ?? []
}

/** The colour of a chart's n-th series under a theme (``fallback``: its own colour, kept by "auto") */
export function themed(style: ChartStyle | undefined, index: number, fallback: string): string {
  const colors = style ? paletteColors(style.palette) : []
  return colors.length ? colors[index % colors.length]! : fallback
}

const KEY = 'hm.dash.style.'

export function useChartStyle(tile: string, defaults: Partial<ChartStyle> & { type: string }, allowed: readonly string[] = CHART_TYPES): Ref<ChartStyle> & { reset: () => void } {
  const base: ChartStyle = { palette: 'auto', grid: true, average: false, ...defaults }
  let stored: Partial<ChartStyle> = {}
  try {
    stored = JSON.parse(localStorage.getItem(KEY + tile) ?? '{}') ?? {}
  } catch {
    stored = {}
  }
  const style = ref<ChartStyle>({
    type: typeof stored.type === 'string' && allowed.includes(stored.type) ? stored.type : base.type,
    palette: PALETTES.some((p) => p.id === stored.palette) ? stored.palette! : base.palette,
    grid: typeof stored.grid === 'boolean' ? stored.grid : base.grid,
    average: typeof stored.average === 'boolean' ? stored.average : base.average,
  })
  watch(style, (value) => localStorage.setItem(KEY + tile, JSON.stringify(value)), { deep: true })
  return Object.assign(style, { reset: () => (style.value = { ...base }) })
}
