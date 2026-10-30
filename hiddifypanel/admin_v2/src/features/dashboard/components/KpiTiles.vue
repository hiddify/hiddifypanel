<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsage, DashboardUsers } from '@/core/api/generated'
import { formatBytes, formatCount, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import StatTile, { type TileDetail } from './StatTile.vue'

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
  /** The numbers behind the tile, shown on hover as label / value rows */
  details?: TileDetail[]
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
    value: `${props.users?.online.m5 ?? 0} / ${props.users?.active ?? 0}`,
    icon: 'pi pi-users',
    accent: SERIES.online,
    caption: t('dashboard.inFiveMinutes'),
    details: [
      { label: t('dashboard.onlineNow'), value: formatCount(props.users?.online.m5 ?? 0), main: true },
      { label: t('dashboard.today'), value: formatCount(props.users?.online.today ?? 0) },
      { label: t('dashboard.yesterday'), value: formatCount(props.users?.online.yesterday ?? 0) },
      { label: t('dashboard.weekUsers'), value: formatCount(props.users?.online.week ?? 0) },
      { label: t('dashboard.monthUsers'), value: formatCount(props.users?.online.month ?? 0) },
    ],
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
    caption: t('dashboard.onlineToday', { count: props.users?.online.today ?? 0, total: props.users?.active ?? 0 }),
    details: [
      { label: t('dashboard.today'), value: formatBytes(props.usage?.totals.today ?? 0), main: true },
      { label: t('dashboard.yesterday'), value: formatBytes(props.usage?.totals.yesterday ?? 0) },
      { label: t('dashboard.todayOnline'), value: `${formatCount(props.users?.online.today ?? 0)} / ${formatCount(props.users?.active ?? 0)}` },
    ],
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
    details: [
      { label: t('dashboard.tip.last7Days'), value: formatBytes(props.usage?.totals.week ?? 0), main: true },
      { label: t('dashboard.tip.previous7Days'), value: formatBytes(props.usage?.previous.week ?? 0) },
      { label: t('dashboard.tip.dailyAverage'), value: t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_week ?? 0) }) },
    ],
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
    details: [
      { label: t('dashboard.tip.last30Days'), value: formatBytes(props.usage?.totals.month ?? 0), main: true },
      { label: t('dashboard.tip.previous30Days'), value: formatBytes(props.usage?.previous.month ?? 0) },
      { label: t('dashboard.tip.dailyAverage'), value: t('dashboard.perDay', { value: formatBytes(props.usage?.averages.daily_month ?? 0) }) },
    ],
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
      :details="tile.details"
      :sparkline="tile.sparkline"
      :spark-labels="tile.sparkLabels"
      :spark-formatter="tile.sparkFormatter"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}
@container dashboard (min-width: 52rem) {
  .kpi-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
  }
}
@container dashboard (max-width: 20rem) {
  .kpi-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
