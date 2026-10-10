<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import SelectButton from 'primevue/selectbutton'
import type { DashboardDailyPoint, DashboardNode, DashboardUsers } from '@/core/api/generated'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import ResourceGauge from './ResourceGauge.vue'

const props = defineProps<{
  users: DashboardUsers | null
  series: DashboardDailyPoint[]
  nodes: DashboardNode[]
  stacked: boolean
}>()

const { t } = useI18n()

/**
 * One card, three readings of the same users:
 * unique = distinct users seen in the period (whole panel); average = users online per active day;
 * peak = the most users online in a single day. Average and peak split by server.
 */
type Mode = 'unique' | 'average' | 'peak'
const MODE_KEY = 'hiddify.dashboard.usersMode'
const MODES: Mode[] = ['unique', 'average', 'peak']

/** The reading you picked last time (browser storage), else the distinct users. */
function savedMode(): Mode {
  try {
    const value = localStorage.getItem(MODE_KEY) as Mode | null
    return value && MODES.includes(value) ? value : 'unique'
  } catch {
    return 'unique' // storage blocked
  }
}
const mode = ref<Mode>(savedMode())
watch(mode, (value) => {
  try {
    localStorage.setItem(MODE_KEY, value)
  } catch {
    /* storage blocked: not remembered */
  }
})
const modeOptions = computed(() => [
  { value: 'unique' as Mode, icon: 'pi pi-users', label: t('dashboard.modeUnique') },
  { value: 'average' as Mode, icon: 'pi pi-wave-pulse', label: t('dashboard.modeAverage') },
  { value: 'peak' as Mode, icon: 'pi pi-arrow-up-right', label: t('dashboard.modePeak') },
])
const modeHint = computed(() => t(`dashboard.${mode.value}Hint`))

const nodeName = (id: string) => {
  const numeric = Number(id)
  if (numeric === 0) return t('dashboard.thisServer')
  return props.nodes.find((node) => node.id === numeric)?.name || `${t('dashboard.node')} ${id}`
}

const nodeIds = computed(() => {
  const ids = new Set<string>()
  for (const point of props.series) for (const id of Object.keys(point.by_child ?? {})) ids.add(id)
  return [...ids].sort((a, b) => Number(a) - Number(b))
})
const perNode = computed(() => props.stacked && nodeIds.value.length > 1 && mode.value !== 'unique')

/** Month, week, yesterday, today for one node (or all): average over days with someone online, or the best day. */
function row(value: (point: DashboardDailyPoint) => number): number[] {
  const points = props.series
  const last = points.length - 1
  const window = (days: number) => points.slice(-days).map(value)
  const aggregate = (days: number) => {
    const values = window(days)
    if (mode.value === 'peak') return values.reduce((best, v) => Math.max(best, v), 0)
    const active = values.filter((v) => v > 0)
    return active.length ? active.reduce((sum, v) => sum + v, 0) / active.length : 0
  }
  return [aggregate(30), aggregate(7), last > 0 ? value(points[last - 1]!) : 0, last >= 0 ? value(points[last]!) : 0]
}

const dayLabels = computed(() => [t('dashboard.monthUsers'), t('dashboard.weekUsers'), t('dashboard.yesterday'), t('dashboard.today')])
const uniqueBuckets = computed(() => [
  { label: t('dashboard.monthUsers'), value: props.users?.online.month ?? 0 },
  { label: t('dashboard.weekUsers'), value: props.users?.online.week ?? 0 },
  { label: t('dashboard.yesterday'), value: props.users?.online.yesterday ?? 0 },
  { label: t('dashboard.today'), value: props.users?.online.today ?? 0 },
  { label: t('dashboard.onlineNow'), value: props.users?.online.m5 ?? 0 },
])

const labels = computed(() => (mode.value === 'unique' ? uniqueBuckets.value.map((b) => b.label) : dayLabels.value))

const chartSeries = computed(() => {
  if (mode.value === 'unique') {
    return [{ label: t('dashboard.onlineUsers'), values: uniqueBuckets.value.map((b) => b.value), color: SERIES.online, type: 'bar' as const }]
  }
  if (perNode.value) {
    return nodeIds.value.map((id) => ({
      label: nodeName(id),
      values: row((point) => point.by_child?.[id]?.online ?? 0),
      color: nodeColor(Number(id)),
      type: 'bar' as const,
    }))
  }
  return [{ label: t('dashboard.onlineUsers'), values: row((point) => point.online), color: mode.value === 'peak' ? SERIES.users : SERIES.online, type: 'bar' as const }]
})

/** Averages can be fractional: show 1.4, not a rounded 1 next to a taller bar. */
function countText(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

const onlineShare = computed(() => {
  const total = props.users?.active ?? 0
  if (!total) return 0
  return ((props.users?.online.m5 ?? 0) / total) * 100
})
</script>

<template>
  <DashCard :title="t('dashboard.usersComparison')" :subtitle="modeHint" icon="pi pi-user-plus" :accent="SERIES.online" padded>
    <template #actions>
      <SelectButton v-model="mode" :options="modeOptions" option-label="label" option-value="value" :allow-empty="false" size="small" :aria-label="t('dashboard.usersComparison')">
        <template #option="{ option }">
          <span class="users-mode"><i :class="option.icon" />{{ option.label }}</span>
        </template>
      </SelectButton>
    </template>

    <div class="users-compare-wrap">
      <div class="users-compare">
        <div class="users-compare__gauge">
          <ResourceGauge
            :percent="onlineShare"
            :color="SERIES.online"
            :value="`${users?.online.m5 ?? 0}/${users?.active ?? 0}`"
            :caption="t('dashboard.onlineNow')"
            :auto-color="false"
            :size="110"
          />
          <p class="users-compare__hint">{{ t('dashboard.inFiveMinutes') }}</p>
        </div>
        <MetricChart
          class="users-compare__chart"
          :labels="labels"
          :series="chartSeries"
          type="bar"
          :stacked="perNode"
          :stack-total-label="t('dashboard.onlineUsers')"
          :value-formatter="countText"
          :height="216"
          :legend="perNode"
          :max-x-ticks="5"
        />
      </div>
      <!-- Distinct users behind the week and month, whichever reading is shown -->
      <div class="users-compare__totals">
        <span class="users-compare__total"><i class="pi pi-calendar" />{{ t('dashboard.uniqueWeek') }}<b>{{ users?.online.week ?? 0 }}</b></span>
        <span class="users-compare__total"><i class="pi pi-calendar-plus" />{{ t('dashboard.uniqueMonth') }}<b>{{ users?.online.month ?? 0 }}</b></span>
      </div>
    </div>
  </DashCard>
</template>

<style scoped>
.users-compare-wrap {
  container-type: inline-size;
}
.users-compare {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.users-compare__gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}
.users-compare__hint {
  margin: 0;
  font-size: 0.7rem;
  text-align: center;
  color: var(--p-text-muted-color);
}
.users-compare__chart {
  flex: 1;
  min-width: 0;
}
.users-mode {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
}
.users-compare__note {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.users-compare__note i {
  margin-top: 0.15rem;
}
.users-compare__totals {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1rem;
  margin-top: 0.6rem;
  padding-top: 0.6rem;
  border-top: 1px dashed var(--p-content-border-color);
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.users-compare__total {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.users-compare__total b {
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
@container (max-width: 30rem) {
  .users-compare {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
}
</style>
