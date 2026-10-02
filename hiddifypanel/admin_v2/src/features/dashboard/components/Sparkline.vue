<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    values: number[]
    color?: string
    height?: number
    filled?: boolean
    labels?: string[]
    formatter?: (value: number) => string
  }>(),
  { color: 'var(--p-primary-color)', height: 40, filled: true, labels: () => [], formatter: (value: number) => String(value) },
)

const WIDTH = 100
const gradientId = `spark-${Math.random().toString(36).slice(2, 9)}`
const hover = ref<{ index: number; clientX: number; clientY: number } | null>(null)

/** Points normalized into a 100 x height viewBox, oldest sample first. */
const points = computed(() => {
  const values = props.values
  if (values.length === 0) return []
  const max = Math.max(...values, 0)
  const min = Math.min(...values, 0)
  const span = max - min || 1
  const step = values.length > 1 ? WIDTH / (values.length - 1) : 0
  const usable = props.height - 4
  return values.map((value, index) => ({
    x: values.length > 1 ? index * step : WIDTH / 2,
    y: 2 + usable - ((value - min) / span) * usable,
  }))
})

const line = computed(() => points.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' '))

const area = computed(() => {
  if (points.value.length < 2) return ''
  const first = points.value[0]!
  const last = points.value[points.value.length - 1]!
  return `${line.value} L${last.x.toFixed(2)},${props.height} L${first.x.toFixed(2)},${props.height} Z`
})

const hoverText = computed(() => {
  if (!hover.value) return ''
  const value = props.values[hover.value.index]
  if (value === undefined) return ''
  const label = props.labels[hover.value.index]
  const formatted = props.formatter(value)
  return label ? `${label} · ${formatted}` : formatted
})

/** Keeps the tip on screen: it flips to the pointer's left past mid-viewport. */
const tipStyle = computed(() => {
  if (!hover.value) return {}
  const { clientX, clientY } = hover.value
  const top = `${Math.max(8, clientY - 36)}px`
  return clientX > window.innerWidth / 2
    ? { right: `${window.innerWidth - clientX + 12}px`, top }
    : { left: `${clientX + 12}px`, top }
})

let hideTimer: ReturnType<typeof setTimeout> | undefined

function onMove(event: PointerEvent) {
  clearTimeout(hideTimer)
  if (props.values.length === 0) return
  const rect = (event.currentTarget as SVGElement).getBoundingClientRect()
  const ratio = rect.width ? (event.clientX - rect.left) / rect.width : 0
  const index = Math.min(props.values.length - 1, Math.max(0, Math.round(ratio * (props.values.length - 1))))
  hover.value = { index, clientX: event.clientX, clientY: event.clientY }
}

function onLeave(event: PointerEvent) {
  // Touch fires pointerleave on lift; keep the value readable for a moment.
  if (event.pointerType === 'mouse') {
    hover.value = null
    return
  }
  hideTimer = setTimeout(() => (hover.value = null), 1500)
}

onBeforeUnmount(() => clearTimeout(hideTimer))
</script>

<template>
  <div class="sparkline-wrap">
    <svg
      class="sparkline"
      :viewBox="`0 0 ${WIDTH} ${height}`"
      :style="{ height: `${height}px`, color }"
      preserveAspectRatio="none"
      role="img"
      @pointerdown="onMove"
      @pointermove="onMove"
      @pointerleave="onLeave"
    >
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
          <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path v-if="filled && area" :d="area" :fill="`url(#${gradientId})`" stroke="none" />
      <path
        v-if="line"
        :d="line"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linecap="round"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    <div
      v-if="hover && hoverText"
      class="sparkline-tip"
      :style="tipStyle"
    >
      {{ hoverText }}
    </div>
  </div>
</template>

<style scoped>
.sparkline-wrap {
  position: relative;
  width: 100%;
}
.sparkline {
  display: block;
  width: 100%;
}
.sparkline-tip {
  position: fixed;
  z-index: 40;
  pointer-events: none;
  padding: 0.35rem 0.55rem;
  border-radius: 0.45rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.72rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 8px 24px -12px rgb(15 23 42 / 45%);
  white-space: nowrap;
}
</style>
