<script setup lang="ts">
/**
 * The four tiles over the dashboard. Online users is live (the last five minutes); the other three follow the chosen
 * period: its usage (against the period of the same length before it), its daily average (against its last day) and
 * its busiest day. Each tile names what it covers.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsers } from '@/core/api/generated'
import { formatBytes, formatCount, formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import StatTile, { type TileComparison, type TileDetail } from './StatTile.vue'
import ChartStyleButton from './ChartStyleButton.vue'
import { TILE_TYPES, themed, useChartStyle } from '../composables/useChartStyle'
import { rollingAverage } from '../utils/series'

const props = defineProps<{
  users: DashboardUsers | null
  series: DashboardDailyPoint[]
  /** The period of the same length before (null: out of the API's year) */
  previousSeries: DashboardDailyPoint[] | null
  /** The chosen period in words: "Last 30 Days", "Nov 10 – Nov 12" */
  periodLabel: string
}>()

const { t, locale } = useI18n()

type Key = 'online' | 'usage' | 'average' | 'peak'
interface Tile {
  key: Key
  comparison: TileComparison
  label: string
  /** What the tile covers: the period, or "Live" */
  scope: string
  live?: boolean
  value: string
  icon: string
  accent: string
  caption?: string
  trend?: number | null
  trendLabel?: string
  details?: TileDetail[]
  sparkline: number[]
  sparkLabels: string[]
  sparkFormatter: (value: number) => string
}

/** Each tile's face (a small chart, a ring or a bar pair) and colour, chosen from its own small window */
const styles = {
  online: useChartStyle('kpi-online', { type: 'area' }, TILE_TYPES),
  usage: useChartStyle('kpi-usage', { type: 'area' }, TILE_TYPES),
  average: useChartStyle('kpi-average', { type: 'line' }, TILE_TYPES),
  peak: useChartStyle('kpi-peak', { type: 'column' }, TILE_TYPES),
}
const pair = (current: [string, number, string], previous: [string, number, string], caption: string): TileComparison => ({
  current: { label: current[0], amount: current[1], text: current[2] },
  previous: { label: previous[0], amount: previous[1], text: previous[2] },
  caption,
})
const change = (now: number, before: number) => (before > 0 ? Math.round(((now - before) / before) * 1000) / 10 : null)
const bytes = (value: number) => formatBytes(value)

const usageSpark = computed(() => props.series.map((point) => point.usage))
const sparkLabels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))
const days = computed(() => Math.max(1, props.series.length))
const total = computed(() => usageSpark.value.reduce((a, b) => a + b, 0))
const previousTotal = computed(() => (props.previousSeries ? props.previousSeries.reduce((a, point) => a + point.usage, 0) : null))
const average = computed(() => total.value / days.value)
const lastDay = computed(() => props.series[props.series.length - 1])
const peak = computed(() => props.series.reduce<DashboardDailyPoint | undefined>((best, point) => (!best || point.usage > best.usage ? point : best), undefined))
const onlineAverage = computed(() => props.series.reduce((a, point) => a + point.online, 0) / days.value)

const tiles = computed<Tile[]>(() => [
  {
    key: 'online',
    scope: t('dashboard.kpi.live'),
    live: true,
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
      { label: t('dashboard.kpi.onlineAverage', { period: props.periodLabel }), value: onlineAverage.value.toFixed(1) },
    ],
    sparkline: props.series.map((point) => point.online),
    sparkLabels: sparkLabels.value,
    sparkFormatter: (value: number) => String(Math.round(value)),
  },
  {
    key: 'usage',
    scope: props.periodLabel,
    comparison: pair(
      [t('dashboard.face.period'), total.value, bytes(total.value)],
      [t('dashboard.face.before'), previousTotal.value ?? 0, previousTotal.value === null ? '—' : bytes(previousTotal.value)],
      t('dashboard.face.ofPrevious'),
    ),
    label: t('dashboard.kpi.usage'),
    value: bytes(total.value),
    icon: 'pi pi-chart-bar',
    accent: SERIES.usage,
    trend: previousTotal.value === null ? null : change(total.value, previousTotal.value),
    trendLabel: t('dashboard.kpi.vsPreviousPeriod'),
    caption: previousTotal.value === null ? t('dashboard.kpi.noPrevious') : undefined,
    details: [
      { label: t('dashboard.kpi.thisPeriod'), value: bytes(total.value), main: true },
      { label: t('dashboard.kpi.previousPeriod'), value: previousTotal.value === null ? '—' : bytes(previousTotal.value) },
      { label: t('dashboard.kpi.days'), value: String(props.series.length) },
    ],
    sparkline: usageSpark.value,
    sparkLabels: sparkLabels.value,
    sparkFormatter: bytes,
  },
  {
    key: 'average',
    scope: props.periodLabel,
    comparison: pair([t('dashboard.face.lastDay'), lastDay.value?.usage ?? 0, bytes(lastDay.value?.usage ?? 0)], [t('dashboard.face.average'), average.value, bytes(average.value)], t('dashboard.face.ofAverage')),
    label: t('dashboard.kpi.dailyAverage'),
    value: bytes(average.value),
    icon: 'pi pi-wave-pulse',
    accent: SERIES.download,
    trend: lastDay.value ? change(lastDay.value.usage, average.value) : null,
    trendLabel: t('dashboard.kpi.lastDayVsAverage'),
    details: [
      { label: t('dashboard.kpi.dailyAverage'), value: bytes(average.value), main: true },
      { label: t('dashboard.kpi.lastDay'), value: bytes(lastDay.value?.usage ?? 0) },
      { label: t('dashboard.kpi.thisPeriod'), value: bytes(total.value) },
    ],
    sparkline: rollingAverage(usageSpark.value, 7),
    sparkLabels: sparkLabels.value,
    sparkFormatter: bytes,
  },
  {
    key: 'peak',
    scope: props.periodLabel,
    comparison: pair([t('dashboard.face.peak'), peak.value?.usage ?? 0, bytes(peak.value?.usage ?? 0)], [t('dashboard.face.average'), average.value, bytes(average.value)], t('dashboard.face.ofAverage')),
    label: t('dashboard.kpi.busiestDay'),
    value: peak.value && peak.value.usage > 0 ? bytes(peak.value.usage) : '—',
    icon: 'pi pi-bolt',
    accent: SERIES.usageAvg,
    caption: peak.value && peak.value.usage > 0 ? formatDayLabel(peak.value.date, locale.value) : t('dashboard.noData'),
    details: [
      { label: t('dashboard.kpi.busiestDay'), value: peak.value ? bytes(peak.value.usage) : '—', main: true },
      { label: t('dashboard.kpi.on'), value: peak.value ? formatDayLabel(peak.value.date, locale.value) : '—' },
      { label: t('dashboard.kpi.dailyAverage'), value: bytes(average.value) },
    ],
    sparkline: usageSpark.value,
    sparkLabels: sparkLabels.value,
    sparkFormatter: bytes,
  },
])
</script>

<template>
  <div class="kpi-grid">
    <StatTile
      v-for="tile in tiles"
      :key="tile.label"
      :label="tile.label"
      :scope="tile.scope"
      :live="tile.live"
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
