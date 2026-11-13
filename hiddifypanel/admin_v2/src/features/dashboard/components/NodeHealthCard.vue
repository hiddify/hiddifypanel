<script setup lang="ts">
import { countryFlag, countryName } from '@/shared/utils/country'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import NodeContactError from '@/features/nodes/components/NodeContactError.vue'
import ProgressSpinner from 'primevue/progressspinner'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { dashboardApi, type DashboardDiskDetail, type DashboardNodeStats } from '@/core/api/generated'
import { durationParts, formatBitRate, formatGb, formatPercent } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import type { NodeSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricBar from './MetricBar.vue'
import MetricChart from './MetricChart.vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { isChildPanel, isSuperAdmin } from '@/core/panelShell'
import { nodesApi } from '@/features/nodes/api'
import { dashboardNodeName, editableNodeName } from '../utils/node-name'

const props = defineProps<{
  nodes: DashboardNodeStats[]
  history: Record<number, NodeSample[]>
  childId?: number | null
}>()
const emit = defineEmits<{ renamed: [] }>()

const { t, locale } = useI18n()
const toast = useToast()

/** Only the toolbar's selected node, or every node when nothing is selected. */
const visibleNodes = computed(() =>
  props.childId == null ? props.nodes : props.nodes.filter((node) => node.id === props.childId),
)
const multiNode = computed(() => visibleNodes.value.length > 1)

const nodeTitle = (node: DashboardNodeStats) => dashboardNodeName(node.id, node.name, t('dashboard.thisServer'))
/** The node's country, by its address: the flag before its name, as on the Nodes page. */
const nodeFlag = (node: DashboardNodeStats) => countryFlag(node.country)
const nodeCountry = (node: DashboardNodeStats) => (node.country ? countryName(node.country, locale.value) : '')

const tableRows = computed(() =>
  visibleNodes.value.map((node) => ({
    id: node.id,
    title: nodeTitle(node),
    name: node.name,
    flag: nodeFlag(node),
    country: nodeCountry(node),
    color: nodeColor(node.id),
    panelUrl: node.panel_url ?? null,
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

/** Renaming from the dashboard: the pencil after a name opens a small popover (super admins, not on a node's panel). */
const canRename = computed(() => isSuperAdmin.value && !isChildPanel.value)
const renamePop = ref<InstanceType<typeof Popover> | null>(null)
const renameInput = ref<{ $el: HTMLInputElement } | null>(null)
const renameTarget = ref<{ id: number; title: string; name: string } | null>(null)
const renameValue = ref('')
const renaming = ref(false)

function openRename(event: Event, row: { id: number; title: string; name: string }) {
  renameTarget.value = row
  renameValue.value = editableNodeName(row.id, row.name)
  renamePop.value?.show(event)
}
function focusRename() {
  renameInput.value?.$el.focus()
  renameInput.value?.$el.select()
}
async function saveRename() {
  const target = renameTarget.value
  if (!target || renaming.value) return
  const name = renameValue.value.trim()
  // this server may go back to its default name (empty); a node needs one
  if ((!name && target.id !== 0) || name === editableNodeName(target.id, target.name)) {
    renamePop.value?.hide()
    return
  }
  renaming.value = true
  try {
    const res = await nodesApi.rename(target.id, name)
    const shown = name || t('dashboard.thisServer')
    if (res.synced_to_node) toast.add({ severity: 'success', summary: t('nodes.renamed', { name: shown }), life: 3000 })
    else toast.add({ severity: 'warn', summary: t('nodes.renamedHereOnly', { name: shown }), detail: t('nodes.renamedHereOnlyDetail'), life: 7000 })
    renamePop.value?.hide()
    emit('renamed')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    renaming.value = false
  }
}

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

/** Upload above zero, download below (mirrored), in each node's own colour; several nodes stack per side. */
const networkOverview = computed(() => {
  const width = overviewLabels.value.length
  return visibleNodes.value.flatMap((node) => {
    const samples = props.history[node.id] ?? []
    const pad = Math.max(0, width - samples.length)
    const color = nodeColor(node.id)
    const title = nodeTitle(node)
    return [
      { label: `${title} · ${t('dashboard.upload')}`, values: [...Array(pad).fill(0), ...samples.map((sample) => sample.up)], color, type: 'line' as const, area: true },
      { label: `${title} · ${t('dashboard.download')}`, values: [...Array(pad).fill(0), ...samples.map((sample) => -sample.down)], color, type: 'line' as const, area: true, dashed: true },
    ]
  })
})

/** The same range above and below zero (zero in the middle: upload's half and download's half), from the peak. */
const networkPeak = computed(() => {
  const series = networkOverview.value
  let peak = 0
  for (let i = 0; i < overviewLabels.value.length; i++) {
    let up = 0
    let down = 0
    for (const s of series) {
      const v = s.values[i] ?? 0
      if (v > 0) up += v
      else down -= v
    }
    peak = Math.max(peak, up, down)
  }
  return peak > 0 ? niceRate(peak * 1.1) : undefined
})

/** A round rate at or above ``bytesPerSecond`` (1, 2 or 5 × 10ⁿ bits/s), so the ticks read 20 / 40 Mb/s, not 68.8. */
function niceRate(bytesPerSecond: number): number {
  const bits = bytesPerSecond * 8
  const magnitude = 10 ** Math.floor(Math.log10(bits))
  const step = [1, 2, 5, 10].find((m) => m * magnitude >= bits) ?? 10
  return (step * magnitude) / 8
}

/** Each node's colour and its latest rates, under the network chart. */
const networkLegend = computed(() =>
  visibleNodes.value.map((node) => {
    const samples = props.history[node.id] ?? []
    const last = samples[samples.length - 1]
    // no sample: the node could not be asked (shown as —, not as 0 b/s)
    return { id: node.id, title: nodeTitle(node), color: nodeColor(node.id), last }
  }),
)

const cpuOverview = computed(() => resourceSeries('cpu', t('dashboard.cpu'), SERIES.cpu))
const memoryOverview = computed(() => resourceSeries('memory', t('dashboard.ram'), SERIES.memory))

/** The sample a chart point shows for a node (multi-node series are left-padded to the same width). */
function sampleAt(node: DashboardNodeStats, dataIndex: number): NodeSample | undefined {
  const samples = props.history[node.id] ?? []
  const pad = Math.max(0, overviewLabels.value.length - samples.length)
  return samples[dataIndex - pad]
}

/** Hover text per server: CPU usage and core count, or RAM percent with used / total. */
function tooltipLabel(metric: 'cpu' | 'memory') {
  return (datasetIndex: number, dataIndex: number, formatted: string): string | undefined => {
    const node = visibleNodes.value[multiNode.value ? datasetIndex : 0]
    const sample = node ? sampleAt(node, dataIndex) : undefined
    if (!node || !sample) return undefined
    const detail =
      metric === 'cpu'
        ? t('dashboard.cpuCores', { count: sample.cores })
        : `${formatGb(sample.memoryUsedGb, 1)} / ${formatGb(sample.memoryTotalGb, 1)}`
    // Each part is isolated, so a Latin server name between Persian text does not scramble the line
    const rtl = document.documentElement.dir === 'rtl'
    const iso = (text: string) => (rtl ? `\u2068${text}\u2069` : text)
    const name = (text: string) => (rtl ? `\u2067${text}\u2069` : text)
    return `${rtl ? '\u200F' : ''}${name(nodeTitle(node))}: ${iso(formatted)} · ${iso(detail)}`
  }
}
const cpuTooltipLabel = tooltipLabel('cpu')
const memoryTooltipLabel = tooltipLabel('memory')

const percentFormatter = (value: number) => formatPercent(value, 1)
const bitRateFormatter = (value: number) => formatBitRate(Math.abs(value))

/** Clicking the CPU/RAM overview chart toggles a combined top-processes list across visible nodes. */
function formatUptime(seconds: number): string {
  const parts = durationParts(seconds)
  if (parts.days) return t('dashboard.durationDaysHours', parts)
  if (parts.hours) return t('dashboard.durationHoursMinutes', parts)
  return t('dashboard.durationMinutes', parts)
}

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
        <span v-if="node.flag" class="node-flag" :title="node.country" :aria-label="node.country">{{ node.flag }}</span>
        {{ node.title }}
      </span>
    </div>

    <div class="node-health__overview-grid">
      <button type="button" class="node-health__overview-chart" @click="toggleMetric('cpu')">
        <p class="node-health__heading">{{ t('dashboard.cpu') }}</p>
        <MetricChart
          :labels="overviewLabels"
          :series="cpuOverview"
          :tooltip-label="cpuTooltipLabel"
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
          :tooltip-label="memoryTooltipLabel"
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
        <div class="node-health__net">
          <span class="node-health__net-side node-health__net-side--up"><i class="pi pi-arrow-up" />{{ t('dashboard.upload') }}</span>
          <span class="node-health__net-side node-health__net-side--down"><i class="pi pi-arrow-down" />{{ t('dashboard.download') }}</span>
          <MetricChart
            :labels="overviewLabels"
            :series="networkOverview"
            type="line"
            :stacked="true"
            mirror
            :y-max="networkPeak"
            :y-min="networkPeak ? -networkPeak : undefined"
            :legend="false"
            :value-formatter="bitRateFormatter"
            :height="140"
            :max-x-ticks="6"
          />
        </div>
        <ul class="node-health__net-legend">
          <li v-for="n in networkLegend" :key="n.id">
            <span class="node-health__net-dot" :style="{ background: n.color }" />
            <span class="node-health__net-name">{{ n.title }}</span>
            <template v-if="n.last">
              <span class="node-health__net-rate" dir="ltr"><i class="pi pi-arrow-up" />{{ bitRateFormatter(n.last.up) }}</span>
              <span class="node-health__net-rate" dir="ltr"><i class="pi pi-arrow-down" />{{ bitRateFormatter(n.last.down) }}</span>
            </template>
            <span v-else class="node-health__net-rate">—</span>
          </li>
        </ul>
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

    <DataTable :value="tableRows" size="small" class="node-table" data-key="id" scrollable>
      <Column :header="t('dashboard.node')">
        <template #body="{ data }">
          <span class="node-cell__dot" :style="{ background: data.color }" />
          <a v-if="data.panelUrl" :href="data.panelUrl" target="_blank" rel="noopener" class="min-w-0 node-cell__title node-cell__link">
            <strong><span v-if="data.flag" class="node-flag" :title="data.country" :aria-label="data.country">{{ data.flag }}</span>{{ data.title }} <i class="pi pi-external-link" /></strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </a>
          <div v-else class="min-w-0 node-cell__title">
            <strong><span v-if="data.flag" class="node-flag" :title="data.country" :aria-label="data.country">{{ data.flag }}</span>{{ data.title }}</strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </div>
          <button v-if="canRename" type="button" class="node-cell__edit" :aria-label="t('nodes.rename')" :title="t('nodes.rename')" @click="openRename($event, data)">
            <i class="pi pi-pencil" />
          </button>
          <Tag v-if="!data.ok" :value="t('dashboard.nodeOffline')" severity="danger" class="node-cell__tag" />
        </template>
      </Column>
      <Column :header="t('dashboard.uptime')">
        <template #body="{ data }">{{ data.uptimeS !== null ? formatUptime(data.uptimeS) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.panelVersion')">
        <template #body="{ data }">{{ data.panelVersion ?? '—' }}</template>
      </Column>
      <Column :header="t('dashboard.disk')">
        <template #body="{ data }">
          <button v-if="data.ok" type="button" class="disk-cell" @click="openDisk({ id: data.id, title: data.title })">
            {{ data.diskPercent !== null ? formatPercent(data.diskPercent, 1) : '—' }}
            <!-- hidden for now; shown again with v-if="data.diskUsedGb !== null" -->
            <span v-if="false" class="disk-cell__sub">{{ formatGb(data.diskUsedGb, 1) }} / {{ formatGb(data.diskTotalGb ?? 0, 1) }}</span>
            <i class="pi pi-external-link" />
          </button>
          <span v-else>—</span>
        </template>
      </Column>
      <Column :header="t('dashboard.uploadSinceBoot')">
        <template #body="{ data }">{{ data.sentGb !== null ? formatGb(data.sentGb, 1) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.downloadSinceBoot')">
        <template #body="{ data }">{{ data.recvGb !== null ? formatGb(data.recvGb, 1) : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.connections')">
        <template #body="{ data }">{{ data.connections !== null ? data.connections : '—' }}</template>
      </Column>
      <Column :header="t('dashboard.uniqueIps')">
        <template #body="{ data }">{{ data.uniqueIps !== null ? data.uniqueIps : '—' }}</template>
      </Column>
    </DataTable>

    <ul class="node-list">
      <li v-for="data in tableRows" :key="data.id" class="node-list__item">
        <div class="node-list__head">
          <span class="node-cell__dot" :style="{ background: data.color }" />
          <a v-if="data.panelUrl" :href="data.panelUrl" target="_blank" rel="noopener" class="min-w-0 node-cell__title node-cell__link">
            <strong><span v-if="data.flag" class="node-flag" :title="data.country" :aria-label="data.country">{{ data.flag }}</span>{{ data.title }} <i class="pi pi-external-link" /></strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </a>
          <div v-else class="min-w-0 node-cell__title">
            <strong><span v-if="data.flag" class="node-flag" :title="data.country" :aria-label="data.country">{{ data.flag }}</span>{{ data.title }}</strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </div>
          <button v-if="canRename" type="button" class="node-cell__edit" :aria-label="t('nodes.rename')" :title="t('nodes.rename')" @click="openRename($event, data)">
            <i class="pi pi-pencil" />
          </button>
          <Tag v-if="!data.ok" :value="t('dashboard.nodeOffline')" severity="danger" class="node-cell__tag" />
        </div>
        <dl class="node-list__stats">
          <div>
            <dt>{{ t('dashboard.uptime') }}</dt>
            <dd>{{ data.uptimeS !== null ? formatUptime(data.uptimeS) : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('dashboard.panelVersion') }}</dt>
            <dd>{{ data.panelVersion ?? '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('dashboard.disk') }}</dt>
            <dd>
              <button v-if="data.ok" type="button" class="disk-cell" @click="openDisk({ id: data.id, title: data.title })">
                {{ data.diskPercent !== null ? formatPercent(data.diskPercent, 1) : '—' }}
                <i class="pi pi-external-link" />
              </button>
              <span v-else>—</span>
            </dd>
          </div>
          <div>
            <dt>{{ t('dashboard.connections') }}</dt>
            <dd>{{ data.connections !== null ? data.connections : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('dashboard.uploadSinceBoot') }}</dt>
            <dd>{{ data.sentGb !== null ? formatGb(data.sentGb, 1) : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('dashboard.downloadSinceBoot') }}</dt>
            <dd>{{ data.recvGb !== null ? formatGb(data.recvGb, 1) : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('dashboard.uniqueIps') }}</dt>
            <dd>{{ data.uniqueIps !== null ? data.uniqueIps : '—' }}</dd>
          </div>
        </dl>
      </li>
    </ul>

    <Dialog
      v-model:visible="diskDialogOpen"
      modal
      :header="diskDialogNode?.title"
      :style="{ width: '30rem' }"
      :breakpoints="{ '575px': 'calc(100vw - 2rem)' }"
    >
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
        <!-- The node could not be asked: why and what to do, in the panel's language -->
        <NodeContactError v-if="diskDetail.error_code" :code="diskDetail.error_code" :detail="diskDetail.error" />
        <p v-else-if="diskDetail.error" class="disk-dialog__error">{{ diskDetail.error }}</p>
      </template>
    </Dialog>
    <Popover ref="renamePop" class="node-rename" @show="focusRename">
      <form v-if="renameTarget" class="node-rename__form" @submit.prevent="saveRename">
        <label class="node-rename__label" for="node-rename-input">{{ t('nodes.rename') }}</label>
        <div class="node-rename__row">
          <InputText
            id="node-rename-input"
            ref="renameInput"
            v-model="renameValue"
            size="small"
            maxlength="100"
            :placeholder="renameTarget.id === 0 ? t('dashboard.thisServer') : ''"
            @keydown.esc="renamePop?.hide()"
          />
          <Button
            type="submit"
            icon="pi pi-check"
            size="small"
            :loading="renaming"
            :disabled="renameTarget.id !== 0 && !renameValue.trim()"
            :aria-label="t('common.save')"
          />
        </div>
        <small v-if="renameTarget.id === 0" class="node-rename__hint">{{ t('dashboard.renameThisServerHint', { name: t('dashboard.thisServer') }) }}</small>
      </form>
    </Popover>
  </DashCard>
</template>

<style scoped>
/* The node's country flag before its name; colour emoji fonts first, so the flag shows, not its two letters */
.node-flag {
  display: inline-block;
  margin-inline-end: 0.35rem;
  font-size: 1.1em;
  line-height: 1;
  font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
}
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
  grid-template-columns: minmax(0, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
@container dashboard (min-width: 52rem) {
  .node-health__overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
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
.node-health__net {
  position: relative;
}
/* which half is which: upload on top, download below zero */
.node-health__net-side {
  position: absolute;
  inset-inline-end: 0.25rem;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-content-background) 80%, transparent);
  pointer-events: none;
}
.node-health__net-side i {
  font-size: 0.55rem;
}
.node-health__net-side--up {
  top: 0;
}
.node-health__net-side--down {
  /* above the time labels */
  bottom: 2.15rem;
}
.node-health__net-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.9rem;
  margin: 0.45rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.72rem;
}
.node-health__net-legend li {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
}
.node-health__net-dot {
  width: 0.55rem;
  height: 0.55rem;
  flex: none;
  border-radius: 999px;
}
.node-health__net-name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 9rem;
}
.node-health__net-rate {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.node-health__net-rate i {
  font-size: 0.55rem;
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
  /* A slow pulse, like a heartbeat: only its opacity moves, never its size */
  animation: node-dot-pulse 2.8s ease-in-out infinite;
}
@keyframes node-dot-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .node-cell__dot {
    animation: none;
  }
}
/* The pencil after a name: renames the server or node in a small popover */
.node-cell__edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  margin-inline-start: 0.15rem;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  flex-shrink: 0;
  vertical-align: middle;
}
.node-cell__edit i {
  font-size: 0.7rem;
}
.node-cell__edit:hover,
.node-cell__edit:focus-visible {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}
.node-rename__form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  width: min(15rem, 80vw);
}
.node-rename__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.node-rename__row {
  display: flex;
  gap: 0.4rem;
}
.node-rename__row :deep(input) {
  flex: 1;
  min-width: 0;
}
.node-rename__hint {
  color: var(--p-text-muted-color);
  font-size: 0.7rem;
  line-height: 1.35;
}
/* One line: the name, then the machine's host name, small and grey; every row is as tall and the name in its middle */
.node-cell__title {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  column-gap: 0.45rem;
  vertical-align: middle;
}
.node-cell__link {
  color: inherit;
  text-decoration: none;
}
.node-cell__link:hover strong {
  color: var(--p-primary-color);
}
.node-cell__link i {
  font-size: 0.6rem;
  color: var(--p-text-muted-color);
}
.node-cell__host {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--p-text-muted-color);
}
/* No taller than a line of text: the offline node's row is as tall as the others */
.node-cell__tag {
  margin-inline-start: 0.5rem;
  padding: 0.05rem 0.45rem;
  font-size: 0.7rem;
  line-height: 1.3;
  vertical-align: middle;
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
/* Stacked node cards replace the wide table on narrow screens. */
.node-list {
  display: none;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.node-list__item {
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.85rem;
}
.node-list__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.6rem;
}
.node-list__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem 1rem;
  margin: 0;
}
.node-list__stats dt {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
}
.node-list__stats dd {
  margin: 0.1rem 0 0;
  font-size: 0.85rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
@container dashboard (max-width: 48rem) {
  .node-table {
    display: none;
  }
  .node-list {
    display: flex;
  }
}
</style>
