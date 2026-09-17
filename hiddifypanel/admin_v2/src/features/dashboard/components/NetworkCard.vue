<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardNetwork, DashboardNodeStats } from '@/core/api/generated'
import { formatBitRate, formatGb } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import type { MetricSample, NodeSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'

const props = defineProps<{
  network: DashboardNetwork | null
  samples: MetricSample[]
  nodes: DashboardNodeStats[]
  nodeSamples: Record<number, NodeSample[]>
}>()

const { t, locale } = useI18n()

const liveNodes = computed(() => props.nodes.filter((node) => node.ok && (props.nodeSamples[node.id]?.length ?? 0) > 0))
const multiNode = computed(() => liveNodes.value.length > 1)

const nodeTitle = (node: DashboardNodeStats) => (node.id === 0 ? t('dashboard.thisServer') : node.name)

const longest = computed(() => {
  let best: NodeSample[] = []
  for (const node of liveNodes.value) {
    const series = props.nodeSamples[node.id] ?? []
    if (series.length > best.length) best = series
  }
  return best
})

const chartSeries = computed(() => {
  if (!multiNode.value) {
    return [
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
    ]
  }
  const width = longest.value.length
  return liveNodes.value.flatMap((node, index) => {
    const series = props.nodeSamples[node.id] ?? []
    const pad = Math.max(0, width - series.length)
    const color = nodeColor(index)
    return [
      {
        label: `${nodeTitle(node)} ↓`,
        values: [...Array(pad).fill(0), ...series.map((sample) => sample.down)],
        color,
        type: 'line' as const,
        area: true,
      },
      {
        label: `${nodeTitle(node)} ↑`,
        values: [...Array(pad).fill(0), ...series.map((sample) => sample.up)],
        color,
        dashed: true,
        type: 'line' as const,
        area: true,
      },
    ]
  })
})

const labels = computed(() => {
  if (!multiNode.value) return timeLabels(props.samples.map((sample) => sample.at), locale.value)
  return timeLabels(longest.value.map((sample) => sample.at), locale.value)
})

const latest = computed(() => {
  if (!multiNode.value) return props.samples[props.samples.length - 1] ?? null
  let up = 0
  let down = 0
  for (const node of liveNodes.value) {
    const series = props.nodeSamples[node.id] ?? []
    const point = series[series.length - 1]
    up += point?.up ?? 0
    down += point?.down ?? 0
  }
  return { up, down }
})

const totals = computed(() => {
  if (!multiNode.value) {
    return {
      sent: props.network?.sent_gb ?? 0,
      recv: props.network?.recv_gb ?? 0,
      connections: props.network?.connections ?? 0,
      uniqueIps: props.network?.unique_ips ?? 0,
    }
  }
  return liveNodes.value.reduce(
    (acc, node) => ({
      sent: acc.sent + (node.network?.sent_gb ?? 0),
      recv: acc.recv + (node.network?.recv_gb ?? 0),
      connections: acc.connections + (node.network?.connections ?? 0),
      uniqueIps: acc.uniqueIps + (node.network?.unique_ips ?? 0),
    }),
    { sent: 0, recv: 0, connections: 0, uniqueIps: 0 },
  )
})

function tooltipExtra(index: number): string[] {
  if (!multiNode.value) return []
  return liveNodes.value.map((node) => {
    const series = props.nodeSamples[node.id] ?? []
    const point = series[index - (longest.value.length - series.length)] ?? series[series.length - 1]
    return `${nodeTitle(node)}: ↑ ${formatBitRate(point?.up ?? 0)} · ↓ ${formatBitRate(point?.down ?? 0)}`
  })
}
</script>

<template>
  <DashCard
    :title="t('dashboard.network')"
    :subtitle="multiNode ? t('dashboard.nodeNetworkHint') : t('dashboard.liveThroughput')"
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
      :labels="labels"
      :series="chartSeries"
      type="line"
      :stacked="multiNode"
      :stack-total-label="t('dashboard.liveThroughput')"
      :tooltip-extra="tooltipExtra"
      :value-formatter="(value: number) => formatBitRate(value)"
      :height="190"
      :max-x-ticks="6"
    />

    <template #footer>
      <div class="net-footer">
        <MiniStat
          :label="t('dashboard.sentSinceRestart')"
          :value="formatGb(totals.sent, 1)"
          icon="pi pi-arrow-up"
          :accent="SERIES.upload"
        />
        <MiniStat
          :label="t('dashboard.receivedSinceRestart')"
          :value="formatGb(totals.recv, 1)"
          icon="pi pi-arrow-down"
          :accent="SERIES.download"
        />
        <MiniStat
          :label="t('dashboard.connections')"
          :value="String(totals.connections)"
          icon="pi pi-link"
          :accent="SERIES.users"
        />
        <MiniStat
          :label="t('dashboard.uniqueIps')"
          :value="String(totals.uniqueIps)"
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
