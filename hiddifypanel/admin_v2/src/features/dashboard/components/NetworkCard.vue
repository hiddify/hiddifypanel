<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardNetwork } from '@/core/api/generated'
import { formatBitRate, formatGb } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import type { MetricSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'

const props = defineProps<{
  network: DashboardNetwork | null
  samples: MetricSample[]
}>()

const { t, locale } = useI18n()

const chartSeries = computed(() => [
  {
    label: t('dashboard.upload'),
    values: props.samples.map((sample) => sample.up),
    color: SERIES.upload,
    type: 'line' as const,
    area: true,
  },
  {
    label: t('dashboard.download'),
    values: props.samples.map((sample) => sample.down),
    color: SERIES.download,
    type: 'line' as const,
    area: true,
  },
])

const latest = computed(() => props.samples[props.samples.length - 1] ?? null)
</script>

<template>
  <DashCard
    :title="t('dashboard.network')"
    :subtitle="t('dashboard.liveThroughput')"
    icon="pi pi-globe"
    :accent="SERIES.download"
    padded
  >
    <template #actions>
      <div class="net-rates">
        <span class="net-rate net-rate--up">
          <i class="pi pi-arrow-up" />{{ formatBitRate(latest?.up ?? 0) }}
        </span>
        <span class="net-rate net-rate--down">
          <i class="pi pi-arrow-down" />{{ formatBitRate(latest?.down ?? 0) }}
        </span>
      </div>
    </template>

    <MetricChart
      :labels="timeLabels(samples.map((sample) => sample.at), locale)"
      :series="chartSeries"
      type="line"
      :value-formatter="(value: number) => formatBitRate(value)"
      :height="190"
      :max-x-ticks="6"
    />

    <template #footer>
      <div class="net-footer">
        <MiniStat
          :label="t('dashboard.sentSinceRestart')"
          :value="formatGb(network?.sent_gb ?? 0, 1)"
          icon="pi pi-arrow-up"
          :accent="SERIES.upload"
        />
        <MiniStat
          :label="t('dashboard.receivedSinceRestart')"
          :value="formatGb(network?.recv_gb ?? 0, 1)"
          icon="pi pi-arrow-down"
          :accent="SERIES.download"
        />
        <MiniStat
          :label="t('dashboard.connections')"
          :value="String(network?.connections ?? 0)"
          icon="pi pi-link"
          :accent="SERIES.users"
        />
        <MiniStat
          :label="t('dashboard.uniqueIps')"
          :value="String(network?.unique_ips ?? 0)"
          icon="pi pi-map-marker"
          :accent="SERIES.online"
        />
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.net-rates {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.net-rate {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.net-rate i {
  font-size: 0.65rem;
}
.net-rate--up {
  color: #f97316;
  background: rgb(249 115 22 / 14%);
}
.net-rate--down {
  color: #06b6d4;
  background: rgb(6 182 212 / 14%);
}
.net-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem 1.25rem;
}
</style>
