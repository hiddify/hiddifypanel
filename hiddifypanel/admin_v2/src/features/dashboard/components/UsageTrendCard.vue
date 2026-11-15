<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardUsage } from '@/core/api/generated'
import { formatBytes, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'
import { dashboardNodeName } from '../utils/node-name'
import ChartViewSwitch from './ChartViewSwitch.vue'
import HeatmapCalendar from './views/HeatmapCalendar.vue'
import WeekdayRhythm from './views/WeekdayRhythm.vue'
import { useChartView } from '../composables/useChartView'
import ChartStyleButton from './ChartStyleButton.vue'
import { CHART_TYPES, themed, useChartStyle } from '../composables/useChartStyle'

const props = defineProps<{
  series: DashboardDailyPoint[]
  usage: DashboardUsage | null
  rangeDays: number
  /** The chosen period in words ("Last 30 days", "Nov 10 – Nov 12") */
  periodLabel?: string
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

/** What is shown: the daily trend, the running total, a calendar, or the week's rhythm; how the trend and the total
 *  are drawn (columns, lines, candles…) is the style sheet's choice */
const VIEWS = ['trend', 'cumulative', 'calendar', 'rhythm'] as const
const view = useChartView('usage-trend', VIEWS)
const viewOptions = computed(() => [
  { value: 'trend', icon: 'pi pi-chart-bar', label: t('dashboard.views.trend') },
  { value: 'cumulative', icon: 'pi pi-chart-line', label: t('dashboard.views.cumulative') },
  { value: 'calendar', icon: 'pi pi-calendar', label: t('dashboard.views.calendar') },
  { value: 'rhythm', icon: 'pi pi-clock', label: t('dashboard.views.rhythm') },
])
const style = useChartStyle('usage-trend', { type: 'column', average: true })
const resetStyle = style.reset
const charted = computed(() => view.value === 'trend' || view.value === 'cumulative')
const color = computed(() => themed(style.value, 0, SERIES.usage))
const perNode = computed(() => props.stacked && stackedSeries.value.length > 1)
const points = computed(() => props.series.map((point) => ({ date: point.date, value: point.usage })))
const cumulative = computed(() => {
  let sum = 0
  return values.value.map((value) => (sum += value))
})

const chartSeries = computed(() => {
  if (view.value === 'cumulative') return [{ label: t('dashboard.views.cumulative'), values: cumulative.value, color: SERIES.usage, type: 'line' as const, area: true }]
  if (perNode.value) return stackedSeries.value
  return [{ label: t('dashboard.dailyUsage'), values: values.value, color: SERIES.usage, type: 'bar' as const }]
})

/** The busiest day of the shown period (the API's own peak covers the days it sent, more than the period) */
const peakPoint = computed(() => props.series.reduce<DashboardDailyPoint | undefined>((best, point) => (!best || point.usage > best.usage ? point : best), undefined))
const peakLabel = computed(() => (peakPoint.value && peakPoint.value.usage > 0 ? formatBytes(peakPoint.value.usage) : t('dashboard.noData')))
const peakDay = computed(() => (peakPoint.value && peakPoint.value.usage > 0 ? formatDayLabel(peakPoint.value.date, locale.value) : undefined))
</script>

<template>
  <DashCard
    :title="t('dashboard.usageTrend')"
    :subtitle="perNode && view === 'trend' ? t('dashboard.usageStackedHint') : (periodLabel ?? t('dashboard.lastNDays', { days: rangeDays }))"
    icon="pi pi-chart-bar"
    :accent="SERIES.usage"
    padded
  >
    <template #actions>
      <ChartViewSwitch v-model="view" :options="viewOptions" :label="t('dashboard.views.switch')" />
      <ChartStyleButton v-model="style" :types="charted ? CHART_TYPES : []" :toggles="charted ? ['grid', 'average'] : []" :accent="SERIES.usage" @reset="resetStyle" />
    </template>
    <Transition name="cv" mode="out-in">
      <HeatmapCalendar
        v-if="view === 'calendar'"
        key="calendar"
        :points="points"
        :color="color"
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
        :color="color"
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
        :chart-style="style"
        :stacked="perNode && view !== 'cumulative'"
        :value-formatter="(value: number) => formatBytes(value, 0)"
        :height="280"
        :max-x-ticks="rangeDays > 60 ? 8 : 12"
        :stack-total-label="t('dashboard.totalUsage')"
        :tooltip-extra="
          (index: number) => {
            const point = series[index]
            if (!point) return []
            return [t('dashboard.onlineOnDay', { count: point.online })]
          }
        "
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
