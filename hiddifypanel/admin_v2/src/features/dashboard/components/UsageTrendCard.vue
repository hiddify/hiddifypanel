<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardUsage } from '@/core/api/generated'
import { formatBytes, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import { rollingAverage } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'
import { dashboardNodeName } from '../utils/node-name'
import ChartViewSwitch from './ChartViewSwitch.vue'
import HeatmapCalendar from './views/HeatmapCalendar.vue'
import WeekdayRhythm from './views/WeekdayRhythm.vue'
import { useChartView } from '../composables/useChartView'

const props = defineProps<{
  series: DashboardDailyPoint[]
  usage: DashboardUsage | null
  rangeDays: number
  nodes: DashboardNode[]
  stacked: boolean
}>()

const { t, locale } = useI18n()

const labels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))
const values = computed(() => props.series.map((point) => point.usage))

const nodeName = (id: string) => {
  const numeric = Number(id)
  const node = props.nodes.find((row) => row.id === numeric)
  if (numeric === 0) return dashboardNodeName(0, node?.name, t('dashboard.thisServer'))
  return node?.name || `${t('dashboard.node')} ${id}`
}

const stackedSeries = computed(() => {
  const ids = new Set<string>()
  for (const point of props.series) {
    for (const id of Object.keys(point.by_child ?? {})) ids.add(id)
  }
  const ordered = [...ids].sort((a, b) => Number(a) - Number(b))
  return ordered.map((id) => ({
    label: nodeName(id),
    values: props.series.map((point) => point.by_child?.[id]?.usage ?? 0),
    color: nodeColor(Number(id)),
    type: 'line' as const,
    area: true,
  }))
})

/** How the trend is shown: daily bars (with the 7-day average), smooth areas, the running total, a calendar, or the
 *  week's rhythm */
const VIEWS = ['bars', 'area', 'cumulative', 'calendar', 'rhythm'] as const
const view = useChartView('usage-trend', VIEWS)
const viewOptions = computed(() => [
  { value: 'bars', icon: 'pi pi-chart-bar', label: t('dashboard.views.bars') },
  { value: 'area', icon: 'pi pi-wave-pulse', label: t('dashboard.views.area') },
  { value: 'cumulative', icon: 'pi pi-chart-line', label: t('dashboard.views.cumulative') },
  { value: 'calendar', icon: 'pi pi-calendar', label: t('dashboard.views.calendar') },
  { value: 'rhythm', icon: 'pi pi-clock', label: t('dashboard.views.rhythm') },
])
const perNode = computed(() => props.stacked && stackedSeries.value.length > 1)
const points = computed(() => props.series.map((point) => ({ date: point.date, value: point.usage })))
const cumulative = computed(() => {
  let sum = 0
  return values.value.map((value) => (sum += value))
})

const chartSeries = computed(() => {
  if (view.value === 'cumulative') return [{ label: t('dashboard.views.cumulative'), values: cumulative.value, color: SERIES.usage, type: 'line' as const, area: true }]
  if (perNode.value) return stackedSeries.value.map((s) => (view.value === 'bars' ? { ...s, type: 'bar' as const, area: false } : s))
  if (view.value === 'area')
    return [
      { label: t('dashboard.dailyUsage'), values: values.value, color: SERIES.usage, type: 'line' as const, area: true },
      { label: t('dashboard.rollingAverage'), values: rollingAverage(values.value, 7), color: SERIES.usageAvg, type: 'line' as const, dashed: true },
    ]
  return [
    { label: t('dashboard.dailyUsage'), values: values.value, color: SERIES.usage, type: 'bar' as const },
    {
      label: t('dashboard.rollingAverage'),
      values: rollingAverage(values.value, 7),
      color: SERIES.usageAvg,
      type: 'line' as const,
      dashed: true,
    },
  ]
})

const peakLabel = computed(() => {
  const peak = props.usage?.peak
  return peak ? formatBytes(peak.usage) : t('dashboard.noData')
})
const peakDay = computed(() => {
  const peak = props.usage?.peak
  return peak ? formatDayLabel(peak.date, locale.value) : undefined
})
</script>

<template>
  <DashCard
    :title="t('dashboard.usageTrend')"
    :subtitle="perNode && view !== 'cumulative' && view !== 'calendar' && view !== 'rhythm' ? t('dashboard.usageStackedHint') : t('dashboard.lastNDays', { days: rangeDays })"
    icon="pi pi-chart-bar"
    :accent="SERIES.usage"
    padded
  >
    <template #actions>
      <ChartViewSwitch v-model="view" :options="viewOptions" :label="t('dashboard.views.switch')" />
    </template>
    <Transition name="cv" mode="out-in">
      <HeatmapCalendar
        v-if="view === 'calendar'"
        key="calendar"
        :points="points"
        :color="SERIES.usage"
        :format="(value: number) => formatBytes(value, 1)"
        :locale="locale"
        :peak-label="t('dashboard.views.busiestDay')"
        :less-label="t('dashboard.views.less')"
        :more-label="t('dashboard.views.more')"
      />
      <WeekdayRhythm
        v-else-if="view === 'rhythm'"
        key="rhythm"
        :points="points"
        :color="SERIES.usage"
        :format="(value: number) => formatBytes(value, 1)"
        :locale="locale"
        :busiest-label="t('dashboard.views.busiestWeekday')"
        :average-label="t('dashboard.views.average')"
      />
      <MetricChart
        v-else
        :key="view"
        :labels="labels"
        :series="chartSeries"
        :type="view === 'bars' ? 'bar' : 'line'"
        :stacked="perNode && view !== 'cumulative'"
        :value-formatter="(value: number) => formatBytes(value, 0)"
        :height="280"
        :max-x-ticks="rangeDays > 60 ? 8 : 12"
        :stack-total-label="t('dashboard.totalUsage')"
        :tooltip-extra="(index: number) => {
          const point = series[index]
          if (!point) return []
          return [t('dashboard.onlineOnDay', { count: point.online })]
        }"
      />
    </Transition>
    <template #footer>
      <div class="usage-footer">
        <MiniStat :label="t('dashboard.totalUsage')" :value="formatBytes(usage?.totals.total ?? 0)" icon="pi pi-database" :accent="SERIES.usage" />
        <MiniStat :label="t('dashboard.monthUsage')" :value="formatBytes(usage?.totals.month ?? 0)" icon="pi pi-calendar" :accent="SERIES.users" />
        <MiniStat :label="t('dashboard.weekUsage')" :value="formatBytes(usage?.totals.week ?? 0)" icon="pi pi-calendar-clock" :accent="SERIES.download" />
        <MiniStat :label="t('dashboard.peakDay')" :value="peakLabel" :extra="peakDay" icon="pi pi-bolt" :accent="SERIES.usageAvg" />
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.usage-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
  gap: 0.75rem 1.25rem;
}
</style>
