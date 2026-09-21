import { computed } from 'vue'
import { useLayout } from '@/core/layout/sakai/composables/layout'

/** Series palette shared by every dashboard chart. */
export const SERIES = {
  usage: '#6366f1',
  usageAvg: '#f59e0b',
  users: '#8b5cf6',
  online: '#10b981',
  upload: '#f97316',
  download: '#06b6d4',
  cpu: '#6366f1',
  memory: '#ec4899',
  disk: '#0ea5e9',
  neutral: '#94a3b8',
} as const

/** Distinct colors for stacked per-node usage. */
export const NODE_COLORS = [
  '#6366f1',
  '#06b6d4',
  '#f59e0b',
  '#10b981',
  '#ec4899',
  '#8b5cf6',
  '#f97316',
  '#14b8a6',
  '#ef4444',
  '#84cc16',
] as const

/**
 * Stable color for a node's identity, keyed by its id (not array position) so
 * the same node gets the same color on every chart across the dashboard.
 */
export function nodeColor(id: number): string {
  return NODE_COLORS[Math.abs(id) % NODE_COLORS.length]
}

export type ChartOptionsLike = Record<string, unknown>

interface TooltipItem {
  dataset: { label?: string }
  parsed: { x: number; y: number }
  label?: string
  dataIndex: number
  raw?: unknown
}

export interface BaseOptions {
  /** Formats axis ticks and tooltip values (bytes, percent, counts, …). */
  valueFormatter?: (value: number) => string
  legend?: boolean
  stacked?: boolean
  yMax?: number
  yTitle?: string
  hideXGrid?: boolean
  maxXTicks?: number
  /** Extra tooltip lines for the hovered index (online users, per-node rates, …). */
  tooltipExtra?: (index: number) => string[]
  stackTotalLabel?: string
  /** Lets the y-axis range below zero (e.g. upload above / download below a mirrored stacked area). */
  mirror?: boolean
}

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

/** Converts `#rrggbb` to `rgba()` so series can be used as translucent fills. */
export function alpha(color: string, opacity: number): string {
  const hex = color.replace('#', '')
  const int = Number.parseInt(hex.length === 3 ? hex.replace(/(.)/g, '$1$1') : hex, 16)
  const r = (int >> 16) & 255
  const g = (int >> 8) & 255
  const b = int & 255
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}

/**
 * Chart colors and option defaults that follow the active PrimeVue theme and
 * react to the dark mode toggle.
 */
export function useChartTheme() {
  const { isDarkTheme } = useLayout()

  const colors = computed(() => {
    const dark = isDarkTheme.value
    return {
      dark,
      text: cssVar('--p-text-color', dark ? '#e2e8f0' : '#334155'),
      muted: cssVar('--p-text-muted-color', dark ? '#94a3b8' : '#64748b'),
      grid: dark ? 'rgba(148, 163, 184, 0.16)' : 'rgba(100, 116, 139, 0.14)',
      surface: cssVar('--p-content-background', dark ? '#1f2937' : '#ffffff'),
      border: cssVar('--p-content-border-color', dark ? '#374151' : '#e2e8f0'),
    }
  })

  /** Vertical gradient fill for area charts, resolved lazily per render. */
  function areaFill(color: string) {
    return (context: { chart: { ctx: CanvasRenderingContext2D; chartArea?: { top: number; bottom: number } } }) => {
      const { ctx, chartArea } = context.chart
      if (!chartArea) return alpha(color, 0.15)
      const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
      gradient.addColorStop(0, alpha(color, 0.38))
      gradient.addColorStop(1, alpha(color, 0.02))
      return gradient
    }
  }

  function baseOptions(options: BaseOptions = {}): ChartOptionsLike {
    const { text, muted, grid, surface, border } = colors.value
    const format = options.valueFormatter ?? ((value: number) => String(value))

    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: options.legend ?? true,
          position: 'top',
          align: 'end',
          labels: {
            color: muted,
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 8,
            boxHeight: 8,
            padding: 16,
            font: { size: 11, weight: '500' },
          },
        },
        tooltip: {
          enabled: true,
          backgroundColor: surface,
          titleColor: text,
          bodyColor: text,
          footerColor: muted,
          borderColor: border,
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          displayColors: true,
          usePointStyle: true,
          titleMarginBottom: 8,
          footerMarginTop: 8,
          callbacks: {
            title: (items: TooltipItem[]) => items[0]?.label ?? '',
            label: (item: TooltipItem) =>
              `${item.dataset.label ? `${item.dataset.label}: ` : ''}${format(item.parsed.y)}`,
            footer: (items: TooltipItem[]) => {
              if (!items.length) return []
              const lines: string[] = []
              if ((options.stacked ?? false) && items.length > 1 && options.stackTotalLabel) {
                const total = items.reduce((sum, item) => sum + (Number(item.parsed.y) || 0), 0)
                lines.push(`${options.stackTotalLabel ?? 'Total'}: ${format(total)}`)
              }
              lines.push(...(options.tooltipExtra?.(items[0]!.dataIndex) ?? []))
              return lines
            },
          },
        },
      },
      scales: {
        x: {
          stacked: options.stacked ?? false,
          grid: { display: !options.hideXGrid, color: grid, drawBorder: false },
          border: { display: false },
          ticks: {
            color: muted,
            font: { size: 11 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: options.maxXTicks ?? 8,
          },
        },
        y: {
          stacked: options.stacked ?? false,
          beginAtZero: !options.mirror,
          max: options.yMax,
          grid: { color: grid, drawBorder: false },
          border: { display: false },
          title: options.yTitle ? { display: true, text: options.yTitle, color: muted } : undefined,
          ticks: {
            color: muted,
            font: { size: 11 },
            maxTicksLimit: 5,
            callback: (value: number | string) => format(Number(value)),
          },
        },
      },
    }
  }

  return { colors, baseOptions, areaFill }
}
