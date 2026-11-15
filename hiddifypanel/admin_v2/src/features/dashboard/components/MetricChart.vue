<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Chart from 'chart.js/auto'
import { useChartTheme } from '../composables/useChartTheme'
import type { ChartStyle } from '../composables/useChartStyle'
import { buildChart, type MetricSeries } from '../utils/chart-datasets'

export type { MetricSeries }

const props = withDefaults(
  defineProps<{
    labels: string[]
    series: MetricSeries[]
    type?: 'line' | 'bar'
    valueFormatter?: (value: number) => string
    height?: number
    legend?: boolean
    stacked?: boolean
    yMax?: number
    yMin?: number
    pageTooltip?: boolean
    maxXTicks?: number
    tooltipExtra?: (index: number) => string[]
    tooltipLabel?: (datasetIndex: number, dataIndex: number, formatted: string) => string | undefined
    stackTotalLabel?: string
    mirror?: boolean
    /** The look chosen in the tile's style sheet (type, colours, grid, average); none: the card's own look */
    chartStyle?: ChartStyle
    /** Points in the average line's window (7 days; a few live samples) */
    averageWindow?: number
    averageLabel?: string
  }>(),
  { type: 'line', height: 260, legend: true, stacked: false, averageWindow: 7 },
)

const { t } = useI18n()
const { colors, baseOptions, areaFill } = useChartTheme()

/** Phones get shorter charts with fewer x labels so they stay readable. */
const phoneQuery = window.matchMedia('(max-width: 575px)')
const isPhone = ref(phoneQuery.matches)
const onPhoneChange = (event: MediaQueryListEvent) => (isPhone.value = event.matches)
phoneQuery.addEventListener('change', onPhoneChange)
onBeforeUnmount(() => phoneQuery.removeEventListener('change', onPhoneChange))

const chartHeight = computed(() => (isPhone.value && props.height > 180 ? Math.round(props.height * 0.8) : props.height))

const built = computed(() =>
  buildChart(props.labels, props.series, props.chartStyle, {
    type: props.type,
    stacked: props.stacked,
    dark: colors.value.dark,
    surface: colors.value.surface,
    areaFill: areaFill as (color: string) => unknown,
    averageWindow: props.averageWindow,
    averageLabel: props.averageLabel ?? t('dashboard.rollingAverage'),
    totalLabel: props.stackTotalLabel ?? t('dashboard.chartStyle.total'),
  }),
)

/** Bars underneath: the chart's base type (a mixed chart takes each dataset's own) */
const baseType = computed<'line' | 'bar'>(() => (built.value.datasets.some((dataset) => dataset.type === 'bar') ? 'bar' : props.type))

const data = computed(() => ({ labels: built.value.labels, datasets: built.value.datasets }))

const options = computed(() =>
  baseOptions({
    valueFormatter: props.valueFormatter,
    legend: props.legend && built.value.datasets.filter((dataset) => !dataset.noTip).length > 1,
    stacked: built.value.stacked,
    yMax: props.yMax,
    yMin: props.yMin,
    pageTooltip: props.pageTooltip,
    maxXTicks: isPhone.value ? Math.min(props.maxXTicks ?? 8, 4) : props.maxXTicks,
    tooltipExtra: built.value.remapped ? undefined : props.tooltipExtra,
    tooltipLabel: built.value.remapped ? undefined : props.tooltipLabel,
    stackTotalLabel: props.stackTotalLabel,
    mirror: props.mirror,
    noGrid: props.chartStyle ? !props.chartStyle.grid : false,
    freeY: !built.value.zeroBased && props.yMin === undefined,
    ohlcNames: {
      open: t('dashboard.chartStyle.open'),
      high: t('dashboard.chartStyle.high'),
      low: t('dashboard.chartStyle.low'),
      close: t('dashboard.chartStyle.close'),
    },
  }),
)

/*
 * The chart is created once and updated in place. PrimeVue's <Chart> destroys
 * and recreates it on every data or options change, replaying the intro
 * animation on each dashboard poll even when nothing changed.
 */
const canvas = ref<HTMLCanvasElement | null>(null)
const chart = shallowRef<Chart | null>(null)

/** Comparable form of chart config; functions (formatters, gradients) are rebuilt every render. */
const signature = (value: unknown) => JSON.stringify(value, (_key, v) => (typeof v === 'function' ? undefined : v))

/**
 * Canvas text ignores the page's CSS: it needs the font named explicitly (else Persian falls back to a
 * system font), and the face has to be loaded before the canvas can draw with it.
 */
function applyPageFont() {
  const family = getComputedStyle(document.body).fontFamily
  if (family) Chart.defaults.font.family = family
  const primary = family
    .split(',')
    .map((f) => f.trim())
    .find((f) => !f.includes('Twemoji'))
  if (primary && document.fonts) {
    void Promise.all([document.fonts.load(`400 11px ${primary}`, 'آب 01'), document.fonts.load(`500 11px ${primary}`, 'آب 01')])
      .then(() => chart.value?.update('none'))
      .catch(() => undefined)
  }
}

let dataSignature = ''
let optionsSignature = ''

function createChart() {
  chart.value?.destroy()
  if (!canvas.value) return
  applyPageFont()
  chart.value = new Chart(canvas.value, {
    type: baseType.value,
    data: data.value,
    options: options.value,
  } as never)
  dataSignature = signature(data.value)
  optionsSignature = signature(options.value)
}

function syncChart() {
  const instance = chart.value
  if (!instance) return
  const nextData = data.value
  const nextDataSignature = signature(nextData)
  const nextOptionsSignature = signature(options.value)
  const dataChanged = nextDataSignature !== dataSignature
  const optionsChanged = nextOptionsSignature !== optionsSignature

  // Always hand over the latest callbacks (tooltip extras read current props).
  instance.options = options.value as never
  if (!dataChanged && !optionsChanged) return

  if (dataChanged) {
    instance.data.labels = nextData.labels
    const current = instance.data.datasets
    if (current.length === nextData.datasets.length) {
      // Keep dataset objects so Chart.js animates from the previous values.
      nextData.datasets.forEach((dataset, index) => Object.assign(current[index]!, dataset))
    } else {
      instance.data.datasets = nextData.datasets as never
    }
  }
  dataSignature = nextDataSignature
  optionsSignature = nextOptionsSignature
  // Only real data changes animate; theme or layout option changes apply instantly.
  instance.update(dataChanged ? undefined : 'none')
}

onMounted(createChart)
// A new chart type is drawn afresh (it grows in again), not morphed from the old shapes
watch([baseType, () => props.chartStyle?.type], createChart)
watch([data, options], syncChart)
onBeforeUnmount(() => {
  chart.value?.destroy()
  chart.value = null
})
</script>

<template>
  <div class="metric-chart" :style="{ height: `${chartHeight}px` }">
    <canvas ref="canvas" />
  </div>
</template>

<style scoped>
.metric-chart {
  position: relative;
}
.metric-chart canvas {
  width: 100% !important;
}
</style>
