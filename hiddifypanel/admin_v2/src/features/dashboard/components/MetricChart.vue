<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import Chart from 'primevue/chart'
import { useChartTheme, alpha } from '../composables/useChartTheme'

export interface MetricSeries {
  label: string
  values: number[]
  color: string
  /** Overrides the chart type for this series (mixed bar + line charts). */
  type?: 'line' | 'bar'
  area?: boolean
  dashed?: boolean
}

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
    maxXTicks?: number
    tooltipExtra?: (index: number) => string[]
    stackTotalLabel?: string
    mirror?: boolean
  }>(),
  { type: 'line', height: 260, legend: true, stacked: false },
)

const { colors, baseOptions, areaFill } = useChartTheme()

/** Phones get shorter charts with fewer x labels so they stay readable. */
const phoneQuery = window.matchMedia('(max-width: 575px)')
const isPhone = ref(phoneQuery.matches)
const onPhoneChange = (event: MediaQueryListEvent) => (isPhone.value = event.matches)
phoneQuery.addEventListener('change', onPhoneChange)
onBeforeUnmount(() => phoneQuery.removeEventListener('change', onPhoneChange))

const chartHeight = computed(() => (isPhone.value && props.height > 180 ? Math.round(props.height * 0.8) : props.height))

const stackedAreas = computed(() => props.stacked && props.series.filter((series) => series.area).length > 1)

const isNegative = (series: MetricSeries) => series.values.some((value) => value < 0)

/**
 * Stacked areas fill down to the previous area of the same sign (upload and
 * download stack separately in mirror charts), so each band keeps its own
 * color instead of every area filling to the origin and blending together.
 */
function fillTarget(index: number): number | string | boolean {
  const series = props.series[index]!
  if (!series.area) return false
  if (!stackedAreas.value) return true
  const negative = isNegative(series)
  for (let prev = index - 1; prev >= 0; prev--) {
    const candidate = props.series[prev]!
    if ((candidate.type ?? props.type) === 'line' && candidate.area && isNegative(candidate) === negative) return prev
  }
  return 'origin'
}

const data = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((series, index) => {
    const isBar = (series.type ?? props.type) === 'bar'
    const stackedArea = stackedAreas.value && !isBar && series.area
    return {
      type: series.type ?? props.type,
      label: series.label,
      data: series.values,
      borderColor: series.color,
      backgroundColor: isBar
        ? alpha(series.color, colors.value.dark ? 0.75 : 0.85)
        : stackedArea
          ? alpha(series.color, colors.value.dark ? 0.45 : 0.35)
          : series.area
            ? areaFill(series.color)
            : 'transparent',
      fill: isBar ? false : fillTarget(index),
      borderWidth: isBar ? 0 : 2,
      borderDash: series.dashed ? [5, 4] : undefined,
      borderRadius: isBar ? 6 : undefined,
      maxBarThickness: isBar ? 34 : undefined,
      tension: 0.35,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHitRadius: 12,
      pointHoverBorderWidth: 2,
      pointHoverBackgroundColor: series.color,
      order: isBar ? 2 : 1,
    }
  }),
}))

const options = computed(() =>
  baseOptions({
    valueFormatter: props.valueFormatter,
    legend: props.legend && props.series.length > 1,
    stacked: props.stacked,
    yMax: props.yMax,
    maxXTicks: isPhone.value ? Math.min(props.maxXTicks ?? 8, 5) : props.maxXTicks,
    tooltipExtra: props.tooltipExtra,
    stackTotalLabel: props.stackTotalLabel,
    mirror: props.mirror,
  }),
)
</script>

<template>
  <Chart
    :type="type"
    :data="data"
    :options="options"
    class="metric-chart"
    :style="{ height: `${chartHeight}px` }"
  />
</template>

<style scoped>
.metric-chart :deep(canvas) {
  width: 100% !important;
}
</style>
