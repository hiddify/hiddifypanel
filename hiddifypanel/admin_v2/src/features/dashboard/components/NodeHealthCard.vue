<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import type { DashboardNodeStats } from '@/core/api/generated'
import { formatDuration, formatGb, formatPercent } from '@/shared/utils/format-metrics'
import { SERIES, nodeColor } from '../composables/useChartTheme'
import type { NodeSample } from '../composables/useMetricHistory'
import { timeLabels } from '../utils/series'
import DashCard from './DashCard.vue'
import ProcessTable from './ProcessTable.vue'
import Sparkline from './Sparkline.vue'

const props = defineProps<{
  nodes: DashboardNodeStats[]
  history: Record<number, NodeSample[]>
}>()

const { t, locale } = useI18n()

type MetricKey = 'cpu' | 'memory'

const expanded = ref<Record<number, MetricKey | null>>({})

const rows = computed(() =>
  props.nodes.map((node, index) => {
    const samples = props.history[node.id] ?? []
    return {
      ...node,
      color: nodeColor(index),
      title: node.id === 0 ? t('dashboard.thisServer') : node.name,
      samples,
      times: timeLabels(
        samples.map((sample) => sample.at),
        locale.value,
      ),
    }
  }),
)

function toggle(nodeId: number, metric: MetricKey) {
  expanded.value = {
    ...expanded.value,
    [nodeId]: expanded.value[nodeId] === metric ? null : metric,
  }
}

function percentFormatter(value: number) {
  return formatPercent(value, 1)
}
</script>

<template>
  <DashCard
    v-if="rows.length"
    :title="t('dashboard.nodeHealth')"
    :subtitle="t('dashboard.nodeHealthHint')"
    icon="pi pi-server"
    :accent="SERIES.usage"
    padded
  >
    <div class="node-health">
      <article v-for="node in rows" :key="node.id" class="node-health__row">
        <header class="node-health__head">
          <span class="node-health__dot" :style="{ background: node.color }" />
          <div class="min-w-0">
            <strong>{{ node.title }}</strong>
            <p v-if="node.host" class="node-health__host">
              {{ node.host.hostname }}
              <template v-if="node.host.uptime_s"> · {{ formatDuration(node.host.uptime_s) }}</template>
            </p>
          </div>
          <Tag
            :value="node.ok ? t('dashboard.nodeOnline') : t('dashboard.nodeOffline')"
            :severity="node.ok ? 'success' : 'danger'"
          />
        </header>
        <p v-if="!node.ok" class="node-health__error">{{ node.error || t('dashboard.nodeUnreachable') }}</p>
        <div v-else class="node-health__metrics">
          <button
            type="button"
            class="node-metric"
            :class="{ 'node-metric--open': expanded[node.id] === 'cpu' }"
            :style="{ '--metric-accent': SERIES.cpu }"
            :title="t('dashboard.clickForProcesses')"
            @click="toggle(node.id, 'cpu')"
          >
            <div class="node-metric__top">
              <span>{{ t('dashboard.cpu') }}</span>
              <strong>{{ formatPercent(node.cpu?.percent ?? 0, 1) }}</strong>
            </div>
            <Sparkline
              :values="node.samples.map((sample) => sample.cpu)"
              :color="SERIES.cpu"
              :height="42"
              :labels="node.times"
              :formatter="percentFormatter"
            />
          </button>
          <button
            type="button"
            class="node-metric"
            :class="{ 'node-metric--open': expanded[node.id] === 'memory' }"
            :style="{ '--metric-accent': SERIES.memory }"
            :title="t('dashboard.clickForProcesses')"
            @click="toggle(node.id, 'memory')"
          >
            <div class="node-metric__top">
              <span>{{ t('dashboard.ram') }}</span>
              <strong>{{ formatPercent(node.memory?.percent ?? 0, 1) }}</strong>
            </div>
            <Sparkline
              :values="node.samples.map((sample) => sample.memory)"
              :color="SERIES.memory"
              :height="42"
              :labels="node.times"
              :formatter="percentFormatter"
            />
            <p class="node-metric__caption">
              {{ formatGb(node.memory?.used_gb ?? 0, 1) }} / {{ formatGb(node.memory?.total_gb ?? 0, 1) }}
            </p>
          </button>
          <div class="node-metric node-metric--static" :style="{ '--metric-accent': SERIES.disk }">
            <div class="node-metric__top">
              <span>{{ t('dashboard.disk') }}</span>
              <strong>{{ formatPercent(node.disk?.percent ?? 0, 1) }}</strong>
            </div>
            <Sparkline
              :values="node.samples.map((sample) => sample.disk)"
              :color="SERIES.disk"
              :height="42"
              :labels="node.times"
              :formatter="percentFormatter"
            />
            <p class="node-metric__caption">
              {{ formatGb(node.disk?.used_gb ?? 0, 1) }} / {{ formatGb(node.disk?.total_gb ?? 0, 1) }}
            </p>
          </div>
        </div>
        <div v-if="expanded[node.id] === 'cpu'" class="node-health__processes">
          <p class="node-health__heading">{{ t('dashboard.topProcesses') }} · {{ t('dashboard.cpu') }}</p>
          <ProcessTable
            :processes="node.processes?.cpu ?? []"
            :color="SERIES.cpu"
            :formatter="(process) => formatPercent(process.percent, 1)"
            :limit="12"
          />
        </div>
        <div v-else-if="expanded[node.id] === 'memory'" class="node-health__processes">
          <p class="node-health__heading">{{ t('dashboard.topProcesses') }} · {{ t('dashboard.ram') }}</p>
          <ProcessTable
            :processes="node.processes?.memory ?? []"
            :color="SERIES.memory"
            :formatter="(process) => formatGb(process.memory_gb ?? 0, 2)"
            :limit="12"
          />
        </div>
      </article>
    </div>
  </DashCard>
</template>

<style scoped>
.node-health {
  display: grid;
  gap: 1rem;
}
.node-health__row {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 0.85rem 0.9rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.9rem;
  background: color-mix(in srgb, var(--p-text-color) 3%, transparent);
}
.node-health__head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}
.node-health__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  flex-shrink: 0;
}
.node-health__host {
  margin: 0.15rem 0 0;
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--p-text-muted-color);
}
.node-health__error {
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-red-500);
}
.node-health__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}
.node-metric {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 0;
  padding: 0.55rem 0.65rem 0.45rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: var(--p-content-background);
  color: inherit;
  text-align: start;
  cursor: pointer;
}
.node-metric--static {
  cursor: default;
}
.node-metric--open {
  border-color: color-mix(in srgb, var(--metric-accent) 55%, var(--p-content-border-color));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--metric-accent) 35%, transparent);
}
.node-metric__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.node-metric__top strong {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
  text-transform: none;
  letter-spacing: 0;
}
.node-metric__caption {
  margin: 0;
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.node-health__processes {
  padding-top: 0.25rem;
}
.node-health__heading {
  margin: 0 0 0.55rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
@media (max-width: 767px) {
  .node-health__metrics {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
