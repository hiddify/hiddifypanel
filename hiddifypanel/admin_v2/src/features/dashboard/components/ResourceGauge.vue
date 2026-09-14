<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    percent: number
    color?: string
    size?: number
    /** Big text in the middle; defaults to the rounded percentage. */
    value?: string
    caption?: string
    /** Turn the arc amber/red as the metric approaches saturation. */
    autoColor?: boolean
  }>(),
  { color: 'var(--p-primary-color)', size: 96, autoColor: true },
)

const RADIUS = 42
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const SWEEP = 0.75

const clamped = computed(() => Math.min(100, Math.max(0, Number(props.percent) || 0)))

const arcColor = computed(() => {
  if (!props.autoColor) return props.color
  if (clamped.value >= 90) return 'var(--p-red-500)'
  if (clamped.value >= 75) return 'var(--p-amber-500)'
  return props.color
})

const trackDash = `${CIRCUMFERENCE * SWEEP} ${CIRCUMFERENCE}`
const valueDash = computed(() => `${CIRCUMFERENCE * SWEEP * (clamped.value / 100)} ${CIRCUMFERENCE}`)
</script>

<template>
  <div class="gauge" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 100 100">
      <circle
        class="gauge__track"
        cx="50"
        cy="50"
        :r="RADIUS"
        fill="none"
        stroke-width="8"
        stroke-linecap="round"
        :stroke-dasharray="trackDash"
        transform="rotate(135 50 50)"
      />
      <circle
        cx="50"
        cy="50"
        :r="RADIUS"
        fill="none"
        :stroke="arcColor"
        stroke-width="8"
        stroke-linecap="round"
        :stroke-dasharray="valueDash"
        transform="rotate(135 50 50)"
        class="gauge__value"
      />
    </svg>
    <div class="gauge__center">
      <span class="gauge__number">{{ value ?? `${Math.round(clamped)}%` }}</span>
      <span v-if="caption" class="gauge__caption">{{ caption }}</span>
    </div>
  </div>
</template>

<style scoped>
.gauge {
  position: relative;
  flex-shrink: 0;
}
.gauge svg {
  width: 100%;
  height: 100%;
}
.gauge__track {
  stroke: color-mix(in srgb, var(--p-text-color) 10%, transparent);
}
.gauge__value {
  transition: stroke-dasharray 0.45s ease, stroke 0.3s ease;
}
.gauge__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.1rem;
  pointer-events: none;
}
.gauge__number {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.gauge__caption {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
}
</style>
