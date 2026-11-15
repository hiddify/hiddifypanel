<script setup lang="ts">
/**
 * A tiny drawing of a chart type for the style window: the same seven points as a line, a fill, bars or candles.
 * ``live``: the drawing itself moves (its points rise and fall, bars grow, candles change, the ring fills), drawn as
 * SVG animations of the shapes, not a wiggle of the whole icon.
 */
import { computed, h } from 'vue'
import { FALL, RISE } from '../composables/useChartStyle'

const props = defineProps<{ type: string; color: string; live?: boolean }>()

const W = 44
const H = 28
/** Three sets of the same seven points: the live drawing moves from one to the next and back */
const FRAMES = [
  [9, 15, 11, 19, 14, 22, 17],
  [12, 10, 17, 13, 20, 15, 21],
  [7, 17, 13, 16, 18, 13, 23],
]
const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
const moving = computed(() => props.live && !reduced)

type Pt = { x: number; y: number }
const ptsOf = (data: number[]): Pt[] => data.map((v, i) => ({ x: 4 + i * 6, y: H - 2 - v }))
const frames = FRAMES.map(ptsOf)
const pts = frames[0]!
const mean = FRAMES[0]!.reduce((a, b) => a + b, 0) / 7
const meanY = H - 2 - mean
const uid = `cti-${Math.random().toString(36).slice(2, 8)}`

const straightOf = (p: Pt[]) => p.map((q, i) => `${i ? 'L' : 'M'}${q.x},${q.y}`).join(' ')
/** Catmull-Rom through the points as cubic Béziers */
const smoothOf = (p: Pt[]) =>
  p
    .map((q, i) => {
      if (!i) return `M${q.x},${q.y}`
      const p0 = p[i - 2] ?? p[i - 1]!
      const p1 = p[i - 1]!
      const p3 = p[i + 1] ?? q
      const c1 = { x: p1.x + (q.x - p0.x) / 6, y: p1.y + (q.y - p0.y) / 6 }
      const c2 = { x: q.x - (p3.x - p1.x) / 6, y: q.y - (p3.y - p1.y) / 6 }
      return `C${c1.x.toFixed(1)},${c1.y.toFixed(1)} ${c2.x.toFixed(1)},${c2.y.toFixed(1)} ${q.x},${q.y}`
    })
    .join(' ')
const stepOf = (p: Pt[]) => p.map((q, i) => (i ? `H${(p[i - 1]!.x + q.x) / 2} V${q.y} H${q.x}` : `M${q.x},${q.y}`)).join(' ')
const closeOf = (d: string) => `${d} L${pts[6]!.x},${H - 2} L${pts[0]!.x},${H - 2} Z`
const toMeanOf = (d: string) => `${d} L${pts[6]!.x},${meanY} L${pts[0]!.x},${meanY} Z`

/** The shape's value in each frame, for an <animate> (back to the first to loop smoothly) */
const seq = (make: (p: Pt[], f: number) => string | number) => [...frames, frames[0]!].map((p, f) => make(p, f % 3)).join(';')

/** One SVG animation of an attribute through the frames; nothing when still */
const Anim = (p: { attr: string; values: string; dur?: number; delay?: number }) =>
  moving.value
    ? h('animate', {
        attributeName: p.attr,
        values: p.values,
        dur: `${p.dur ?? 2.8}s`,
        begin: `${-(p.delay ?? 0)}s`,
        repeatCount: 'indefinite',
        calcMode: 'spline',
        keyTimes: '0;0.33;0.66;1',
        keySplines: '0.45 0 0.55 1;0.45 0 0.55 1;0.45 0 0.55 1',
      })
    : null

// --- candles: three frames each, every candle breathing on its own ---------------------------------------------
const CANDLE_BASE = [
  { o: 10, c: 16, h: 18, l: 8 },
  { o: 16, c: 12, h: 17, l: 10 },
  { o: 12, c: 19, h: 21, l: 11 },
  { o: 19, c: 15, h: 20, l: 13 },
  { o: 15, c: 22, h: 24, l: 14 },
  { o: 22, c: 18, h: 23, l: 16 },
]
const HEIKIN_BASE = [
  { o: 9, c: 13, h: 14, l: 8 },
  { o: 11, c: 16, h: 17, l: 10 },
  { o: 14, c: 20, h: 22, l: 13 },
  { o: 18, c: 15, h: 19, l: 13 },
  { o: 16, c: 13, h: 17, l: 11 },
  { o: 14, c: 19, h: 21, l: 13 },
]
const SHIFT = [0, 2.5, -2]
const candles = computed(() =>
  (props.type === 'heikin' ? HEIKIN_BASE : CANDLE_BASE).map((c, i) => {
    const x = 6 + i * 6.4
    const up = c.c >= c.o
    const at = (f: number) => {
      const s = SHIFT[(f + i) % 3]!
      const stretch = 1 + ((f + i) % 3) * 0.18
      const mid = (c.o + c.c) / 2 + s
      const half = (Math.abs(c.c - c.o) / 2) * stretch
      return { top: H - 2 - (mid + half), bottom: H - 2 - (mid - half), hi: H - 2 - (c.h + s + 1), lo: H - 2 - (c.l + s - 1) }
    }
    const f0 = at(0)
    const each = (key: 'top' | 'bottom' | 'hi' | 'lo' | 'height') => [0, 1, 2, 0].map((f) => (key === 'height' ? Math.max(1.2, at(f).bottom - at(f).top) : at(f)[key]).toFixed(2)).join(';')
    return { x, up, ...f0, each }
  }),
)
</script>

<template>
  <svg class="cti" :class="{ 'cti--live': moving }" :viewBox="`0 0 ${W} ${H}`" :style="{ color }" aria-hidden="true">
    <defs>
      <linearGradient :id="`${uid}-g`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="currentColor" stop-opacity="0.45" />
        <stop offset="100%" stop-color="currentColor" stop-opacity="0.04" />
      </linearGradient>
      <clipPath :id="`${uid}-top`"><rect x="0" y="0" :width="W" :height="meanY" /></clipPath>
      <clipPath :id="`${uid}-bot`"><rect x="0" :y="meanY" :width="W" :height="H - meanY" /></clipPath>
    </defs>

    <path v-if="type === 'line'" :d="straightOf(pts)" class="cti__stroke"><Anim attr="d" :values="seq(straightOf)" /></path>
    <path v-else-if="type === 'smooth'" :d="smoothOf(pts)" class="cti__stroke"><Anim attr="d" :values="seq(smoothOf)" /></path>
    <path v-else-if="type === 'step'" :d="stepOf(pts)" class="cti__stroke"><Anim attr="d" :values="seq(stepOf)" /></path>
    <g v-else-if="type === 'markers'">
      <path :d="straightOf(pts)" class="cti__stroke cti__stroke--thin"><Anim attr="d" :values="seq(straightOf)" /></path>
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="1.9" class="cti__ring"><Anim attr="cy" :values="seq((q) => q[i]!.y)" /></circle>
    </g>
    <g v-else-if="type === 'area'">
      <path :d="closeOf(smoothOf(pts))" :fill="`url(#${uid}-g)`"><Anim attr="d" :values="seq((q) => closeOf(smoothOf(q)))" /></path>
      <path :d="smoothOf(pts)" class="cti__stroke"><Anim attr="d" :values="seq(smoothOf)" /></path>
    </g>
    <g v-else-if="type === 'baseline'">
      <line x1="2" :x2="W - 2" :y1="meanY" :y2="meanY" class="cti__mean" />
      <g :clip-path="`url(#${uid}-top)`">
        <path :d="toMeanOf(smoothOf(pts))" :fill="RISE" fill-opacity="0.22"><Anim attr="d" :values="seq((q) => toMeanOf(smoothOf(q)))" /></path>
        <path :d="smoothOf(pts)" class="cti__stroke" :stroke="RISE"><Anim attr="d" :values="seq(smoothOf)" /></path>
      </g>
      <g :clip-path="`url(#${uid}-bot)`">
        <path :d="toMeanOf(smoothOf(pts))" :fill="FALL" fill-opacity="0.22"><Anim attr="d" :values="seq((q) => toMeanOf(smoothOf(q)))" /></path>
        <path :d="smoothOf(pts)" class="cti__stroke" :stroke="FALL"><Anim attr="d" :values="seq(smoothOf)" /></path>
      </g>
    </g>
    <g v-else-if="type === 'column'">
      <rect v-for="(p, i) in pts" :key="i" :x="p.x - 2.1" :y="p.y" width="4.2" :height="H - 2 - p.y" rx="1.3" fill="currentColor">
        <Anim attr="y" :values="seq((q) => q[i]!.y)" :dur="2.4" />
        <Anim attr="height" :values="seq((q) => H - 2 - q[i]!.y)" :dur="2.4" />
      </rect>
    </g>
    <g v-else-if="type === 'lollipop'">
      <line v-for="(p, i) in pts" :key="`s${i}`" :x1="p.x" :x2="p.x" :y1="H - 2" :y2="p.y" stroke="currentColor" stroke-opacity="0.5" stroke-width="1">
        <Anim attr="y2" :values="seq((q) => q[i]!.y)" />
      </line>
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="2.2" fill="currentColor"><Anim attr="cy" :values="seq((q) => q[i]!.y)" /></circle>
    </g>
    <g v-else-if="type === 'dots'">
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="2" fill="currentColor"><Anim attr="cy" :values="seq((q) => q[i]!.y)" /></circle>
      <circle v-for="(p, i) in pts.slice(1, 6)" :key="`b${i}`" :cx="p.x + 3" :cy="p.y + 4" r="1.4" fill="currentColor" fill-opacity="0.45">
        <Anim attr="cy" :values="seq((q) => q[i + 1]!.y + 4)" :delay="0.4" />
      </circle>
    </g>
    <g v-else-if="type === 'candles' || type === 'hollow' || type === 'heikin'">
      <g v-for="(c, i) in candles" :key="i" :color="c.up ? RISE : FALL">
        <line :x1="c.x" :x2="c.x" :y1="c.hi" :y2="c.lo" stroke="currentColor" stroke-width="1">
          <Anim attr="y1" :values="c.each('hi')" :dur="3" />
          <Anim attr="y2" :values="c.each('lo')" :dur="3" />
        </line>
        <rect :x="c.x - 2" :y="c.top" width="4" :height="Math.max(1.2, c.bottom - c.top)" rx="0.8" :fill="type === 'hollow' && c.up ? 'var(--cti-hollow, #fff)' : 'currentColor'" stroke="currentColor" stroke-width="1">
          <Anim attr="y" :values="c.each('top')" :dur="3" />
          <Anim attr="height" :values="c.each('height')" :dur="3" />
        </rect>
      </g>
    </g>
    <g v-else-if="type === 'highlow'">
      <g v-for="(c, i) in candles" :key="i">
        <rect :x="c.x - 1.6" :y="c.hi" width="3.2" :height="c.lo - c.hi" rx="1.6" fill="currentColor" fill-opacity="0.75">
          <Anim attr="y" :values="c.each('hi')" :dur="3" />
        </rect>
        <circle :cx="c.x" :cy="c.up ? c.top : c.bottom" r="1.5" class="cti__ring"><Anim attr="cy" :values="c.each(c.up ? 'top' : 'bottom')" :dur="3" /></circle>
      </g>
    </g>
    <g v-else-if="type === 'ring'">
      <circle cx="22" cy="14" r="10" fill="none" stroke="currentColor" stroke-opacity="0.18" stroke-width="3.5" />
      <circle cx="22" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="44 63" transform="rotate(-90 22 14)">
        <Anim attr="stroke-dasharray" values="44 63;60 63;28 63;44 63" :dur="3.2" />
      </circle>
    </g>
    <g v-else-if="type === 'compare'">
      <rect x="4" y="7" width="34" height="5" rx="2.5" fill="currentColor"><Anim attr="width" values="34;26;36;34" :dur="3" /></rect>
      <rect x="4" y="16" width="24" height="5" rx="2.5" fill="currentColor" fill-opacity="0.3"><Anim attr="width" values="24;32;18;24" :dur="3" /></rect>
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
