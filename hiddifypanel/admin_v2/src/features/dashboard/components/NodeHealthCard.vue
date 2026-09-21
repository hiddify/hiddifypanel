<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { dashboardApi, type DashboardDiskDetail, type DashboardNodeStats } from '@/core/api/generated'
import { formatBitRate, formatDuration, formatGb, formatPercent } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import type { NodeSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricBar from './MetricBar.vue'
import MetricChart from './MetricChart.vue'

const props = defineProps<{
  nodes: DashboardNodeStats[]
  history: Record<number, NodeSample[]>
  childId?: number | null
}>()

const { t, locale } = useI18n()

/** Only the toolbar's selected node, or every node when nothing is selected. */
const visibleNodes = computed(() =>
  props.childId == null ? props.nodes : props.nodes.filter((node) => node.id === props.childId),
)
const multiNode = computed(() => visibleNodes.value.length > 1)

const nodeTitle = (node: DashboardNodeStats) => (node.id === 0 ? t('dashboard.thisServer') : node.name)

const tableRows = computed(() =>
  visibleNodes.value.map((node) => ({
    id: node.id,
    title: nodeTitle(node),
    color: nodeColor(node.id),
    ok: node.ok,
    hostname: node.host?.hostname ?? '',
    uptimeS: node.host?.uptime_s ?? null,
    panelVersion: node.host?.panel_version ?? null,
    diskPercent: node.disk?.percent ?? null,
    diskUsedGb: node.disk?.used_gb ?? null,
    diskTotalGb: node.disk?.total_gb ?? null,
    sentGb: node.network?.sent_gb ?? null,
    recvGb: node.network?.recv_gb ?? null,
    connections: node.network?.connections ?? null,
    uniqueIps: node.network?.unique_ips ?? null,
  })),
)

const overviewLabels = computed(() => {
  let longest: NodeSample[] = []
  for (const node of visibleNodes.value) {
    const samples = props.history[node.id] ?? []
    if (samples.length > longest.length) longest = samples
  }
  return timeLabels(
    longest.map((sample) => sample.at),
    locale.value,
  )
})

/** Stacked per node when several are visible; a single semantic-colored line otherwise. */
function resourceSeries(metric: 'cpu' | 'memory', label: string, color: string) {
  if (!multiNode.value) {
    const node = visibleNodes.value[0]
    const samples = node ? (props.history[node.id] ?? []) : []
    return [{ label, values: samples.map((sample) => sample[metric]), color, type: 'line' as const, area: true }]
  }
  const width = overviewLabels.value.length
  return visibleNodes.value.map((node) => {
    const samples = props.history[node.id] ?? []
    const pad = Math.max(0, width - samples.length)
    return {
      label: nodeTitle(node),
      values: [...Array(pad).fill(0), ...samples.map((sample) => sample[metric])],
      color: nodeColor(node.id),
      type: 'line' as const,
      area: true,
    }
  })
}

/** Mirrored upload(+)/download(-); one node's pair, or every node's pair stacked. */
const networkOverview = computed(() => {
  if (!multiNode.value) {
    const node = visibleNodes.value[0]
    const samples = node ? (props.history[node.id] ?? []) : []
    return [
      { label: t('dashboard.upload'), values: samples.map((sample) => sample.up), color: SERIES.upload, type: 'line' as const, area: true },
      { label: t('dashboard.download'), values: samples.map((sample) => -sample.down), color: SERIES.download, type: 'line' as const, area: true },
    ]
  }
  const width = overviewLabels.value.length
  return visibleNodes.value.flatMap((node) => {
    const samples = props.history[node.id] ?? []
    const pad = Math.max(0, width - samples.length)
    const color = nodeColor(node.id)
    const title = nodeTitle(node)
    return [
      { label: `${title} ↑`, values: [...Array(pad).fill(0), ...samples.map((sample) => sample.up)], color, type: 'line' as const, area: true },
      { label: `${title} ↓`, values: [...Array(pad).fill(0), ...samples.map((sample) => -sample.down)], color, type: 'line' as const, area: true },
    ]
  })
})

const cpuOverview = computed(() => resourceSeries('cpu', t('dashboard.cpu'), SERIES.cpu))
const memoryOverview = computed(() => resourceSeries('memory', t('dashboard.ram'), SERIES.memory))

const percentFormatter = (value: number) => formatPercent(value, 1)
const bitRateFormatter = (value: number) => formatBitRate(Math.abs(value))

/** Clicking the CPU/RAM overview chart toggles a combined top-processes list across visible nodes. */
const expandedMetric = ref<'cpu' | 'memory' | null>(null)
function toggleMetric(metric: 'cpu' | 'memory') {
  expandedMetric.value = expandedMetric.value === metric ? null : metric
}

interface ProcRow {
  nodeTitle: string
  color: string
  name: string
  path: string
  percent: number
  valueText: string
}

function aggregatedProcesses(metric: 'cpu' | 'memory'): ProcRow[] {
  const rows: ProcRow[] = []
  for (const node of visibleNodes.value) {
    if (!node.ok) continue
    const title = nodeTitle(node)
    const color = nodeColor(node.id)
    const list = (metric === 'cpu' ? node.processes?.cpu : node.processes?.memory) ?? []
    for (const proc of list) {
      if (!proc.name.trim()) continue
      rows.push({
        nodeTitle: title,
        color,
        name: proc.name,
        path: proc.path ?? '',
        percent: proc.percent,
        valueText: metric === 'cpu' ? formatPercent(proc.percent, 1) : formatGb(proc.memory_gb ?? 0, 2),
      })
    }
  }
  return rows.sort((a, b) => b.percent - a.percent).slice(0, 15)
}

const cpuProcesses = computed(() => aggregatedProcesses('cpu'))
const memoryProcesses = computed(() => aggregatedProcesses('memory'))
const visibleProcesses = computed(() => (expandedMetric.value === 'cpu' ? cpuProcesses.value : memoryProcesses.value))
const processScale = computed(() => Math.max(1, ...visibleProcesses.value.map((row) => row.percent)))

/** Disk popup: current usage + largest top-level folders, fetched on demand. */
const diskDialogOpen = ref(false)
const diskDialogNode = ref<{ id: number; title: string } | null>(null)
const diskDetail = ref<DashboardDiskDetail | null>(null)
const diskLoading = ref(false)

async function openDisk(row: { id: number; title: string }) {
  diskDialogNode.value = row
  diskDialogOpen.value = true
  diskDetail.value = null
  diskLoading.value = true
  try {
    diskDetail.value = await dashboardApi.disk({ child_id: row.id })
  } catch {
    diskDetail.value = null
  } finally {
    diskLoading.value = false
  }
}

const largestFolder = computed(() => diskDetail.value?.top_folders[0]?.size_gb ?? 1)
</script>

<template>
  <DashCard
    v-if="tableRows.length"
    :title="t('dashboard.nodeHealth')"
    :subtitle="multiNode ? t('dashboard.nodeHealthStackedHint') : t('dashboard.nodeHealthHint')"
    icon="pi pi-server"
    :accent="SERIES.usage"
    padded
  >
    <div v-if="multiNode" class="node-health__legend">
      <span v-for="node in tableRows" :key="node.id" class="node-health__legend-item">
        <span class="node-health__dot" :style="{ background: node.color }" />
        {{ node.title }}
      </span>
    </div>

    <div class="node-health__overview-grid">
      <button type="button" class="node-health__overview-chart" @click="toggleMetric('cpu')">
        <p class="node-health__heading">{{ t('dashboard.cpu') }}</p>
        <MetricChart
          :labels="overviewLabels"
          :series="cpuOverview"
          type="line"
          :stacked="true"
          :legend="false"
          :value-formatter="percentFormatter"
          :height="140"
          :max-x-ticks="6"
        />
      </button>
      <button type="button" class="node-health__overview-chart" @click="toggleMetric('memory')">
        <p class="node-health__heading">{{ t('dashboard.ram') }}</p>
        <MetricChart
          :labels="overviewLabels"
          :series="memoryOverview"
          type="line"
          :stacked="true"
          :legend="false"
          :value-formatter="percentFormatter"
          :height="140"
          :max-x-ticks="6"
        />
      </button>
      <div class="node-health__overview-chart node-health__overview-chart--static">
        <p class="node-health__heading">{{ t('dashboard.network') }}</p>
        <MetricChart
          :labels="overviewLabels"
          :series="networkOverview"
          type="line"
          :stacked="true"
          mirror
          :legend="false"
          :value-formatter="bitRateFormatter"
          :height="140"
          :max-x-ticks="6"
        />
      </div>
    </div>

    <div v-if="expandedMetric" class="node-health__processes">
      <p class="node-health__heading">{{ t('dashboard.topProcesses') }} · {{ expandedMetric === 'cpu' ? t('dashboard.cpu') : t('dashboard.ram') }}</p>
      <div v-if="visibleProcesses.length" class="processes">
        <MetricBar
          v-for="(row, index) in visibleProcesses"
          :key="index"
          :label="`${row.nodeTitle} ${row.name}`"
          :sublabel="row.path || undefined"
          :percent="(row.percent / processScale) * 100"
          :value="row.valueText"
          :color="row.color"
          compact
        >
          <template #label>
            <span class="proc-node" :style="{ color: row.color }">{{ row.nodeTitle }}</span>
            <span class="proc-name">{{ row.name }}</span>
          </template>
        </MetricBar>
      </div>
      <p v-else class="node-health__empty">{{ t('dashboard.noData') }}</p>
    </div>

    <DataTable :value="tableRows" size="small" class="node-table" data-key="id">
      <Column :header="t('dashboard.node')">
        <template #body="{ data }">
          <span class="node-cell__dot" :style="{ background: data.color }" />
          <div class="min-w-0 node-cell__title">
            <strong>{{ data.title }}</strong>
            <p v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</p>
          </div>
          <Tag v-if="!data.ok" :value="t('dashboard.nodeOffline')" severity="danger" class="node-cell__tag" />
        </template>
      </Column>
      <Column :header="t('dashboard.uptime')">
        <template #body="{ data }">{{ data.uptimeS !== null ? formatDuration(data.uptimeS) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.panelVersion')">
        <template #body="{ data }">{{ data.panelVersion ?? '—' }}</template>
      </Column>
      <Column :header="t('dashboard.disk')">
        <template #body="{ data }">
          <button v-if="data.ok" type="button" class="disk-cell" @click="openDisk({ id: data.id, title: data.title })">
            {{ data.diskPercent !== null ? formatPercent(data.diskPercent, 1) : '—' }}
            <span v-if="data.diskUsedGb !== null" class="disk-cell__sub">{{ formatGb(data.diskUsedGb, 1) }} / {{ formatGb(data.diskTotalGb ?? 0, 1) }}</span>
            <i class="pi pi-external-link" />
          </button>
          <span v-else>—</span>
        </template>
      </Column>
      <Column :header="t('dashboard.sentSinceRestart')">
        <template #body="{ data }">{{ data.sentGb !== null ? formatGb(data.sentGb, 1) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.receivedSinceRestart')">
        <template #body="{ data }">{{ data.recvGb !== null ? formatGb(data.recvGb, 1) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.connections')">
        <template #body="{ data }">{{ data.connections !== null ? data.connections : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.uniqueIps')">
        <template #body="{ data }">{{ data.uniqueIps !== null ? data.uniqueIps : '—' }}</template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="diskDialogOpen" modal :header="diskDialogNode?.title" :style="{ width: '30rem' }">
      <div v-if="diskLoading" class="disk-dialog__loading">
        <ProgressSpinner style="width: 2.5rem; height: 2.5rem" stroke-width="4" />
      </div>
      <template v-else-if="diskDetail">
        <MetricBar
          :label="t('dashboard.disk')"
          :sublabel="`${t('dashboard.free')}: ${formatGb(diskDetail.disk.free_gb, 1)}`"
          :percent="diskDetail.disk.percent"
          :value="`${formatGb(diskDetail.disk.used_gb, 1)} / ${formatGb(diskDetail.disk.total_gb, 1)}`"
          :color="SERIES.disk"
          auto-color
        />
        <p class="disk-dialog__heading">{{ t('dashboard.topFolders') }} · {{ t('dashboard.hiddifyData') }}</p>
        <div v-if="diskDetail.top_folders.length" class="disk-dialog__folders">
          <MetricBar
            v-for="folder in diskDetail.top_folders"
            :key="folder.path"
            :label="folder.name"
            :sublabel="folder.path"
            :percent="(folder.size_gb / largestFolder) * 100"
            :value="formatGb(folder.size_gb, 1)"
            :color="SERIES.disk"
            compact
          />
        </div>
        <p v-else class="disk-dialog__empty">{{ t('dashboard.noData') }}</p>
        <p v-if="diskDetail.error" class="disk-dialog__error">{{ diskDetail.error }}</p>
      </template>
    </Dialog>
  </DashCard>
</template>

<style scoped>
.node-health__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.9rem;
  margin-bottom: 0.75rem;
}
.node-health__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.node-health__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  flex-shrink: 0;
}
.node-health__overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.node-health__overview-chart {
  display: block;
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.85rem;
  background: var(--p-content-background);
  text-align: start;
  cursor: pointer;
  color: inherit;
}
.node-health__overview-chart--static {
  cursor: default;
}
.node-health__heading {
  margin: 0 0 0.35rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.node-health__processes {
  margin-bottom: 1rem;
  padding: 0.85rem 0.9rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.85rem;
  background: color-mix(in srgb, var(--p-text-color) 3%, transparent);
}
.node-health__empty {
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.processes {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.proc-node {
  font-weight: 700;
}
.proc-name {
  color: var(--p-text-color);
}
.node-cell__dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  margin-inline-end: 0.5rem;
  flex-shrink: 0;
}
.node-cell__title {
  display: inline-block;
  vertical-align: middle;
}
.node-cell__host {
  margin: 0.1rem 0 0;
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--p-text-muted-color);
}
.node-cell__tag {
  margin-inline-start: 0.5rem;
}
.disk-cell {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0;
  border: none;
  background: none;
  color: var(--p-text-color);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.disk-cell:hover {
  color: var(--p-primary-color);
}
.disk-cell__sub {
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--p-text-muted-color);
}
.disk-cell i {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
}
.disk-dialog__loading {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}
.disk-dialog__heading {
  margin: 1.1rem 0 0.55rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.disk-dialog__folders {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.disk-dialog__empty {
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.disk-dialog__error {
  margin: 0.75rem 0 0;
  font-size: 0.78rem;
  color: var(--p-red-500);
}
@media (max-width: 991px) {
  .node-health__overview-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
