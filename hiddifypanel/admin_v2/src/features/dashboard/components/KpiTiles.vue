<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsage, DashboardUsers } from '@/core/api/generated'
import { formatBytes, formatCount, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import StatTile from './StatTile.vue'

const props = defineProps<{
  usage: DashboardUsage | null
  users: DashboardUsers | null
  series: DashboardDailyPoint[]
}>()

const { t, locale } = useI18n()

interface Tile {
  label: string
  value: string
  icon: string
  accent: string
  caption?: string
  trend?: number | null
  trendLabel?: string
  tooltip?: string
  sparkline: number[]
  sparkLabels: string[]
  sparkFormatter: (value: number) => string
}

const usageSpark = computed(() => props.series.map((point) => point.usage))
const onlineSpark = computed(() => props.series.map((point) => point.online))
const sparkLabels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))

const tiles = computed<Tile[]>(() => [
  {
    label: t('dashboard.onlineUsers'),
    value: `${props.users?.online.m5 ?? 0} / ${props.users?.total ?? 0}`,
    icon: 'pi pi-users',
    accent: SERIES.online,
    caption: t('dashboard.inFiveMinutes'),
    tooltip: [
      `${t('dashboard.onlineNow')}: ${formatCount(props.users?.online.m5 ?? 0)}`,
      `${t('dashboard.today')}: ${formatCount(props.users?.online.today ?? 0)}`,
      `${t('dashboard.yesterday')}: ${formatCount(props.users?.online.yesterday ?? 0)}`,
      `${t('dashboard.weekUsers')}: ${formatCount(props.users?.online.week ?? 0)}`,
      `${t('dashboard.monthUsers')}: ${formatCount(props.users?.online.month ?? 0)}`,
    ].join('\n'),
    sparkline: onlineSpark.value.slice(-14),
    sparkLabels: sparkLabels.value.slice(-14),
    sparkFormatter: (value: number) => String(Math.round(value)),
  },
  {
    label: t('dashboard.todayUsage'),
    value: formatBytes(props.usage?.totals.today ?? 0),
    icon: 'pi pi-calendar',
    accent: SERIES.usage,
    trend: props.usage?.trends.day ?? null,
    trendLabel: t('dashboard.vsYesterday'),
    caption: t('dashboard.onlineToday', { count: props.users?.online.today ?? 0, total: props.users?.total ?? 0 }),
    tooltip: [
      `${t('dashboard.today')}: ${formatBytes(props.usage?.totals.today ?? 0)}`,
      `${t('dashboard.yesterday')}: ${formatBytes(props.usage?.totals.yesterday ?? 0)}`,
      t('dashboard.onlineToday', { count: props.users?.online.today ?? 0, total: props.users?.total ?? 0 }),
    ].join('\n'),
    sparkline: usageSpark.value.slice(-14),
    sparkLabels: sparkLabels.value.slice(-14),
    sparkFormatter: (value: number) => formatBytes(value),
  },
  {
    label: t('dashboard.weekUsage'),
    value: formatBytes(props.usage?.totals.week ?? 0),
    icon: 'pi pi-calendar-clock',
    accent: SERIES.download,
    trend: props.usage?.trends.week ?? null,
    trendLabel: t('dashboard.vsPreviousWeek'),
    caption: t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_week ?? 0) }),
    tooltip: [
      `${t('dashboard.weekUsage')}: ${formatBytes(props.usage?.totals.week ?? 0)}`,
      `${t('dashboard.vsPreviousWeek')}: ${formatBytes(props.usage?.previous.week ?? 0)}`,
      `${t('dashboard.weeklyAverage')}: ${t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_week ?? 0) })}`,
    ].join('\n'),
    sparkline: usageSpark.value.slice(-14),
    sparkLabels: sparkLabels.value.slice(-14),
    sparkFormatter: (value: number) => formatBytes(value),
  },
  {
    label: t('dashboard.monthUsage'),
    value: formatBytes(props.usage?.totals.month ?? 0),
    icon: 'pi pi-calendar-plus',
    accent: SERIES.users,
    trend: props.usage?.trends.month ?? null,
    trendLabel: t('dashboard.vsPreviousMonth'),
    caption: t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_month ?? 0) }),
    tooltip: [
      `${t('dashboard.monthUsage')}: ${formatBytes(props.usage?.totals.month ?? 0)}`,
      `${t('dashboard.vsPreviousMonth')}: ${formatBytes(props.usage?.previous.month ?? 0)}`,
      `${t('dashboard.monthlyAverage')}: ${t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_month ?? 0) })}`,
    ].join('\n'),
    sparkline: usageSpark.value.slice(-30),
    sparkLabels: sparkLabels.value.slice(-30),
    sparkFormatter: (value: number) => formatBytes(value),
  }
])
</script>

<template>
  <div class="kpi-grid">
    <StatTile
      v-for="tile in tiles"
      :key="tile.label"
      :label="tile.label"
      :value="tile.value"
      :icon="tile.icon"
      :accent="tile.accent"
      :caption="tile.caption"
      :trend="tile.trend"
      :trend-label="tile.trendLabel"
      :tooltip="tile.tooltip"
      :sparkline="tile.sparkline"
      :spark-labels="tile.sparkLabels"
      :spark-formatter="tile.sparkFormatter"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}
@media (max-width: 767px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }
}
</style>
