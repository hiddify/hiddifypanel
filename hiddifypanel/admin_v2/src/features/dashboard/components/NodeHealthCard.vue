<script setup lang="ts">
import { countryName } from '@/shared/utils/country'
import FlagIcon from '@/shared/components/FlagIcon.vue'
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
import ResourceGauge from './ResourceGauge.vue'
import ChartViewSwitch from './ChartViewSwitch.vue'
import { useChartView } from '../composables/useChartView'
import ChartStyleButton from './ChartStyleButton.vue'
import SpeedGauge from './views/SpeedGauge.vue'
import NetStats from './views/NetStats.vue'
import { CHART_TYPES, LINE_TYPES, useChartStyle } from '../composables/useChartStyle'
import { formatBytes } from '@/shared/utils/format-metrics'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { isChildPanel, isSuperAdmin } from '@/core/panelShell'
import { nodesApi } from '@/features/nodes/api'
import { dashboardNodeName, editableNodeName } from '../utils/node-name'
import { useCardPopover } from '@/shared/composables/useCardPopover'
import { RENAME_MIN_MAJOR, nodeRenameBlock, type RenameBlock } from '@/shared/utils/node-rename'
import NodeIpInfo from './NodeIpInfo.vue'
import ColorGlyph from './ColorGlyph.vue'

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
/** The node's country, by its address: the flag before its name (waving, as on the Nodes page). */
const nodeFlag = (node: DashboardNodeStats) => (node.country ?? '').toLowerCase()
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
const renameInput = ref<{ $el: HTMLInputElement } | null>(null)
const renameTarget = ref<{ id: number; title: string; name: string; block: RenameBlock | null; version: string | null } | null>(null)
const renameValue = ref('')
const renaming = ref(false)

/** A node that can't take a new name now (it would only change here, see nodeRenameBlock): the popover says why */
const { pop: renamePop, open: openPop, hide: hidePop, onShow: onRenameShow, onHide: onRenameHide } = useCardPopover({
  card: '.node-list__item',
  onPlaced: () => focusRename(),
})

function openRename(event: Event, row: { id: number; title: string; name: string; ok: boolean; panelVersion: string | null }) {
  // this server is renamed here only: nothing to reach
  const block = row.id === 0 ? null : nodeRenameBlock(row.ok, row.panelVersion)
  renameTarget.value = { id: row.id, title: row.title, name: row.name, block, version: row.panelVersion }
  renameValue.value = editableNodeName(row.id, row.name)
  openPop(event)
}

function focusRename() {
  if (!renameTarget.value || renameTarget.value.block) return
  renameInput.value?.$el.focus()
  renameInput.value?.$el.select()
}
async function saveRename() {
  const target = renameTarget.value
  if (!target || target.block || renaming.value) return
  const name = renameValue.value.trim()
  // this server may go back to its default name (empty); a node needs one
  if ((!name && target.id !== 0) || name === editableNodeName(target.id, target.name)) {
    hidePop()
    return
  }
  renaming.value = true
  try {
    const res = await nodesApi.rename(target.id, name)
    const shown = name || t('dashboard.thisServer')
    if (res.synced_to_node) toast.add({ severity: 'success', summary: t('nodes.renamed', { name: shown }), life: 3000 })
    else toast.add({ severity: 'warn', summary: t('nodes.renamedHereOnly', { name: shown }), detail: t('nodes.renamedHereOnlyDetail'), life: 7000 })
    hidePop()
    emit('renamed')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    renaming.value = false
  }
}

/** The (i) after a name: everything known about the server's IP addresses, in a sheet (super admins) */
const ipInfoNode = ref<{ id: number; title: string } | null>(null)
const ipInfoOpen = ref(false)
function openIpInfo(row: { id: number; title: string }) {
  ipInfoNode.value = { id: row.id, title: row.title }
  ipInfoOpen.value = true
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
/** How the CPU and memory charts are shown: a chart over the last minutes (drawn in the style sheet's type), or gauges
 *  of the latest reading */
const OVERVIEW_VIEWS = ['lines', 'gauges'] as const
const overviewView = useChartView('node-overview', OVERVIEW_VIEWS)
const overviewViewOptions = computed(() => [
  { value: 'lines', icon: 'pi pi-wave-pulse', label: t('dashboard.views.lines') },
  { value: 'gauges', icon: 'pi pi-gauge', label: t('dashboard.views.gauges') },
])
/** Several servers stack: summed shapes (candles, baselines) would add their percentages up, so only per-server types */
const SPLIT_TYPES = [...LINE_TYPES, 'area', 'column', 'dots'] as readonly string[]
const resourceTypes = computed(() => (multiNode.value ? SPLIT_TYPES : CHART_TYPES))
const resourceStyleRaw = useChartStyle('node-resources', { type: 'area' })
const resetResourceStyle = resourceStyleRaw.reset
const resourceStyle = computed(() => (resourceTypes.value.includes(resourceStyleRaw.value.type) ? resourceStyleRaw.value : { ...resourceStyleRaw.value, type: 'area' }))

/** The network on its own: upload above and download below (mirror), both over zero (overlay), speedometers of the
 *  rate now, or the window's numbers */
const NET_VIEWS = ['mirror', 'overlay', 'speed', 'stats'] as const
const netView = useChartView('node-network', NET_VIEWS)
const netViewOptions = computed(() => [
  { value: 'mirror', icon: 'pi pi-sort-alt', label: t('dashboard.views.mirror') },
  { value: 'overlay', icon: 'pi pi-chart-line', label: t('dashboard.views.overlay') },
  { value: 'speed', icon: 'pi pi-gauge', label: t('dashboard.views.speed') },
  { value: 'stats', icon: 'pi pi-list', label: t('dashboard.views.stats') },
])
const netStyleRaw = useChartStyle('node-network', { type: 'area' })
const resetNetStyle = netStyleRaw.reset
/** Overlaid, upload and download are on one side: shapes that sum a side (candles, baselines, lollipops) would add them */
const netTypes = computed(() => (netView.value === 'overlay' ? SPLIT_TYPES : CHART_TYPES))
const netStyle = computed(() => (netTypes.value.includes(netStyleRaw.value.type) ? netStyleRaw.value : { ...netStyleRaw.value, type: 'area' }))

/** Download and upload over zero, each node in its colour (one server: download cyan, upload orange) */
const networkOverlay = computed(() => {
  const width = overviewLabels.value.length
  return visibleNodes.value.flatMap((node) => {
    const samples = props.history[node.id] ?? []
    const pad: number[] = Array(Math.max(0, width - samples.length)).fill(0)
    const title = nodeTitle(node)
    const one = !multiNode.value
    return [
      { label: one ? t('dashboard.download') : `${title} · ${t('dashboard.download')}`, values: [...pad, ...samples.map((x) => x.down)], color: one ? SERIES.download : nodeColor(node.id), type: 'line' as const, area: true },
      { label: one ? t('dashboard.upload') : `${title} · ${t('dashboard.upload')}`, values: [...pad, ...samples.map((x) => x.up)], color: one ? SERIES.upload : nodeColor(node.id), type: 'line' as const, area: one, dashed: !one },
    ]
  })
})

/** Every shown server together, per sample: times, download and upload */
const netTotals = computed(() => {
  let longest: NodeSample[] = []
  for (const node of visibleNodes.value) {
    const samples = props.history[node.id] ?? []
    if (samples.length > longest.length) longest = samples
  }
  const width = longest.length
  const down: number[] = Array(width).fill(0)
  const up: number[] = Array(width).fill(0)
  for (const node of visibleNodes.value) {
    const samples = props.history[node.id] ?? []
    const offset = width - samples.length
    samples.forEach((sample, i) => {
      down[offset + i]! += sample.down
      up[offset + i]! += sample.up
    })
  }
  return { times: longest.map((x) => x.at), down, up }
})
const netNow = computed(() => ({ down: netTotals.value.down.at(-1) ?? 0, up: netTotals.value.up.at(-1) ?? 0 }))
const netPeaks = computed(() => ({ down: Math.max(0, ...netTotals.value.down), up: Math.max(0, ...netTotals.value.up) }))
/** One scale for both dials, so their needles compare */
const speedMax = computed(() => niceRate(Math.max(netPeaks.value.down, netPeaks.value.up, 125000) * 1.1))
const netSides = computed(() => [
  { key: 'down', label: t('dashboard.download'), icon: 'pi pi-arrow-down', color: SERIES.download, values: netTotals.value.down },
  { key: 'up', label: t('dashboard.upload'), icon: 'pi pi-arrow-up', color: SERIES.upload, values: netTotals.value.up },
])
const netStatNames = computed(() => ({
  now: t('dashboard.netStats.now'),
  average: t('dashboard.netStats.average'),
  peak: t('dashboard.netStats.peak'),
  p95: t('dashboard.netStats.p95'),
  moved: t('dashboard.netStats.moved'),
}))
const bytesText = (value: number) => formatBytes(value, 1)

/** The latest reading of each shown server, for the gauges */
const latest = computed(() =>
  visibleNodes.value.map((node) => {
    const samples = props.history[node.id] ?? []
    return { id: node.id, title: nodeTitle(node), color: nodeColor(node.id), sample: samples[samples.length - 1] }
  }),
)


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
    <template #actions>
      <ChartViewSwitch v-model="overviewView" :options="overviewViewOptions" :label="t('dashboard.views.switch')" />
      <ChartStyleButton
        v-if="overviewView === 'lines'"
        v-model="resourceStyleRaw"
        :types="resourceTypes"
        :accent="SERIES.cpu"
        @reset="resetResourceStyle"
      />
    </template>
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
        <Transition name="cv" mode="out-in">
          <div v-if="overviewView === 'gauges'" key="gauges" class="node-health__gauges">
            <div v-for="n in latest" :key="n.id" class="node-health__gauge">
              <ResourceGauge
                :percent="n.sample?.cpu ?? 0"
                :color="multiNode ? n.color : SERIES.cpu"
                :value="n.sample ? percentFormatter(n.sample.cpu) : '—'"
                :size="multiNode ? 78 : 104"
              />
              <span v-if="multiNode" class="node-health__gauge-name">{{ n.title }}</span>
            </div>
          </div>
          <MetricChart
            v-else
            :key="overviewView"
            :labels="overviewLabels"
            :series="cpuOverview"
            :tooltip-label="cpuTooltipLabel"
            :chart-style="resourceStyle"
            :average-window="6"
            :average-label="t('dashboard.chartStyle.movingAverage')""
            :stacked="true"
            :legend="false"
            :value-formatter="percentFormatter"
            :height="140"
            :max-x-ticks="6"
          />
        </Transition>
      </button>
      <button type="button" class="node-health__overview-chart" @click="toggleMetric('memory')">
        <p class="node-health__heading">{{ t('dashboard.ram') }}</p>
        <Transition name="cv" mode="out-in">
          <div v-if="overviewView === 'gauges'" key="gauges" class="node-health__gauges">
            <div v-for="n in latest" :key="n.id" class="node-health__gauge">
              <ResourceGauge
                :percent="n.sample?.memory ?? 0"
                :color="multiNode ? n.color : SERIES.memory"
                :value="n.sample ? percentFormatter(n.sample.memory) : '—'"
                :size="multiNode ? 78 : 104"
              />
              <span v-if="multiNode" class="node-health__gauge-name">{{ n.title }}</span>
            </div>
          </div>
          <MetricChart
            v-else
            :key="overviewView"
            :labels="overviewLabels"
            :series="memoryOverview"
            :tooltip-label="memoryTooltipLabel"
            :chart-style="resourceStyle"
            :average-window="6"
            :average-label="t('dashboard.chartStyle.movingAverage')""
            :stacked="true"
            :legend="false"
            :value-formatter="percentFormatter"
            :height="140"
            :max-x-ticks="6"
          />
        </Transition>
      </button>
    </div>

    <!-- The network on its own panel: its own views and its own chart style -->
    <section class="nh-net">
      <header class="nh-net__head">
        <p class="node-health__heading nh-net__title">{{ t('dashboard.network') }}</p>
        <span class="nh-net__now" dir="ltr">
          <span class="nh-net__chip nh-net__chip--down"><i class="pi pi-arrow-down" />{{ bitRateFormatter(netNow.down) }}</span>
          <span class="nh-net__chip nh-net__chip--up"><i class="pi pi-arrow-up" />{{ bitRateFormatter(netNow.up) }}</span>
        </span>
        <div class="nh-net__tools">
          <ChartViewSwitch v-model="netView" :options="netViewOptions" :label="t('dashboard.views.switch')" />
          <ChartStyleButton v-if="netView === 'mirror' || netView === 'overlay'" v-model="netStyleRaw" :types="netTypes" :accent="SERIES.download" @reset="resetNetStyle" />
        </div>
      </header>
      <Transition name="cv" mode="out-in">
        <div v-if="netView === 'speed'" key="speed" class="nh-net__speed">
          <SpeedGauge :value="netNow.down" :max="speedMax" :peak="netPeaks.down" :label="t('dashboard.download')" icon="pi pi-arrow-down" :color="SERIES.download" :format="bitRateFormatter" />
          <SpeedGauge :value="netNow.up" :max="speedMax" :peak="netPeaks.up" :label="t('dashboard.upload')" icon="pi pi-arrow-up" :color="SERIES.upload" :format="bitRateFormatter" />
        </div>
        <NetStats
          v-else-if="netView === 'stats'"
          key="stats"
          :sides="netSides"
          :times="netTotals.times"
          :labels="overviewLabels.slice(-netTotals.times.length)"
          :rate="bitRateFormatter"
          :bytes="bytesText"
          :names="netStatNames"
        />
        <div v-else :key="netView" class="node-health__net">
          <template v-if="netView === 'mirror'">
            <span class="node-health__net-side node-health__net-side--up"><i class="pi pi-arrow-up" />{{ t('dashboard.upload') }}</span>
            <span class="node-health__net-side node-health__net-side--down"><i class="pi pi-arrow-down" />{{ t('dashboard.download') }}</span>
          </template>
          <MetricChart
            :labels="overviewLabels"
            :series="netView === 'mirror' ? networkOverview : networkOverlay"
            :chart-style="netStyle"
            :average-window="6"
            :average-label="t('dashboard.chartStyle.movingAverage')"
            :stacked="netView === 'mirror'"
            :mirror="netView === 'mirror'"
            :y-max="netView === 'mirror' ? networkPeak : undefined"
            :y-min="netView === 'mirror' && networkPeak ? -networkPeak : undefined"
            :legend="false"
            :value-formatter="bitRateFormatter"
            :height="190"
            :max-x-ticks="8"
          />
        </div>
      </Transition>
      <ul v-if="multiNode || netView === 'mirror'" class="node-health__net-legend">
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
    </section>

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
            <strong><FlagIcon v-if="data.flag" class="node-flag" :code="data.flag" :label="data.country" waving />{{ data.title }} <i class="pi pi-external-link" /></strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </a>
          <div v-else class="min-w-0 node-cell__title">
            <strong><FlagIcon v-if="data.flag" class="node-flag" :code="data.flag" :label="data.country" waving />{{ data.title }}</strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </div>
          <button v-if="canRename" type="button" class="node-cell__edit" :aria-label="t('nodes.rename')" :title="t('nodes.rename')" @click="openRename($event, data)">
            <ColorGlyph name="pencil" />
          </button>
          <button v-if="isSuperAdmin" type="button" class="node-cell__info" :aria-label="t('dashboard.ipInfo.open')" :title="t('dashboard.ipInfo.open')" @click="openIpInfo(data)">
            <ColorGlyph name="info" />
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
            <strong><FlagIcon v-if="data.flag" class="node-flag" :code="data.flag" :label="data.country" waving />{{ data.title }} <i class="pi pi-external-link" /></strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </a>
          <div v-else class="min-w-0 node-cell__title">
            <strong><FlagIcon v-if="data.flag" class="node-flag" :code="data.flag" :label="data.country" waving />{{ data.title }}</strong>
            <span v-if="data.hostname" class="node-cell__host">{{ data.hostname }}</span>
          </div>
          <button v-if="canRename" type="button" class="node-cell__edit" :aria-label="t('nodes.rename')" :title="t('nodes.rename')" @click="openRename($event, data)">
            <ColorGlyph name="pencil" />
          </button>
          <button v-if="isSuperAdmin" type="button" class="node-cell__info" :aria-label="t('dashboard.ipInfo.open')" :title="t('dashboard.ipInfo.open')" @click="openIpInfo(data)">
            <ColorGlyph name="info" />
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
    <Popover ref="renamePop" class="card-popover node-rename" @show="onRenameShow" @hide="onRenameHide">
      <form v-if="renameTarget && !renameTarget.block" class="node-rename__form" @submit.prevent="saveRename">
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
      <div v-else-if="renameTarget" class="card-popover__notice" role="status">
        <strong v-if="renameTarget.block === 'checking'"><i class="pi pi-spin pi-spinner" />{{ t('dashboard.renameCheckingTitle') }}</strong>
        <strong v-else><i class="pi pi-info-circle" />{{ t('dashboard.renameOfflineTitle') }}</strong>
        <p v-if="renameTarget.block === 'checking'">{{ t('dashboard.renameChecking', { name: renameTarget.title }) }}</p>
        <p v-else-if="renameTarget.block === 'tooOld'">{{ t('dashboard.renameTooOld', { name: renameTarget.title, version: renameTarget.version, min: `${RENAME_MIN_MAJOR}.0` }) }}</p>
        <p v-else>{{ t('dashboard.renameOffline', { name: renameTarget.title }) }}</p>
      </div>
    </Popover>
    <NodeIpInfo v-model:visible="ipInfoOpen" :node="ipInfoNode" />
  </DashCard>
</template>

<style scoped>
/* Gauges view of the live charts: a ring per server (latest reading), and up / down meters for the network */
.node-health__gauges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.75rem 1.25rem;
  min-height: 140px;
}
.node-health__gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
}
.node-health__gauge-name {
  max-width: 7rem;
  overflow: hidden;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}


/* The node's country flag before its name (a waving FlagIcon) */
.node-flag {
  margin-inline-end: 0.4rem;
  font-size: 0.95em;
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
/* The network's own panel under the CPU and memory charts */
.nh-net {
  margin-bottom: 1rem;
  padding: 0.75rem 0.85rem 0.6rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.85rem;
  background: var(--p-content-background);
}
.nh-net__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.6rem;
}
.nh-net__title {
  margin: 0;
}
.nh-net__now {
  display: inline-flex;
  gap: 0.35rem;
  min-width: 0;
}
.nh-net__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.nh-net__chip i {
  font-size: 0.6rem;
}
.nh-net__chip--down {
  color: color-mix(in srgb, #06b6d4 80%, var(--p-text-color));
  background: color-mix(in srgb, #06b6d4 13%, transparent);
}
.nh-net__chip--up {
  color: color-mix(in srgb, #f97316 80%, var(--p-text-color));
  background: color-mix(in srgb, #f97316 13%, transparent);
}
.nh-net__tools {
  display: flex;
  gap: 0.5rem;
  margin-inline-start: auto;
}
.nh-net__speed {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem 1.5rem;
  max-width: 34rem;
  margin: 0 auto;
  padding-block: 0.25rem 0.4rem;
}
.node-health__overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
@container dashboard (min-width: 40rem) {
  .node-health__overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
  /* on the right in every language: the chart keeps its value axis on the left, also in right-to-left pages */
  right: 0.25rem;
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
/* The (i) after a name: the server's IP details */
.node-cell__info {
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
/* the colour icons (ColorGlyph): a light-blue info circle and a yellow pencil, a little larger than the old glyphs */
.node-cell__info .glyph {
  width: 1.05rem;
  height: 1.05rem;
}
.node-cell__edit .glyph {
  width: 1.15rem;
  height: 1.15rem;
}
.node-cell__info .glyph,
.node-cell__edit .glyph {
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.node-cell__info:hover .glyph,
.node-cell__edit:hover .glyph {
  transform: scale(1.12);
}
.node-cell__info:active .glyph,
.node-cell__edit:active .glyph {
  transform: scale(0.92);
}
.node-cell__info:hover,
.node-cell__info:focus-visible {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background);
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

