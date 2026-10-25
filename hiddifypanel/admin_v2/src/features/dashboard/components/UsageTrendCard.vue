<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardNode, DashboardNodeStats, DashboardUsage } from '@/core/api/generated'
import { formatBytes, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import { rollingAverage } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'

const props = defineProps<{
  series: DashboardDailyPoint[]
  usage: DashboardUsage | null
  rangeDays: number
  nodes: DashboardNode[]
  stacked: boolean
  /** The server shown (the chosen node, else the panel itself): its CPU and RAM right now, next to the usage. */
  health?: DashboardNodeStats | null
}>()

const { t, locale } = useI18n()

const labels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))
const values = computed(() => props.series.map((point) => point.usage))

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
    values: props.series.map((point) => point.by_child?.[id]?.usage ?? 0),
    color: nodeColor(Number(id)),
    type: 'line' as const,
    area: true,
  }))
})

const chartSeries = computed(() => {
  if (props.stacked && stackedSeries.value.length > 1) return stackedSeries.value
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

const cpuLabel = computed(() => {
  const cpu = props.health?.cpu
  return cpu ? `${Math.round(cpu.percent)}%` : '—'
})
const cpuTitle = computed(() => {
  const cpu = props.health?.cpu
  return cpu?.cores ? t('dashboard.cpuCores', { count: cpu.cores }) : t('dashboard.cpu')
})
const ramLabel = computed(() => {
  const mem = props.health?.memory
  return mem ? `${Math.round(mem.percent)}%` : '—'
})
const ramExtra = computed(() => {
  const mem = props.health?.memory
  return mem ? `${mem.used_gb.toFixed(1)} / ${mem.total_gb.toFixed(1)} GB` : undefined
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
    :subtitle="stacked && stackedSeries.length > 1 ? t('dashboard.usageStackedHint') : t('dashboard.lastNDays', { days: rangeDays })"
    icon="pi pi-chart-bar"
    :accent="SERIES.usage"
    padded
  >
    <MetricChart
      :labels="labels"
      :series="chartSeries"
      :type="stacked && stackedSeries.length > 1 ? 'line' : 'bar'"
      :stacked="stacked && stackedSeries.length > 1"
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
    <template #footer>
      <div class="usage-footer">
        <MiniStat :label="t('dashboard.totalUsage')" :value="formatBytes(usage?.totals.total ?? 0)" icon="pi pi-database" :accent="SERIES.usage" />
        <MiniStat :label="t('dashboard.monthUsage')" :value="formatBytes(usage?.totals.month ?? 0)" icon="pi pi-calendar" :accent="SERIES.users" />
        <MiniStat :label="t('dashboard.weekUsage')" :value="formatBytes(usage?.totals.week ?? 0)" icon="pi pi-calendar-clock" :accent="SERIES.download" />
        <MiniStat :label="t('dashboard.peakDay')" :value="peakLabel" :extra="peakDay" icon="pi pi-bolt" :accent="SERIES.usageAvg" />
        <MiniStat v-if="health" :label="cpuTitle" :value="cpuLabel" icon="pi pi-microchip" :accent="SERIES.users" />
        <MiniStat v-if="health" :label="t('dashboard.ram')" :value="ramLabel" :extra="ramExtra" icon="pi pi-server" :accent="SERIES.download" />
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
