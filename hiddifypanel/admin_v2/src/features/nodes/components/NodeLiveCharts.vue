<script setup lang="ts">
/**
 * One node's live charts on its Nodes card ("Show more"): network up/down, CPU and RAM over the last minutes, drawn
 * like the dashboard's Node health (same chart, colours and formats) but for this node only.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricChart from '@/features/dashboard/components/MetricChart.vue'
import { SERIES } from '@/features/dashboard/composables/useChartTheme'
import type { NodeSample } from '@/features/dashboard/composables/useMetricHistory'
import { timeLabels } from '@/features/dashboard/utils/series'
import { formatBitRate, formatGb, formatPercent } from '@/shared/utils/format-metrics'

const props = defineProps<{ samples: NodeSample[]; error?: string }>()

const { t, locale } = useI18n()

const labels = computed(() =>
  timeLabels(
    props.samples.map((sample) => sample.at),
    locale.value,
  ),
)
const network = computed(() => [
  { label: t('dashboard.upload'), values: props.samples.map((sample) => sample.up), color: SERIES.upload, type: 'line' as const, area: true },
  { label: t('dashboard.download'), values: props.samples.map((sample) => -sample.down), color: SERIES.download, type: 'line' as const, area: true },
])
const cpu = computed(() => [{ label: t('dashboard.cpu'), values: props.samples.map((sample) => sample.cpu), color: SERIES.cpu, type: 'line' as const, area: true }])
const memory = computed(() => [{ label: t('dashboard.ram'), values: props.samples.map((sample) => sample.memory), color: SERIES.memory, type: 'line' as const, area: true }])

/** A short chart has two ticks: the same range above and below zero, from the peak (Chart.js picked 800 Kb/s for 100) */
const networkPeak = computed(() => {
  const peak = Math.max(0, ...props.samples.map((sample) => Math.max(sample.up, sample.down)))
  return peak > 0 ? peak * 1.15 : undefined
})

/** The latest value of each chart, beside its heading. */
const last = computed(() => props.samples[props.samples.length - 1])

const percentFormatter = (value: number) => formatPercent(value, 1)
const bitRateFormatter = (value: number) => formatBitRate(Math.abs(value))
const cpuTooltip = (_d: number, i: number, formatted: string) => {
  const sample = props.samples[i]
  return sample ? `${formatted} · ${t('dashboard.cpuCores', { count: sample.cores })}` : undefined
}
const memoryTooltip = (_d: number, i: number, formatted: string) => {
  const sample = props.samples[i]
  return sample ? `${formatted} · ${formatGb(sample.memoryUsedGb, 1)} / ${formatGb(sample.memoryTotalGb, 1)}` : undefined
}
</script>

<template>
  <div class="nlc">
    <p v-if="error" class="nlc__note nlc__note--error"><i class="pi pi-exclamation-triangle" />{{ error }}</p>
    <p v-else-if="samples.length < 2" class="nlc__note"><i class="pi pi-spin pi-spinner" />{{ t('nodes.live.collecting') }}</p>
    <div class="nlc__grid">
      <div class="nlc__chart">
        <p class="nlc__heading">
          {{ t('dashboard.network') }}
          <span v-if="last" class="nlc__now" dir="ltr">↑ {{ bitRateFormatter(last.up) }} · ↓ {{ bitRateFormatter(last.down) }}</span>
        </p>
        <MetricChart :labels="labels" :series="network" type="line" :stacked="true" page-tooltip mirror :y-max="networkPeak" :y-min="networkPeak ? -networkPeak : undefined" :legend="false" :value-formatter="bitRateFormatter" :height="48" :max-x-ticks="3" />
      </div>
      <div class="nlc__chart">
        <p class="nlc__heading">
          {{ t('dashboard.cpu') }}
          <span v-if="last" class="nlc__now">{{ percentFormatter(last.cpu) }}</span>
        </p>
        <MetricChart :labels="labels" :series="cpu" :tooltip-label="cpuTooltip" type="line" :stacked="true" page-tooltip :legend="false" :value-formatter="percentFormatter" :height="48" :max-x-ticks="3" />
      </div>
      <div class="nlc__chart">
        <p class="nlc__heading">
          {{ t('dashboard.ram') }}
          <span v-if="last" class="nlc__now">{{ percentFormatter(last.memory) }}</span>
        </p>
        <MetricChart :labels="labels" :series="memory" :tooltip-label="memoryTooltip" type="line" :stacked="true" page-tooltip :legend="false" :value-formatter="percentFormatter" :height="48" :max-x-ticks="3" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.nlc {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
/* The card is narrow: the charts stack (the dashboard puts three in a row only from 52rem) */
.nlc__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.4rem;
}
/* Half the dashboard's height: a glance inside the card, the dashboard has the large ones */
.nlc__chart {
  padding: 0.4rem 0.55rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.85rem;
  background: var(--p-content-background);
}
.nlc__heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0 0 0.15rem;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.nlc__now {
  font-size: 0.78rem;
  letter-spacing: 0;
  text-transform: none;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.nlc__note {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.nlc__note--error {
  color: var(--p-orange-500);
}
</style>
