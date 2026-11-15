<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardUsage } from '@/core/api/generated'
import { formatBytes } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import TrendChip from './TrendChip.vue'
import { dashboardNodeName } from '../utils/node-name'
import ChartViewSwitch from './ChartViewSwitch.vue'
import ActivityRings from './views/ActivityRings.vue'
import RankedBars from './views/RankedBars.vue'
import { useChartView } from '../composables/useChartView'
import ChartStyleButton from './ChartStyleButton.vue'
import { BAR_TYPES, themed, useChartStyle } from '../composables/useChartStyle'

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
  const node = props.nodes.find((row) => row.id === numeric)
  if (numeric === 0) return dashboardNodeName(0, node?.name, t('dashboard.thisServer'))
  return node?.name || `${t('dashboard.node')} ${id}`
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
    // Only the days this server had traffic: idle days do not pull the average down
    const used = points
      .slice(from)
      .map((point) => point.by_child?.[id]?.usage ?? 0)
      .filter((usage) => usage > 0)
    return used.length ? used.reduce((sum, usage) => sum + usage, 0) / used.length : 0
  }
  return ordered.map((id) => ({
    label: nodeName(id),
    values: [average(id, 30), average(id, 7), nodeUsage(id, last - 1), nodeUsage(id, last)],
    color: nodeColor(Number(id)),
    type: 'bar' as const,
  }))
})

/** How the four readings are shown: bars, activity rings, or ranked bars */
const VIEWS = ['bars', 'rings', 'ranked'] as const
const view = useChartView('usage-comparison', VIEWS)
/** The bars as columns, lollipops or dots, in the chosen colours (the rings and ranked bars take the colours too) */
const style = useChartStyle('usage-comparison', { type: 'column' }, BAR_TYPES)
const resetStyle = style.reset
const viewOptions = computed(() => [
  { value: 'bars', icon: 'pi pi-chart-bar', label: t('dashboard.views.bars') },
  { value: 'rings', icon: 'pi pi-circle', label: t('dashboard.views.rings') },
  { value: 'ranked', icon: 'pi pi-sort-amount-down', label: t('dashboard.views.ranked') },
])
/** Today outermost: the reading the eye goes to first */
const RING_COLORS: Record<string, string> = { today: SERIES.usage, yesterday: SERIES.download, weeklyAverage: SERIES.usageAvg, monthlyAverage: SERIES.online }
const readings = computed(() => [...buckets.value].reverse().map((bucket, i) => ({ label: t(`dashboard.${bucket.key}`), value: bucket.value, color: themed(style.value, i, RING_COLORS[bucket.key]!) })))
const bytes = (value: number) => formatBytes(value, 1)

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
  <DashCard :title="t('dashboard.usageComparison')" :subtitle="t('dashboard.usageComparisonHint')" icon="pi pi-chart-line" :accent="SERIES.usageAvg" padded>
    <template #actions>
      <ChartViewSwitch v-model="view" :options="viewOptions" :label="t('dashboard.views.switch')" />
      <ChartStyleButton v-model="style" :types="view === 'bars' ? BAR_TYPES : []" :toggles="view === 'bars' ? ['grid'] : []" :accent="SERIES.usage" @reset="resetStyle" />
    </template>
    <Transition name="cv" mode="out-in">
      <ActivityRings v-if="view === 'rings'" key="rings" :items="readings" :format="bytes" />
      <RankedBars v-else-if="view === 'ranked'" key="ranked" :items="readings" :color="themed(style, 0, SERIES.usage)" :format="bytes" />
      <MetricChart
        v-else
        key="bars"
        :labels="labels"
        :series="chartSeries"
        type="bar"
        :chart-style="style"
        :stacked="stacked && stackedSeries.length > 1"
        :value-formatter="(value: number) => formatBytes(value, 0)"
        :height="216"
        :legend="stacked && stackedSeries.length > 1"
        :max-x-ticks="4"
      />
    </Transition>
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
