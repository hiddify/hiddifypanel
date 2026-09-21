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
  if (numeric === 0) return t('dashboard.thisServer')
  return props.nodes.find((node) => node.id === numeric)?.name || `${t('dashboard.node')} ${id}`
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

const chartSeries = computed(() => {
  if (props.stacked && stackedSeries.value.length > 1) return stackedSeries.value
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
    :subtitle="stacked && stackedSeries.length > 1 ? t('dashboard.usageStackedHint') : t('dashboard.lastNDays', { days: rangeDays })"
    icon="pi pi-users"
    :accent="SERIES.users"
    padded
  >
    <MetricChart
      :labels="labels"
      :series="chartSeries"
      type="line"
      :stacked="stacked && stackedSeries.length > 1"
      :stack-total-label="t('dashboard.onlineUsers')"
      :value-formatter="(value: number) => String(Math.round(value))"
      :height="280"
      :max-x-ticks="rangeDays > 60 ? 8 : 12"
      :tooltip-extra="(index: number) => {
        const point = series[index]
        if (!point) return []
        return [t('dashboard.usageOnDay', { value: formatBytes(point.usage) })]
      }"
    />
    <template #footer>
      <div class="users-footer">
        <MiniStat
          :label="t('dashboard.onlineEnabledUsers')"
          :value="`${users?.online.m5 ?? 0}/${users?.enabled ?? 0}`"
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
