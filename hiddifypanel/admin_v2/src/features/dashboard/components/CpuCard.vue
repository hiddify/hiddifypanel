<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardCpu, DashboardProcess } from '@/core/api/generated'
import { formatPercent } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import type { MetricSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import MetricBar from './MetricBar.vue'
import MetricChart from './MetricChart.vue'
import ProcessTable from './ProcessTable.vue'
import ResourceCard from './ResourceCard.vue'

const props = defineProps<{
  cpu: DashboardCpu | null
  processes: DashboardProcess[]
  samples: MetricSample[]
}>()

const { t, locale } = useI18n()

const percent = computed(() => props.cpu?.percent ?? 0)
const sparkline = computed(() => props.samples.map((sample) => sample.cpu))

const loadCaption = computed(() => {
  const load = props.cpu?.load_avg ?? []
  if (load.length < 3) return undefined
  return `${t('dashboard.loadAverage')} ${load[0]} · ${load[1]} · ${load[2]}`
})

const chartSeries = computed(() => [
  { label: t('dashboard.cpu'), values: sparkline.value, color: SERIES.cpu, type: 'line' as const, area: true },
])
</script>

<template>
  <ResourceCard
    :title="t('dashboard.cpuCores', { count: cpu?.cores ?? 0 })"
    icon="pi pi-microchip"
    :accent="SERIES.cpu"
    :percent="percent"
    :value="formatPercent(percent, 1)"
    :caption="loadCaption"
    :sparkline="sparkline"
  >
    <template #detail>
      <div class="cpu-detail">
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

        <div class="cpu-detail__section">
          <p class="cpu-detail__heading">{{ t('dashboard.perCore') }}</p>
          <div class="cpu-detail__cores">
            <MetricBar
              v-for="(core, index) in cpu?.per_core ?? []"
              :key="index"
              :label="t('dashboard.core', { index: index + 1 })"
              :percent="core"
              :color="SERIES.cpu"
              auto-color
              compact
            />
          </div>
        </div>

        <div class="cpu-detail__section">
          <p class="cpu-detail__heading">{{ t('dashboard.loadAverage') }}</p>
          <div class="cpu-detail__cores">
            <MetricBar
              v-for="(load, index) in cpu?.load_percent ?? []"
              :key="index"
              :label="[t('dashboard.load1m'), t('dashboard.load5m'), t('dashboard.load15m')][index] ?? ''"
              :percent="load"
              :value="formatPercent(load)"
              :color="SERIES.usageAvg"
              auto-color
              compact
            />
          </div>
        </div>

        <div class="cpu-detail__section">
          <p class="cpu-detail__heading">{{ t('dashboard.topProcesses') }}</p>
          <ProcessTable
            :processes="processes"
            :color="SERIES.cpu"
            :formatter="(process) => formatPercent(process.percent, 1)"
          />
        </div>
      </div>
    </template>
  </ResourceCard>
</template>

<style scoped>
.cpu-detail {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.cpu-detail__section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.cpu-detail__heading {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.cpu-detail__cores {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.5rem 1rem;
}
</style>
