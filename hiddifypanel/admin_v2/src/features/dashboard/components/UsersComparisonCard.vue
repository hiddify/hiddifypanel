<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
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

const buckets = computed(() => [
  { key: 'monthUsers', value: props.users?.online.month ?? 0 },
  { key: 'weekUsers', value: props.users?.online.week ?? 0 },
  { key: 'yesterday', value: props.users?.online.yesterday ?? 0 },
  { key: 'today', value: props.users?.online.today ?? 0 },
  { key: 'onlineNow', value: props.users?.online.m5 ?? 0 },
])

/** `onlineNow` is a live snapshot, not tracked per node — only the daily buckets can stack. */
const stackedLabels = computed(() => buckets.value.slice(0, 4).map((bucket) => t(`dashboard.${bucket.key}`)))

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
  const points = props.series
  const last = points.length - 1
  const nodeOnline = (id: string, index: number) => points[index]?.by_child?.[id]?.online ?? 0
  const average = (id: string, days: number) => {
    const from = Math.max(0, points.length - days)
    const slice = points.slice(from)
    if (!slice.length) return 0
    return slice.reduce((sum, point) => sum + (point.by_child?.[id]?.online ?? 0), 0) / slice.length
  }
  return ordered.map((id) => ({
    label: nodeName(id),
    values: [average(id, 30), average(id, 7), nodeOnline(id, last - 1), nodeOnline(id, last)],
    color: nodeColor(Number(id)),
    type: 'bar' as const,
  }))
})

const labels = computed(() => (props.stacked && stackedSeries.value.length > 1 ? stackedLabels.value : buckets.value.map((bucket) => t(`dashboard.${bucket.key}`))))

const chartSeries = computed(() => {
  if (props.stacked && stackedSeries.value.length > 1) return stackedSeries.value
  return [
    {
      label: t('dashboard.onlineUsers'),
      values: buckets.value.map((bucket) => bucket.value),
      color: SERIES.online,
      type: 'bar' as const,
    },
  ]
})

const onlineShare = computed(() => {
  const total = props.users?.total ?? 0
  if (!total) return 0
  return ((props.users?.online.m5 ?? 0) / total) * 100
})
</script>

<template>
  <DashCard
    :title="t('dashboard.usersComparison')"
    :subtitle="t('dashboard.usersComparisonHint')"
    icon="pi pi-user-plus"
    :accent="SERIES.online"
    padded
  >
    <div class="users-compare">
      <div class="users-compare__gauge">
        <ResourceGauge
          :percent="onlineShare"
          :color="SERIES.online"
          :value="`${users?.online.m5 ?? 0}/${users?.total ?? 0}`"
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
        :stacked="stacked && stackedSeries.length > 1"
        :value-formatter="(value: number) => String(Math.round(value))"
        :height="216"
        :legend="stacked && stackedSeries.length > 1"
        :max-x-ticks="5"
      />
    </div>
  </DashCard>
</template>

<style scoped>
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
@media (max-width: 575px) {
  .users-compare {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
