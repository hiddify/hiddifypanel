<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardUsage } from '@/core/api/generated'
import { formatBytes } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import TrendChip from './TrendChip.vue'

const props = defineProps<{
  usage: DashboardUsage | null
  series: DashboardDailyPoint[]
  nodes: DashboardNode[]
  stacked: boolean
}>()

const { t } = useI18n()

/** Same-scale comparison of the four readings admins check most. */
const buckets = computed(() => [
  { key: 'monthlyAverage', value: props.usage?.averages.daily_month ?? 0 },
  { key: 'weeklyAverage', value: props.usage?.averages.daily_week ?? 0 },
  { key: 'yesterday', value: props.usage?.totals.yesterday ?? 0 },
  { key: 'today', value: props.usage?.totals.today ?? 0 },
])

const labels = computed(() => buckets.value.map((bucket) => t(`dashboard.${bucket.key}`)))

const nodeName = (id: string) => {
  const numeric = Number(id)
  if (numeric === 0) return t('dashboard.thisServer')
  return props.nodes.find((node) => node.id === numeric)?.name || `${t('dashboard.node')} ${id}`
}

/** Per-node average/today/yesterday, derived from the same daily series the trend chart uses. */
const stackedSeries = computed(() => {
  const ids = new Set<string>()
  for (const point of props.series) {
    for (const id of Object.keys(point.by_child ?? {})) ids.add(id)
  }
  const ordered = [...ids].sort((a, b) => Number(a) - Number(b))
  const points = props.series
  const last = points.length - 1
  const nodeUsage = (id: string, index: number) => points[index]?.by_child?.[id]?.usage ?? 0
  const average = (id: string, days: number) => {
    const from = Math.max(0, points.length - days)
    const slice = points.slice(from)
    if (!slice.length) return 0
    return slice.reduce((sum, point) => sum + (point.by_child?.[id]?.usage ?? 0), 0) / slice.length
  }
  return ordered.map((id) => ({
    label: nodeName(id),
    values: [average(id, 30), average(id, 7), nodeUsage(id, last - 1), nodeUsage(id, last)],
    color: nodeColor(Number(id)),
    type: 'bar' as const,
  }))
})

const chartSeries = computed(() => {
  if (props.stacked && stackedSeries.value.length > 1) return stackedSeries.value
  return [
    {
      label: t('dashboard.dailyUsage'),
      values: buckets.value.map((bucket) => bucket.value),
      color: SERIES.usage,
      type: 'bar' as const,
    },
  ]
})
</script>

<template>
  <DashCard
    :title="t('dashboard.usageComparison')"
    :subtitle="t('dashboard.usageComparisonHint')"
    icon="pi pi-chart-line"
    :accent="SERIES.usageAvg"
    padded
  >
    <MetricChart
      :labels="labels"
      :series="chartSeries"
      type="bar"
      :stacked="stacked && stackedSeries.length > 1"
      :value-formatter="(value: number) => formatBytes(value, 0)"
      :height="216"
      :legend="stacked && stackedSeries.length > 1"
      :max-x-ticks="4"
    />
    <template #footer>
      <div class="comparison-footer">
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsYesterday') }}</span>
          <TrendChip :value="usage?.trends.day ?? null" />
        </div>
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsPreviousWeek') }}</span>
          <TrendChip :value="usage?.trends.week ?? null" />
        </div>
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsPreviousMonth') }}</span>
          <TrendChip :value="usage?.trends.month ?? null" />
        </div>
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.comparison-footer {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.comparison-footer__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
</style>
