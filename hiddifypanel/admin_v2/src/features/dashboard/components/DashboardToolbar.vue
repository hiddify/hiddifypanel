<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import type { DashboardNode } from '@/core/api/generated'
import { formatClock } from '@/shared/utils/format-metrics'
import { RANGE_OPTIONS } from '../composables/useDashboard'
import { dashboardNodeName } from '../utils/node-name'
import DateRangeButton from './DateRangeButton.vue'
import type { CustomRange } from '../utils/date-range'

const ALL_NODES = -1

const props = defineProps<{
  rangeDays: number
  customRange: CustomRange | null
  childId: number | null
  nodes: DashboardNode[]
  live: boolean
  refreshing: boolean
  failed: boolean
  updatedAt: Date | null
}>()

const emit = defineEmits<{
  'update:rangeDays': [value: number]
  'update:customRange': [value: CustomRange | null]
  'update:childId': [value: number | null]
  'update:live': [value: boolean]
  refresh: []
}>()

const { t, locale } = useI18n()

const rangeItems = computed(() => RANGE_OPTIONS.map((days) => ({ label: t('dashboard.nDays', { days }), value: days })))

const nodeOptions = computed(() => [
  { label: t('dashboard.allNodes'), value: ALL_NODES },
  ...props.nodes.map((node) => ({
    label: dashboardNodeName(node.id, node.name, t('dashboard.thisServer')),
    value: node.id,
  })),
])

const selectedNode = computed({
  get: () => (props.childId === null ? ALL_NODES : props.childId),
  set: (value: number) => emit('update:childId', value === ALL_NODES ? null : value),
})

function pickDays(days: number) {
  emit('update:customRange', null)
  emit('update:rangeDays', days)
}

const status = computed(() => {
  if (props.failed) return { text: t('dashboard.loadFailed'), tone: 'error' }
  if (!props.live) return { text: t('dashboard.paused'), tone: 'paused' }
  return { text: t('dashboard.liveUpdated', { time: formatClock(props.updatedAt, locale.value) }), tone: 'live' }
})
</script>

<template>
  <div class="toolbar">
    <span class="status" :class="`status--${status.tone}`">
      <span class="status__dot" />
      {{ status.text }}
    </span>
    <div class="toolbar__controls">
      <Select v-model="selectedNode" :options="nodeOptions" option-label="label" option-value="value" size="small" class="toolbar__node" :aria-label="t('dashboard.node')" />
      <div class="toolbar__range-group">
        <SelectButton
          :model-value="customRange ? null : rangeDays"
          :options="rangeItems"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          size="small"
          class="toolbar__range"
          :aria-label="t('dashboard.range')"
          @update:model-value="pickDays"
        />
        <DateRangeButton :range-days="rangeDays" :custom-range="customRange" :toolbar-days="RANGE_OPTIONS" @pick-days="pickDays" @pick-range="(range: CustomRange) => emit('update:customRange', range)" />
      </div>
      <Button :icon="live ? 'pi pi-pause' : 'pi pi-play'" :label="live ? t('dashboard.pause') : t('dashboard.resume')" severity="secondary" size="small" outlined @click="emit('update:live', !live)" />
      <Button icon="pi pi-refresh" :loading="refreshing" :aria-label="t('dashboard.refresh')" severity="secondary" size="small" text rounded @click="emit('refresh')" />
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.toolbar__controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.toolbar__node {
  min-width: 11rem;
}
.toolbar__range-group {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.status__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: var(--p-text-muted-color);
}
.status--live .status__dot {
  background: var(--p-green-500);
  box-shadow: 0 0 0 0 rgb(34 197 94 / 60%);
  animation: status-pulse 2s infinite;
}
.status--error {
  color: var(--p-red-500);
}
.status--error .status__dot {
  background: var(--p-red-500);
}
@keyframes status-pulse {
  70% {
    box-shadow: 0 0 0 0.4rem rgb(34 197 94 / 0%);
  }
  100% {
    box-shadow: 0 0 0 0 rgb(34 197 94 / 0%);
  }
}
@media (max-width: 767px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar__controls {
    width: 100%;
  }
  .toolbar__node {
    flex: 1 1 100%;
    min-width: 0;
  }
  .toolbar__range-group {
    flex: 1 1 100%;
  }
  .toolbar__range {
    flex: 1 1 auto;
    min-width: 0;
  }
  .toolbar__range :deep(.p-selectbutton) {
    width: 100%;
    display: flex;
  }
  .toolbar__range :deep(.p-togglebutton) {
    flex: 1;
  }
}
</style>
