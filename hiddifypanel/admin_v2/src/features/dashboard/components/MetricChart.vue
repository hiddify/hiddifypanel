<script setup lang="ts">
import { computed } from 'vue'
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
  }>(),
  { type: 'line', height: 260, legend: true, stacked: false },
)

const { colors, baseOptions, areaFill } = useChartTheme()

const data = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((series) => {
    const isBar = (series.type ?? props.type) === 'bar'
    return {
      type: series.type ?? props.type,
      label: series.label,
      data: series.values,
      borderColor: series.color,
      backgroundColor: isBar ? alpha(series.color, colors.value.dark ? 0.75 : 0.85) : series.area ? areaFill(series.color) : 'transparent',
      fill: !isBar && series.area,
      borderWidth: isBar ? 0 : 2,
      borderDash: series.dashed ? [5, 4] : undefined,
      borderRadius: isBar ? 6 : undefined,
      maxBarThickness: isBar ? 34 : undefined,
      tension: 0.35,
      pointRadius: 0,
      pointHoverRadius: 4,
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
    maxXTicks: props.maxXTicks,
  }),
)
</script>

<template>
  <Chart
    :type="type"
    :data="data"
    :options="options"
    class="metric-chart"
    :style="{ height: `${height}px` }"
  />
</template>

<style scoped>
.metric-chart :deep(canvas) {
  width: 100% !important;
}
</style>
