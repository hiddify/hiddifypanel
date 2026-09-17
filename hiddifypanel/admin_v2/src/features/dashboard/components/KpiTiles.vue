<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsage, DashboardUsers } from '@/core/api/generated'
import { formatBytes, formatDayLabel } from '@/shared/utils/format-metrics'
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
  sparkline: number[]
  sparkLabels: string[]
  sparkFormatter: (value: number) => string
}

const usageSpark = computed(() => props.series.map((point) => point.usage))
const onlineSpark = computed(() => props.series.map((point) => point.online))
const sparkLabels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))

const tiles = computed<Tile[]>(() => [
  {
    label: t('dashboard.todayUsage'),
    value: formatBytes(props.usage?.totals.today ?? 0),
    icon: 'pi pi-calendar',
    accent: SERIES.usage,
    trend: props.usage?.trends.day ?? null,
    trendLabel: t('dashboard.vsYesterday'),
    caption: t('dashboard.onlineToday', { count: props.users?.online.today ?? 0, total: props.users?.total ?? 0 }),
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
    sparkline: usageSpark.value.slice(-30),
    sparkLabels: sparkLabels.value.slice(-30),
    sparkFormatter: (value: number) => formatBytes(value),
  },
  {
    label: t('dashboard.totalUsage'),
    value: formatBytes(props.usage?.totals.total ?? 0),
    icon: 'pi pi-chart-pie',
    accent: SERIES.usageAvg,
    caption: t('dashboard.usersSummary', { total: props.users?.total ?? 0, enabled: props.users?.enabled ?? 0 }),
    sparkline: [],
    sparkLabels: [],
    sparkFormatter: (value: number) => formatBytes(value),
  },
  {
    label: t('dashboard.onlineUsers'),
    value: `${props.users?.online.m5 ?? 0} / ${props.users?.total ?? 0}`,
    icon: 'pi pi-users',
    accent: SERIES.online,
    caption: t('dashboard.inFiveMinutes'),
    sparkline: onlineSpark.value.slice(-14),
    sparkLabels: sparkLabels.value.slice(-14),
    sparkFormatter: (value: number) => String(Math.round(value)),
  },
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
      :sparkline="tile.sparkline"
      :spark-labels="tile.sparkLabels"
      :spark-formatter="tile.sparkFormatter"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1rem;
}
@media (max-width: 767px) {
  .kpi-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
