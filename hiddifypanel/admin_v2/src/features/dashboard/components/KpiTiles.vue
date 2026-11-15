<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsage, DashboardUsers } from '@/core/api/generated'
import { formatBytes, formatCount, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import StatTile, { type TileComparison, type TileDetail } from './StatTile.vue'
import ChartStyleButton from './ChartStyleButton.vue'
import { TILE_TYPES, themed, useChartStyle } from '../composables/useChartStyle'

const props = defineProps<{
  usage: DashboardUsage | null
  users: DashboardUsers | null
  series: DashboardDailyPoint[]
}>()

const { t, locale } = useI18n()

interface Tile {
  key: 'online' | 'today' | 'week' | 'month'
  comparison: TileComparison
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

/** Each tile's face (a small chart, a ring or a bar pair) and colour, chosen from its own small window */
const styles = {
  online: useChartStyle('kpi-online', { type: 'area' }, TILE_TYPES),
  today: useChartStyle('kpi-today', { type: 'area' }, TILE_TYPES),
  week: useChartStyle('kpi-week', { type: 'area' }, TILE_TYPES),
  month: useChartStyle('kpi-month', { type: 'area' }, TILE_TYPES),
}
const pair = (current: [string, number, string], previous: [string, number, string], caption: string): TileComparison => ({
  current: { label: current[0], amount: current[1], text: current[2] },
  previous: { label: previous[0], amount: previous[1], text: previous[2] },
  caption,
})

const usageSpark = computed(() => props.series.map((point) => point.usage))
const onlineSpark = computed(() => props.series.map((point) => point.online))
const sparkLabels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))

const tiles = computed<Tile[]>(() => [
  {
    key: 'online',
    comparison: pair(
      [t('dashboard.face.now'), props.users?.online.m5 ?? 0, formatCount(props.users?.online.m5 ?? 0)],
      [t('dashboard.face.active'), props.users?.active ?? 0, formatCount(props.users?.active ?? 0)],
      t('dashboard.face.ofActive'),
    ),
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
    key: 'today',
    comparison: pair(
      [t('dashboard.today'), props.usage?.totals.today ?? 0, formatBytes(props.usage?.totals.today ?? 0)],
      [t('dashboard.yesterday'), props.usage?.totals.yesterday ?? 0, formatBytes(props.usage?.totals.yesterday ?? 0)],
      t('dashboard.face.ofYesterday'),
    ),
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
    key: 'week',
    comparison: pair(
      [t('dashboard.face.thisWeek'), props.usage?.totals.week ?? 0, formatBytes(props.usage?.totals.week ?? 0)],
      [t('dashboard.face.lastWeek'), props.usage?.previous.week ?? 0, formatBytes(props.usage?.previous.week ?? 0)],
      t('dashboard.face.ofLastWeek'),
    ),
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
    key: 'month',
    comparison: pair(
      [t('dashboard.face.thisMonth'), props.usage?.totals.month ?? 0, formatBytes(props.usage?.totals.month ?? 0)],
      [t('dashboard.face.lastMonth'), props.usage?.previous.month ?? 0, formatBytes(props.usage?.previous.month ?? 0)],
      t('dashboard.face.ofLastMonth'),
    ),
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
      :accent="themed(styles[tile.key].value, 0, tile.accent)"
      :kind="styles[tile.key].value.type"
      :comparison="tile.comparison"
      :caption="tile.caption"
      :trend="tile.trend"
      :trend-label="tile.trendLabel"
      :details="tile.details"
      :sparkline="tile.sparkline"
      :spark-labels="tile.sparkLabels"
      :spark-formatter="tile.sparkFormatter"
    >
      <template #tools>
        <ChartStyleButton v-model="styles[tile.key].value" :types="TILE_TYPES" :toggles="[]" :accent="tile.accent" size="small" @reset="styles[tile.key].reset()" />
      </template>
    </StatTile>
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
