<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardMemory, DashboardProcess } from '@/core/api/generated'
import { formatGb, formatPercent } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import type { MetricSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import MetricBar from './MetricBar.vue'
import MetricChart from './MetricChart.vue'
import ProcessTable from './ProcessTable.vue'
import ResourceCard from './ResourceCard.vue'

const props = defineProps<{
  memory: DashboardMemory | null
  processes: DashboardProcess[]
  samples: MetricSample[]
}>()

const { t, locale } = useI18n()

const percent = computed(() => props.memory?.percent ?? 0)
const sparkline = computed(() => props.samples.map((sample) => sample.memory))

const headline = computed(() =>
  props.memory ? `${formatGb(props.memory.used_gb, 1)} / ${formatGb(props.memory.total_gb, 1)}` : '—',
)

const caption = computed(() => {
  if (!props.memory) return undefined
  return `${t('dashboard.available')} ${formatGb(props.memory.available_gb, 1)} · ${t('dashboard.cached')} ${formatGb(props.memory.cached_gb, 1)}`
})

const chartSeries = computed(() => [
  { label: t('dashboard.ram'), values: sparkline.value, color: SERIES.memory, type: 'line' as const, area: true },
])

const breakdown = computed(() => {
  const memory = props.memory
  if (!memory) return []
  return [
    { label: t('dashboard.used'), percent: memory.percent, value: formatGb(memory.used_gb, 1), color: SERIES.memory },
    {
      label: t('dashboard.cached'),
      percent: memory.total_gb ? (memory.cached_gb / memory.total_gb) * 100 : 0,
      value: formatGb(memory.cached_gb, 1),
      color: SERIES.users,
    },
    {
      label: t('dashboard.available'),
      percent: memory.total_gb ? (memory.available_gb / memory.total_gb) * 100 : 0,
      value: formatGb(memory.available_gb, 1),
      color: SERIES.online,
    },
    {
      label: t('dashboard.swap'),
      percent: memory.swap_percent,
      value: memory.swap_total_gb
        ? `${formatGb(memory.swap_used_gb, 1)} / ${formatGb(memory.swap_total_gb, 1)}`
        : t('dashboard.none'),
      color: SERIES.usageAvg,
    },
  ]
})
</script>

<template>
  <ResourceCard
    :title="t('dashboard.ram')"
    icon="pi pi-server"
    :accent="SERIES.memory"
    :percent="percent"
    :value="headline"
    :caption="caption"
    :sparkline="sparkline"
  >
    <template #detail>
      <div class="ram-detail">
        <MetricChart
          :labels="timeLabels(samples.map((sample) => sample.at), locale)"
          :series="chartSeries"
          type="line"
          :value-formatter="(value: number) => formatPercent(value)"
          :y-max="100"
          :height="150"
          :legend="false"
          :max-x-ticks="5"
        />

        <div class="ram-detail__section">
          <p class="ram-detail__heading">{{ t('dashboard.breakdown') }}</p>
          <div class="ram-detail__grid">
            <MetricBar
              v-for="row in breakdown"
              :key="row.label"
              :label="row.label"
              :percent="row.percent"
              :value="row.value"
              :color="row.color"
              compact
            />
          </div>
        </div>

        <div class="ram-detail__section">
          <p class="ram-detail__heading">{{ t('dashboard.topProcesses') }}</p>
          <ProcessTable
            :processes="processes"
            :color="SERIES.memory"
            :formatter="(process) => formatGb(process.memory_gb ?? 0, 2)"
          />
        </div>
      </div>
    </template>
  </ResourceCard>
</template>

<style scoped>
.ram-detail {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.ram-detail__section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ram-detail__heading {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.ram-detail__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.5rem 1rem;
}
</style>
