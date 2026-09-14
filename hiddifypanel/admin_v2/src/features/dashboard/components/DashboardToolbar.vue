<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import { formatClock } from '@/shared/utils/format-metrics'
import { RANGE_OPTIONS } from '../composables/useDashboard'

const props = defineProps<{
  rangeDays: number
  live: boolean
  refreshing: boolean
  failed: boolean
  updatedAt: Date | null
}>()

const emit = defineEmits<{
  'update:rangeDays': [value: number]
  'update:live': [value: boolean]
  refresh: []
}>()

const { t, locale } = useI18n()

const rangeItems = computed(() =>
  RANGE_OPTIONS.map((days) => ({ label: t('dashboard.nDays', { days }), value: days })),
)

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
      <SelectButton
        :model-value="rangeDays"
        :options="rangeItems"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        size="small"
        :aria-label="t('dashboard.range')"
        @update:model-value="(value: number) => emit('update:rangeDays', value)"
      />
      <Button
        :icon="live ? 'pi pi-pause' : 'pi pi-play'"
        :label="live ? t('dashboard.pause') : t('dashboard.resume')"
        severity="secondary"
        size="small"
        outlined
        @click="emit('update:live', !live)"
      />
      <Button
        icon="pi pi-refresh"
        :loading="refreshing"
        :aria-label="t('dashboard.refresh')"
        severity="secondary"
        size="small"
        text
        rounded
        @click="emit('refresh')"
      />
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
</style>
