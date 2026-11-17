import { alpha } from '../composables/useChartTheme'
import { FALL, OHLC_TYPES, RISE, paletteColors, type ChartStyle } from '../composables/useChartStyle'
import { rollingAverage } from './series'

export interface MetricSeries {
  label: string
  values: number[]
  color: string
  /** Overrides the chart type for this series (mixed bar + line charts). */
  type?: 'line' | 'bar'
  area?: boolean
  dashed?: boolean
}

export interface Ohlc {
  o: number
  h: number
  l: number
  c: number
}

export interface BuildContext {
  type: 'line' | 'bar'
  stacked: boolean
  dark: boolean
  surface: string
  areaFill: (color: string) => unknown
  averageWindow: number
  averageLabel: string
  /** The name of a summed side (several nodes drawn as one candle / baseline / lollipop series) */
  totalLabel: string
}

export interface BuiltChart {
  labels: string[]
  datasets: Record<string, unknown>[]
  stacked: boolean
  /** The y axis starts at zero (candles and baselines use the data's own range) */
  zeroBased: boolean
  /** Points no longer match the caller's indexes or series (buckets, summed sides): its tooltip extras are dropped */
  remapped: boolean
}

type Dataset = Record<string, unknown>

const isNegative = (series: MetricSeries) => series.values.some((value) => value < 0)

/** The chart as the card asked for it (no style chosen): the original look */
function plainDatasets(series: MetricSeries[], ctx: BuildContext, stacked: boolean): Dataset[] {
  const stackedAreas = stacked && series.filter((one) => one.area).length > 1
  /** Stacked areas fill down to the previous area of the same sign (mirror charts stack each side apart) */
  const fillTarget = (index: number): number | string | boolean => {
    const one = series[index]!
    if (!one.area) return false
    if (!stackedAreas) return true
    const negative = isNegative(one)
    for (let prev = index - 1; prev >= 0; prev--) {
      const candidate = series[prev]!
      if ((candidate.type ?? ctx.type) === 'line' && candidate.area && isNegative(candidate) === negative) return prev
    }
    return 'origin'
  }
  return series.map((one, index) => {
    const isBar = (one.type ?? ctx.type) === 'bar'
    const stackedArea = stackedAreas && !isBar && one.area
    return {
      type: one.type ?? ctx.type,
      label: one.label,
      data: one.values,
      borderColor: one.color,
      backgroundColor: isBar ? alpha(one.color, ctx.dark ? 0.75 : 0.85) : stackedArea ? alpha(one.color, ctx.dark ? 0.45 : 0.35) : one.area ? ctx.areaFill(one.color) : 'transparent',
      fill: isBar ? false : fillTarget(index),
      borderWidth: isBar ? 0 : 2,
      borderDash: one.dashed ? [5, 4] : undefined,
      borderRadius: isBar ? 6 : undefined,
      maxBarThickness: isBar ? 34 : undefined,
      tension: 0.35,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHitRadius: 12,
      pointHoverBorderWidth: 2,
      pointHoverBackgroundColor: one.color,
      order: isBar ? 2 : 1,
    }
  })
}

interface Side {
  label: string
  values: number[]
  color: string
  negative: boolean
}

/** One series per sign: several nodes summed (a mirror chart keeps upload above and download below apart) */
function sides(series: MetricSeries[], ctx: BuildContext, accent: string): Side[] {
  const groups = [series.filter((one) => !isNegative(one)), series.filter(isNegative)]
  return groups
    .filter((group) => group.length)
    .map((group, index) => {
      const width = Math.max(...group.map((one) => one.values.length))
      const values = Array.from({ length: width }, (_, i) => group.reduce((sum, one) => sum + (one.values[i] ?? 0), 0))
      const first = group[0]!
      const negative = isNegative(first)
      return {
        label: group.length === 1 ? first.label : `${ctx.totalLabel}${groups[1]!.length && groups[0]!.length ? (negative ? ' ↓' : ' ↑') : ''}`,
        values,
        color: index === 0 ? first.color : first.color === series[0]!.color ? accent : first.color,
        negative,
      }
    })
}

/** Points into candles: few points one candle each (opened at the point before), more into buckets of a few */
export function toOhlc(values: number[], labels: string[]): { candles: Ohlc[]; labels: string[] } {
  const size = values.length < 12 ? 1 : Math.ceil(values.length / 18)
  const candles: Ohlc[] = []
  const out: string[] = []
  for (let start = 0; start < values.length; start += size) {
    const bucket = values.slice(start, start + size)
    const open = start > 0 ? values[start - 1]! : bucket[0]!
    const close = bucket[bucket.length - 1]!
    candles.push({ o: open, c: close, h: Math.max(open, ...bucket), l: Math.min(open, ...bucket) })
    out.push(labels[Math.min(values.length - 1, start + size - 1)] ?? '')
  }
  return { candles, labels: out }
}

/** Heikin-Ashi: candles averaged with the one before, so a run reads as one colour */
export function heikinAshi(candles: Ohlc[]): Ohlc[] {
  const out: Ohlc[] = []
  candles.forEach((candle, index) => {
    const c = (candle.o + candle.h + candle.l + candle.c) / 4
    const prev = out[index - 1]
    const o = prev ? (prev.o + prev.c) / 2 : (candle.o + candle.c) / 2
    out.push({ o, c, h: Math.max(candle.h, o, c), l: Math.min(candle.l, o, c) })
  })
  return out
}

/** A candle rises when the value grows (below zero: when its size grows) */
const rising = (candle: Ohlc, negative: boolean) => (negative ? Math.abs(candle.c) >= Math.abs(candle.o) : candle.c >= candle.o)

function averageLine(values: number[], window: number, label: string, color: string): Dataset {
  return {
    type: 'line',
    label,
    data: rollingAverage(values, Math.max(2, window)),
    borderColor: color,
    backgroundColor: 'transparent',
    borderWidth: 1.75,
    borderDash: [5, 4],
    fill: false,
    tension: 0.35,
    pointRadius: 0,
    pointHoverRadius: 4,
    pointHitRadius: 10,
    order: 0,
  }
}

/** The data drawn in the chosen style; no style: the card's own look */
export function buildChart(labels: string[], series: MetricSeries[], style: ChartStyle | undefined, ctx: BuildContext): BuiltChart {
  if (!style || !series.length) return { labels, datasets: plainDatasets(series, ctx, ctx.stacked), stacked: ctx.stacked, zeroBased: true, remapped: false }

  const palette = paletteColors(style.palette)
  const colored = palette.length ? series.map((one, index) => ({ ...one, color: palette[index % palette.length]! })) : series
  const accent = palette[1] ?? '#f59e0b'
  const averageColor = palette.length ? palette[1 % palette.length]! : '#f59e0b'
  const type = style.type
  const many = (list: unknown[]) => list.length > 1

  // Candles: a candle set per side, its wick behind its body (floating bars on one x, not side by side)
  if (OHLC_TYPES.includes(type)) {
    const groups = sides(colored, ctx, accent)
    let outLabels = labels
    const datasets: Dataset[] = []
    for (const side of groups) {
      const raw = toOhlc(side.values, labels)
      outLabels = raw.labels
      const candles = type === 'heikin' ? heikinAshi(raw.candles) : raw.candles
      const up = candles.map((candle) => rising(candle, side.negative))
      const tone = (i: number) => (up[i] ? RISE : FALL)
      if (type === 'highlow') {
        datasets.push({
          type: 'bar',
          label: side.label,
          data: candles.map((candle) => [candle.l, candle.h]),
          ohlc: candles,
          backgroundColor: alpha(side.color, ctx.dark ? 0.7 : 0.8),
          borderRadius: 999,
          borderSkipped: false,
          barPercentage: 0.42,
          categoryPercentage: 0.9,
          minBarLength: 3,
          grouped: false,
          order: 2,
        })
        datasets.push({
          type: 'line',
          label: side.label,
          noTip: true,
          data: candles.map((candle) => candle.c),
          showLine: false,
          pointRadius: 3,
          pointHoverRadius: 3,
          pointBackgroundColor: ctx.surface,
          pointBorderColor: side.color,
          pointBorderWidth: 2,
          order: 1,
        })
        continue
      }
      datasets.push({
        type: 'bar',
        label: side.label,
        noTip: true,
        data: candles.map((candle) => [candle.l, candle.h]),
        backgroundColor: candles.map((_, i) => tone(i)),
        barThickness: 1.5,
        minBarLength: 1,
        grouped: false,
        order: 3,
      })
      datasets.push({
        type: 'bar',
        label: side.label,
        data: candles.map((candle) => [candle.o, candle.c]),
        ohlc: candles,
        backgroundColor: candles.map((_, i) => (type === 'hollow' && up[i] ? (ctx.dark ? 'rgba(0,0,0,0.25)' : '#ffffff') : tone(i))),
        borderColor: candles.map((_, i) => tone(i)),
        borderWidth: type === 'hollow' ? 1.5 : 0,
        borderRadius: 3,
        borderSkipped: false,
        barPercentage: 0.62,
        categoryPercentage: 0.86,
        maxBarThickness: 22,
        minBarLength: 2,
        grouped: false,
        order: 2,
      })
    }
    if (style.average)
      for (const side of groups) {
        const raw = toOhlc(side.values, labels)
        const closes = (type === 'heikin' ? heikinAshi(raw.candles) : raw.candles).map((candle) => candle.c)
        datasets.push(averageLine(closes, Math.round(ctx.averageWindow / Math.max(1, side.values.length / closes.length)), many(groups) ? `${ctx.averageLabel} · ${side.label}` : ctx.averageLabel, averageColor))
      }
    return { labels: outLabels, datasets, stacked: false, zeroBased: false, remapped: true }
  }

  // Baseline: one line per side, green above its average and red below, filled to that average
  if (type === 'baseline') {
    const groups = sides(colored, ctx, accent)
    const datasets: Dataset[] = []
    for (const side of groups) {
      const mean = side.values.reduce((sum, value) => sum + value, 0) / Math.max(1, side.values.length)
      const [high, low] = side.negative ? [FALL, RISE] : [RISE, FALL]
      datasets.push({
        type: 'line',
        label: side.label,
        data: side.values,
        borderWidth: 2,
        borderColor: high,
        segment: { borderColor: (seg: { p0: { parsed: { y: number } }; p1: { parsed: { y: number } } }) => ((seg.p0.parsed.y + seg.p1.parsed.y) / 2 >= mean ? high : low) },
        fill: { target: { value: mean }, above: alpha(high, ctx.dark ? 0.22 : 0.16), below: alpha(low, ctx.dark ? 0.22 : 0.16) },
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHitRadius: 12,
        pointHoverBackgroundColor: side.color,
        order: 1,
      })
      datasets.push({
        type: 'line',
        label: many(groups) ? `${ctx.averageLabel} · ${side.label}` : ctx.averageLabel,
        data: side.values.map(() => mean),
        borderColor: alpha(ctx.dark ? '#e2e8f0' : '#475569', 0.55),
        borderWidth: 1,
        borderDash: [3, 4],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0,
        pointHitRadius: 0,
        order: 0,
      })
    }
    return { labels, datasets, stacked: false, zeroBased: false, remapped: true }
  }

  // Lollipop: a thin stem and a round head per point, per side
  if (type === 'lollipop') {
    const groups = sides(colored, ctx, accent)
    const datasets: Dataset[] = groups.flatMap((side) => [
      {
        type: 'bar',
        label: side.label,
        noTip: true,
        data: side.values,
        backgroundColor: alpha(side.color, 0.55),
        barThickness: 2,
        grouped: false,
        order: 2,
      },
      {
        type: 'line',
        label: side.label,
        data: side.values,
        showLine: false,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHitRadius: 12,
        pointBackgroundColor: side.color,
        pointBorderColor: ctx.surface,
        pointBorderWidth: 2,
        borderColor: side.color,
        backgroundColor: side.color,
        order: 1,
      },
    ])
    if (style.average) for (const side of groups) datasets.push(averageLine(side.values, ctx.averageWindow, many(groups) ? `${ctx.averageLabel} · ${side.label}` : ctx.averageLabel, averageColor))
    return { labels, datasets, stacked: false, zeroBased: true, remapped: true }
  }

  // Lines, fills, columns and dots: every series keeps its own line, in its own (or the theme's) colour
  const column = type === 'column'
  const stacked = ctx.stacked && (column || type === 'area')
  const shaped = colored.map((one) => ({ ...one, type: (column ? 'bar' : 'line') as 'bar' | 'line', area: type === 'area' }))
  const datasets = plainDatasets(shaped, ctx, stacked).map((dataset, index) => {
    const color = shaped[index]!.color
    if (type === 'line') return { ...dataset, tension: 0 }
    if (type === 'smooth') return { ...dataset, tension: 0.4, cubicInterpolationMode: 'monotone' }
    if (type === 'step') return { ...dataset, tension: 0, stepped: 'middle' }
    if (type === 'markers') return { ...dataset, tension: 0.2, pointRadius: 3, pointBackgroundColor: ctx.surface, pointBorderColor: color, pointBorderWidth: 2 }
    if (type === 'dots') return { ...dataset, showLine: false, pointRadius: 3.5, pointHoverRadius: 6, pointBackgroundColor: color, pointBorderColor: color }
    if (column) return { ...dataset, borderRadius: 4 }
    return dataset
  })
  if (style.average) {
    const groups = sides(colored, ctx, accent)
    for (const side of groups) datasets.push(averageLine(side.values, ctx.averageWindow, many(groups) ? `${ctx.averageLabel} · ${side.label}` : ctx.averageLabel, averageColor) as never)
  }
  return { labels, datasets, stacked, zeroBased: true, remapped: false }
}
