<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardUsers } from '@/core/api/generated'
import { formatDayLabel, formatBytes } from '@/shared/utils/format-metrics'
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
  users: DashboardUsers | null
  rangeDays: number
  nodes: DashboardNode[]
  stacked: boolean
}>()

const { t, locale } = useI18n()

const labels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))
const values = computed(() => props.series.map((point) => point.online))

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
    values: props.series.map((point) => point.by_child?.[id]?.online ?? 0),
    color: nodeColor(Number(id)),
    type: 'line' as const,
    area: true,
  }))
})

/** How the trend is shown: smooth areas (with the 7-day average), daily bars, a calendar, or the week's rhythm */
const VIEWS = ['area', 'bars', 'calendar', 'rhythm'] as const
const view = useChartView('users-trend', VIEWS)
const viewOptions = computed(() => [
  { value: 'area', icon: 'pi pi-wave-pulse', label: t('dashboard.views.area') },
  { value: 'bars', icon: 'pi pi-chart-bar', label: t('dashboard.views.bars') },
  { value: 'calendar', icon: 'pi pi-calendar', label: t('dashboard.views.calendar') },
  { value: 'rhythm', icon: 'pi pi-clock', label: t('dashboard.views.rhythm') },
])
const perNode = computed(() => props.stacked && stackedSeries.value.length > 1)
const points = computed(() => props.series.map((point) => ({ date: point.date, value: point.online })))
const countText = (value: number) => String(Math.round(value))

const chartSeries = computed(() => {
  if (perNode.value) return stackedSeries.value.map((s) => (view.value === 'bars' ? { ...s, type: 'bar' as const, area: false } : s))
  if (view.value === 'bars')
    return [
      { label: t('dashboard.dailyOnline'), values: values.value, color: SERIES.users, type: 'bar' as const },
      { label: t('dashboard.rollingAverage'), values: rollingAverage(values.value, 7), color: SERIES.online, type: 'line' as const, dashed: true },
    ]
  return [
    { label: t('dashboard.dailyOnline'), values: values.value, color: SERIES.users, type: 'line' as const, area: true },
    {
      label: t('dashboard.rollingAverage'),
      values: rollingAverage(values.value, 7),
      color: SERIES.online,
      type: 'line' as const,
      dashed: true,
    },
  ]
})
</script>

<template>
  <DashCard
    :title="t('dashboard.usersTrend')"
    :subtitle="perNode && (view === 'area' || view === 'bars') ? t('dashboard.usageStackedHint') : t('dashboard.lastNDays', { days: rangeDays })"
    icon="pi pi-users"
    :accent="SERIES.users"
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
        :color="SERIES.users"
        :format="countText"
        :locale="locale"
        :peak-label="t('dashboard.views.busiestDay')"
        :less-label="t('dashboard.views.less')"
        :more-label="t('dashboard.views.more')"
      />
      <WeekdayRhythm
        v-else-if="view === 'rhythm'"
        key="rhythm"
        :points="points"
        :color="SERIES.users"
        :format="(value: number) => value.toFixed(1)"
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
        :stacked="perNode"
        :stack-total-label="t('dashboard.onlineUsers')"
        :value-formatter="countText"
        :height="280"
        :max-x-ticks="rangeDays > 60 ? 8 : 12"
        :tooltip-extra="(index: number) => {
          const point = series[index]
          if (!point) return []
          return [t('dashboard.usageOnDay', { value: formatBytes(point.usage) })]
        }"
      />
    </Transition>
    <template #footer>
      <div class="users-footer">
        <MiniStat
          :label="t('dashboard.onlineEnabledUsers')"
          :value="`${users?.online.m5 ?? 0}/${users?.active ?? 0}`"
          icon="pi pi-id-card"
          :accent="SERIES.users"
        />
        <MiniStat
          :label="t('dashboard.todayOnline')"
          :value="String(users?.online.today ?? 0)"
          icon="pi pi-check-circle"
          :accent="SERIES.online"
        />
        <MiniStat
          :label="t('dashboard.lastdayOnline')"
          :value="String(users?.online.yesterday ?? 0)"
          icon="pi pi-calendar-minus"
          :accent="SERIES.usageAvg"
        />
        <MiniStat
          :label="t('dashboard.weeklyOnline')"
          :value="String(users?.online.week ?? 0)"
          icon="pi pi-calendar-clock"
          :accent="SERIES.usageAvg"
        />
        <MiniStat
          :label="t('dashboard.monthlyOnline')"
          :value="String(users?.online.month ?? 0)"
          icon="pi pi-calendar"
          :accent="SERIES.download"
        />
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.users-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.75rem 1.25rem;
}
</style>
