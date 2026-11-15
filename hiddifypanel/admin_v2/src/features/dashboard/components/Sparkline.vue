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
    /** How the points are drawn: a filled line, a bare line, columns, steps or dots */
    kind?: 'area' | 'line' | 'column' | 'step' | 'dots'
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

const stepped = computed(() => points.value.map((p, i) => (i ? `H${((points.value[i - 1]!.x + p.x) / 2).toFixed(2)} V${p.y.toFixed(2)} H${p.x.toFixed(2)}` : `M${p.x.toFixed(2)},${p.y.toFixed(2)}`)).join(' '))
/** A dot is a zero-length round-capped stroke: it stays round in the stretched viewBox */
const dots = computed(() => points.value.map((p) => `M${p.x.toFixed(2)},${p.y.toFixed(2)} l0,0`).join(' '))
const columns = computed(() => {
  const n = points.value.length
  const slot = WIDTH / Math.max(1, n)
  return points.value.map((p, i) => ({ x: i * slot + slot * 0.18, w: slot * 0.64, y: p.y, h: Math.max(1, props.height - p.y) }))
})

const area = computed(() => {
  if (points.value.length < 2) return ''
  const first = points.value[0]!
  const last = points.value[points.value.length - 1]!
  return `${line.value} L${last.x.toFixed(2)},${props.height} L${first.x.toFixed(2)},${props.height} Z`
})

/** The hovered day and its value, apart: the day quiet, the value bold in the line's colour */
const hoverParts = computed(() => {
  if (!hover.value) return null
  const value = props.values[hover.value.index]
  if (value === undefined) return null
  return { label: props.labels[hover.value.index] ?? '', value: props.formatter(value) }
})

/** Keeps the tip on screen: it flips to the pointer's left past mid-viewport. */
const tipStyle = computed(() => {
  if (!hover.value) return {}
  const { clientX, clientY } = hover.value
  // Under the pointer: above it the tip would cover the tile's big number
  const top = `${Math.min(window.innerHeight - 40, clientY + 18)}px`
  return clientX > window.innerWidth / 2 ? { right: `${window.innerWidth - clientX + 12}px`, top } : { left: `${clientX + 12}px`, top }
})

let hideTimer: ReturnType<typeof setTimeout> | undefined

/** The tip sits fixed on the screen: a scroll would leave it behind, so a scroll closes it */
function hideNow() {
  clearTimeout(hideTimer)
  hover.value = null
  document.removeEventListener('scroll', hideNow, { capture: true })
}

function onMove(event: PointerEvent) {
  clearTimeout(hideTimer)
  if (!hover.value) document.addEventListener('scroll', hideNow, { capture: true, passive: true })
  if (props.values.length === 0) return
  const rect = (event.currentTarget as SVGElement).getBoundingClientRect()
  const ratio = rect.width ? (event.clientX - rect.left) / rect.width : 0
  const index = Math.min(props.values.length - 1, Math.max(0, Math.round(ratio * (props.values.length - 1))))
  hover.value = { index, clientX: event.clientX, clientY: event.clientY }
}

function onLeave(event: PointerEvent) {
  // Touch fires pointerleave on lift; keep the value readable for a moment.
  if (event.pointerType === 'mouse') {
    hideNow()
    return
  }
  hideTimer = setTimeout(hideNow, 1500)
}

onBeforeUnmount(hideNow)
</script>

<template>
  <div class="sparkline-wrap">
    <svg class="sparkline" :viewBox="`0 0 ${WIDTH} ${height}`" :style="{ height: `${height}px`, color }" preserveAspectRatio="none" role="img" @pointerdown="onMove" @pointermove="onMove" @pointerleave="onLeave" @pointercancel="hideNow">
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
          <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
        </linearGradient>
      </defs>
      <Transition name="spark" mode="out-in">
        <g v-if="kind === 'column'" key="column" class="sparkline__shape">
          <rect v-for="(c, i) in columns" :key="i" :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="0.8" fill="currentColor" :fill-opacity="i === columns.length - 1 ? 1 : 0.55" />
        </g>
        <g v-else-if="kind === 'dots'" key="dots" class="sparkline__shape">
          <path :d="dots" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" vector-effect="non-scaling-stroke" />
        </g>
        <g v-else :key="kind ?? 'area'" class="sparkline__shape">
          <path v-if="filled && area && (kind ?? 'area') === 'area'" :d="area" :fill="`url(#${gradientId})`" stroke="none" />
          <path v-if="line" :d="kind === 'step' ? stepped : line" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
        </g>
      </Transition>
    </svg>
    <!-- In <body>: the tile lifts on hover (a transform), which would place a fixed tip from the tile, not the screen,
         and under the cards below it -->
    <Teleport to="body">
      <div v-if="hoverParts" class="sparkline-tip" :style="[tipStyle, { '--spark-color': color }]">
        <span v-if="hoverParts.label" class="sparkline-tip__label">{{ hoverParts.label }}</span>
        <span class="sparkline-tip__value">{{ hoverParts.value }}</span>
      </div>
    </Teleport>
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
.sparkline__shape {
  transform-box: view-box;
  transform-origin: 50% 100%;
}
.spark-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.45s cubic-bezier(0.32, 0.72, 0, 1);
}
.spark-leave-active {
  transition: opacity 0.12s ease;
}
.spark-enter-from {
  opacity: 0;
  transform: scaleY(0.4);
}
.spark-leave-to {
  opacity: 0;
}
.sparkline-tip {
  position: fixed;
  z-index: 40;
  pointer-events: none;
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.4rem 0.65rem;
  border-radius: 10px;
  border: 1px solid var(--p-content-border-color);
  border-top: 2px solid var(--spark-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.75rem;
  box-shadow: 0 14px 30px -14px rgb(15 23 42 / 40%);
  white-space: nowrap;
}
.sparkline-tip__label {
  color: var(--p-text-muted-color);
}
.sparkline-tip__value {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--spark-color);
}
</style>
