<script setup lang="ts">
/** A tiny drawing of a chart type for the style sheet: the same seven points as a line, a fill, bars or candles. */
import { computed } from 'vue'
import { FALL, RISE } from '../composables/useChartStyle'

const props = defineProps<{ type: string; color: string }>()

const W = 44
const H = 28
const DATA = [9, 15, 11, 19, 14, 22, 17]
const pts = DATA.map((v, i) => ({ x: 4 + i * 6, y: H - 2 - v }))
const mean = DATA.reduce((a, b) => a + b, 0) / DATA.length
const meanY = H - 2 - mean
const uid = `cti-${Math.random().toString(36).slice(2, 8)}`

const straight = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ')
/** Catmull-Rom through the points as cubic Béziers */
const smooth = pts
  .map((p, i) => {
    if (!i) return `M${p.x},${p.y}`
    const p0 = pts[i - 2] ?? pts[i - 1]!
    const p1 = pts[i - 1]!
    const p3 = pts[i + 1] ?? p
    const c1 = { x: p1.x + (p.x - p0.x) / 6, y: p1.y + (p.y - p0.y) / 6 }
    const c2 = { x: p.x - (p3.x - p1.x) / 6, y: p.y - (p3.y - p1.y) / 6 }
    return `C${c1.x.toFixed(1)},${c1.y.toFixed(1)} ${c2.x.toFixed(1)},${c2.y.toFixed(1)} ${p.x},${p.y}`
  })
  .join(' ')
const stepped = pts.map((p, i) => (i ? `H${(pts[i - 1]!.x + p.x) / 2} V${p.y} H${p.x}` : `M${p.x},${p.y}`)).join(' ')
const closeArea = (d: string) => `${d} L${pts[pts.length - 1]!.x},${H - 2} L${pts[0]!.x},${H - 2} Z`
const toMean = (d: string) => `${d} L${pts[pts.length - 1]!.x},${meanY} L${pts[0]!.x},${meanY} Z`

const CANDLES = [
  { o: 10, c: 16, h: 18, l: 8 },
  { o: 16, c: 12, h: 17, l: 10 },
  { o: 12, c: 19, h: 21, l: 11 },
  { o: 19, c: 15, h: 20, l: 13 },
  { o: 15, c: 22, h: 24, l: 14 },
  { o: 22, c: 18, h: 23, l: 16 },
]
const HEIKIN = [
  { o: 9, c: 13, h: 14, l: 8 },
  { o: 11, c: 16, h: 17, l: 10 },
  { o: 14, c: 20, h: 22, l: 13 },
  { o: 18, c: 15, h: 19, l: 13 },
  { o: 16, c: 13, h: 17, l: 11 },
  { o: 14, c: 19, h: 21, l: 13 },
]
const candles = computed(() =>
  (props.type === 'heikin' ? HEIKIN : CANDLES).map((c, i) => {
    const x = 6 + i * 6.4
    const up = c.c >= c.o
    return { x, up, top: H - 2 - Math.max(c.o, c.c), bottom: H - 2 - Math.min(c.o, c.c), hi: H - 2 - c.h, lo: H - 2 - c.l }
  }),
)
</script>

<template>
  <svg class="cti" :viewBox="`0 0 ${W} ${H}`" :style="{ color }" aria-hidden="true">
    <defs>
      <linearGradient :id="`${uid}-g`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="currentColor" stop-opacity="0.45" />
        <stop offset="100%" stop-color="currentColor" stop-opacity="0.04" />
      </linearGradient>
      <clipPath :id="`${uid}-top`"><rect x="0" y="0" :width="W" :height="meanY" /></clipPath>
      <clipPath :id="`${uid}-bot`"><rect x="0" :y="meanY" :width="W" :height="H - meanY" /></clipPath>
    </defs>

    <path v-if="type === 'line'" :d="straight" class="cti__stroke" />
    <path v-else-if="type === 'smooth'" :d="smooth" class="cti__stroke" />
    <path v-else-if="type === 'step'" :d="stepped" class="cti__stroke" />
    <g v-else-if="type === 'markers'">
      <path :d="straight" class="cti__stroke cti__stroke--thin" />
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="1.9" class="cti__ring" />
    </g>
    <g v-else-if="type === 'area'">
      <path :d="closeArea(smooth)" :fill="`url(#${uid}-g)`" />
      <path :d="smooth" class="cti__stroke" />
    </g>
    <g v-else-if="type === 'baseline'">
      <line x1="2" :x2="W - 2" :y1="meanY" :y2="meanY" class="cti__mean" />
      <g :clip-path="`url(#${uid}-top)`">
        <path :d="toMean(smooth)" :fill="RISE" fill-opacity="0.22" />
        <path :d="smooth" class="cti__stroke" :stroke="RISE" />
      </g>
      <g :clip-path="`url(#${uid}-bot)`">
        <path :d="toMean(smooth)" :fill="FALL" fill-opacity="0.22" />
        <path :d="smooth" class="cti__stroke" :stroke="FALL" />
      </g>
    </g>
    <g v-else-if="type === 'column'">
      <rect v-for="(p, i) in pts" :key="i" :x="p.x - 2.1" :y="p.y" width="4.2" :height="H - 2 - p.y" rx="1.3" fill="currentColor" />
    </g>
    <g v-else-if="type === 'lollipop'">
      <line v-for="(p, i) in pts" :key="`s${i}`" :x1="p.x" :x2="p.x" :y1="H - 2" :y2="p.y" stroke="currentColor" stroke-opacity="0.5" stroke-width="1" />
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="2.2" fill="currentColor" />
    </g>
    <g v-else-if="type === 'dots'">
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="2" fill="currentColor" />
      <circle v-for="(p, i) in pts.slice(1, 6)" :key="`b${i}`" :cx="p.x + 3" :cy="p.y + 4" r="1.4" fill="currentColor" fill-opacity="0.45" />
    </g>
    <g v-else-if="type === 'candles' || type === 'hollow' || type === 'heikin'">
      <g v-for="(c, i) in candles" :key="i" :color="c.up ? RISE : FALL">
        <line :x1="c.x" :x2="c.x" :y1="c.hi" :y2="c.lo" stroke="currentColor" stroke-width="1" />
        <rect :x="c.x - 2" :y="c.top" width="4" :height="Math.max(1.2, c.bottom - c.top)" rx="0.8" :fill="type === 'hollow' && c.up ? 'var(--cti-hollow, #fff)' : 'currentColor'" stroke="currentColor" stroke-width="1" />
      </g>
    </g>
    <g v-else-if="type === 'highlow'">
      <g v-for="(c, i) in candles" :key="i">
        <rect :x="c.x - 1.6" :y="c.hi" width="3.2" :height="c.lo - c.hi" rx="1.6" fill="currentColor" fill-opacity="0.75" />
        <circle :cx="c.x" :cy="c.up ? c.top : c.bottom" r="1.5" class="cti__ring" />
      </g>
    </g>
    <g v-else-if="type === 'ring'">
      <circle cx="22" cy="14" r="10" fill="none" stroke="currentColor" stroke-opacity="0.18" stroke-width="3.5" />
      <circle cx="22" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="44 63" transform="rotate(-90 22 14)" />
    </g>
    <g v-else-if="type === 'compare'">
      <rect x="4" y="7" width="34" height="5" rx="2.5" fill="currentColor" />
      <rect x="4" y="16" width="24" height="5" rx="2.5" fill="currentColor" fill-opacity="0.3" />
    </g>
  </svg>
</template>

<style scoped>
.cti {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.cti__stroke {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.cti__stroke--thin {
  stroke-width: 1.2;
  stroke-opacity: 0.7;
}
.cti__ring {
  fill: var(--cti-hollow, #fff);
  stroke: currentColor;
  stroke-width: 1.2;
}
.cti__mean {
  stroke: var(--p-text-muted-color);
  stroke-width: 0.8;
  stroke-dasharray: 2 2;
}
</style>
