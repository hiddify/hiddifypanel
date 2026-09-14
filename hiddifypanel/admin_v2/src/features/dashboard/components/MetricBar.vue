<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    percent: number
    value?: string
    color?: string
    compact?: boolean
    autoColor?: boolean
  }>(),
  { color: 'var(--p-primary-color)', compact: false, autoColor: false },
)

const clamped = computed(() => Math.min(100, Math.max(0, Number(props.percent) || 0)))

const barColor = computed(() => {
  if (!props.autoColor) return props.color
  if (clamped.value >= 90) return 'var(--p-red-500)'
  if (clamped.value >= 75) return 'var(--p-amber-500)'
  return props.color
})
</script>

<template>
  <div class="metric-bar" :class="{ 'metric-bar--compact': compact }">
    <div class="metric-bar__labels">
      <span class="metric-bar__label" :title="label">{{ label }}</span>
      <span class="metric-bar__value">{{ value ?? `${Math.round(clamped)}%` }}</span>
    </div>
    <div class="metric-bar__track">
      <div class="metric-bar__fill" :style="{ width: `${clamped}%`, background: barColor }" />
    </div>
  </div>
</template>

<style scoped>
.metric-bar {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.metric-bar__labels {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.78rem;
}
.metric-bar--compact .metric-bar__labels {
  font-size: 0.72rem;
}
.metric-bar__label {
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-bar__value {
  font-weight: 600;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.metric-bar__track {
  height: 0.4rem;
  border-radius: 999px;
  overflow: hidden;
  background: color-mix(in srgb, var(--p-text-color) 10%, transparent);
}
.metric-bar--compact .metric-bar__track {
  height: 0.3rem;
}
.metric-bar__fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.45s ease, background 0.3s ease;
}
</style>
