<script setup lang="ts">
/** A speedometer: a half dial from zero to the scale's top, a coloured arc and a needle that springs to the rate. */
import { computed } from 'vue'

const props = defineProps<{
  value: number
  max: number
  label: string
  color: string
  icon: string
  format: (value: number) => string
  /** The window's peak, marked on the dial */
  peak?: number
}>()

const R = 78
const CX = 100
const CY = 98
const uid = `sg-${Math.random().toString(36).slice(2, 8)}`
const share = computed(() => (props.max > 0 ? Math.min(1, Math.max(0, props.value / props.max)) : 0))
const half = Math.PI * R
const arc = `M${CX - R},${CY} A${R},${R} 0 0 1 ${CX + R},${CY}`
const angle = computed(() => -90 + share.value * 180)
const point = (fraction: number, radius: number) => {
  const a = Math.PI * (1 - fraction)
  return { x: CX + radius * Math.cos(a), y: CY - radius * Math.sin(a) }
}
const ticks = Array.from({ length: 21 }, (_, i) => {
  const major = i % 5 === 0
  const a = point(i / 20, R - 14)
  const b = point(i / 20, R - (major ? 22 : 18))
  return { a, b, major }
})
/** Zero under the dial's left end and the scale's top under its right end, clear of the needle */
const scale = computed(() => [
  { x: CX - R, y: CY + 16, text: '0', anchor: 'middle' },
  { x: CX + R, y: CY + 16, text: props.format(props.max).replace(/\.0+(?=\s)/, ''), anchor: 'middle' },
])
const peakMark = computed(() => {
  if (!props.peak || !props.max) return null
  const f = Math.min(1, props.peak / props.max)
  return { a: point(f, R + 9), b: point(f, R + 2) }
})
const parts = computed(() => {
  const text = props.format(props.value)
  const cut = text.lastIndexOf(' ')
  return cut > 0 ? { number: text.slice(0, cut), unit: text.slice(cut + 1) } : { number: text, unit: '' }
})
</script>

<template>
  <figure class="sg" :style="{ '--sg-color': color }">
    <svg viewBox="0 0 200 118" class="sg__dial" role="img" :aria-label="`${label}: ${format(value)}`">
      <defs>
        <linearGradient :id="`${uid}-arc`" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" :stop-color="color" stop-opacity="0.45" />
          <stop offset="100%" :stop-color="color" />
        </linearGradient>
        <filter :id="`${uid}-glow`" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
      </defs>
      <path :d="arc" class="sg__track" />
      <path :d="arc" class="sg__glow" :stroke="color" :stroke-dasharray="`${half * share} ${half}`" :filter="`url(#${uid}-glow)`" />
      <path :d="arc" class="sg__value" :stroke="`url(#${uid}-arc)`" :stroke-dasharray="`${half * share} ${half}`" />
      <line v-for="(tick, i) in ticks" :key="i" :x1="tick.a.x" :y1="tick.a.y" :x2="tick.b.x" :y2="tick.b.y" class="sg__tick" :class="{ 'sg__tick--major': tick.major }" />
      <text v-for="(s, i) in scale" :key="`s${i}`" :x="s.x" :y="s.y" :text-anchor="s.anchor" class="sg__scale">{{ s.text }}</text>
      <line v-if="peakMark" :x1="peakMark.a.x" :y1="peakMark.a.y" :x2="peakMark.b.x" :y2="peakMark.b.y" class="sg__peak" />
      <g class="sg__needle" :style="{ transform: `rotate(${angle}deg)` }">
        <path :d="`M${CX - 3},${CY} L${CX},${CY - R + 12} L${CX + 3},${CY} Z`" />
      </g>
      <circle :cx="CX" :cy="CY" r="7" class="sg__hub" />
      <circle :cx="CX" :cy="CY" r="2.6" class="sg__hub-dot" />
    </svg>
    <figcaption class="sg__read">
      <span class="sg__label"><i :class="icon" />{{ label }}</span>
      <span class="sg__number" dir="ltr"
        >{{ parts.number }}<small>{{ parts.unit }}</small></span
      >
    </figcaption>
  </figure>
</template>

<style scoped>
.sg {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  margin: 0;
}
.sg__dial {
  width: 100%;
  max-width: 15rem;
  overflow: visible;
}
.sg__track,
.sg__value,
.sg__glow {
  fill: none;
  stroke-width: 11;
  stroke-linecap: round;
}
.sg__track {
  stroke: color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
.sg__glow {
  opacity: 0.35;
}
.sg__value,
.sg__glow {
  transition: stroke-dasharray 0.9s cubic-bezier(0.34, 1.3, 0.5, 1);
}
.sg__tick {
  stroke: color-mix(in srgb, var(--p-text-color) 22%, transparent);
  stroke-width: 1;
}
.sg__tick--major {
  stroke: color-mix(in srgb, var(--p-text-color) 45%, transparent);
  stroke-width: 1.6;
}
.sg__scale {
  fill: var(--p-text-muted-color);
  font-size: 8.5px;
  font-variant-numeric: tabular-nums;
}
.sg__peak {
  stroke: var(--sg-color);
  stroke-width: 2.2;
  stroke-linecap: round;
}
.sg__needle {
  transform-origin: 100px 98px;
  transform-box: view-box;
  fill: var(--p-text-color);
  transition: transform 0.9s cubic-bezier(0.34, 1.45, 0.5, 1);
}
.sg__hub {
  fill: var(--p-content-background);
  stroke: var(--p-text-color);
  stroke-width: 2;
}
.sg__hub-dot {
  fill: var(--sg-color);
}
.sg__read {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  margin-top: -0.2rem;
}
.sg__label {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
}
.sg__label i {
  font-size: 0.66rem;
  color: var(--sg-color);
}
.sg__number {
  font-size: 1.45rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.sg__number small {
  margin-inline-start: 0.25rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
@media (prefers-reduced-motion: reduce) {
  .sg__needle,
  .sg__value,
  .sg__glow {
    transition: none;
  }
}
</style>
