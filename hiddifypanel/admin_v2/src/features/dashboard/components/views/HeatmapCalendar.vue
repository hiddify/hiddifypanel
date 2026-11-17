<script setup lang="ts">
/**
 * A calendar heatmap (like the activity grid of a fitness app): a column per week, a row per weekday, one rounded
 * square per day, darker for more. One hue, five steps (none + four quartiles of the days that had any). The readout
 * line names the day under the finger or the mouse, and the busiest day otherwise. It never grows wider than its
 * tile: the squares shrink to fit, and grow to at most about 28 px, centred.
 */
import { computed, ref } from 'vue'

const props = defineProps<{
  points: { date: string; value: number }[]
  color: string
  format: (value: number) => string
  locale: string
  /** "Busiest" line prefix, "Less" / "More" legend words */
  peakLabel: string
  lessLabel: string
  moreLabel: string
}>()

const STEP = 16 // the cell's pitch in viewBox units (a 13-unit square and a 3-unit gap)
const CELL = 13
const LEFT = 26 // room for the weekday names
const TOP = 16 // room for the month names

/** Saturday first in Persian, Monday first elsewhere */
const firstDay = computed(() => (props.locale.startsWith('fa') ? 6 : 1))
const day = (iso: string) => new Date(`${iso}T00:00:00`)

const grid = computed(() => {
  const pts = props.points
  if (!pts.length) return { cells: [], weeks: 0, months: [] as { x: number; label: string }[] }
  const start = day(pts[0]!.date)
  const offset = (start.getDay() - firstDay.value + 7) % 7
  const nonzero = pts
    .map((p) => p.value)
    .filter((v) => v > 0)
    .sort((a, b) => a - b)
  const q = (f: number) => nonzero[Math.min(nonzero.length - 1, Math.floor(f * nonzero.length))] ?? 0
  const cuts = [q(0.25), q(0.5), q(0.75)]
  const months: { x: number; label: string }[] = []
  let lastMonth = -1
  const cells = pts.map((p, i) => {
    const n = i + offset
    const col = Math.floor(n / 7)
    const row = n % 7
    const d = day(p.date)
    if (d.getMonth() !== lastMonth && row <= 3) {
      lastMonth = d.getMonth()
      months.push({ x: LEFT + col * STEP, label: d.toLocaleDateString(props.locale, { month: 'short' }) })
    }
    const level = p.value <= 0 ? 0 : p.value <= cuts[0]! ? 1 : p.value <= cuts[1]! ? 2 : p.value <= cuts[2]! ? 3 : 4
    return { ...p, x: LEFT + col * STEP, y: TOP + row * STEP, level, d }
  })
  return { cells, weeks: Math.floor((pts.length - 1 + offset) / 7) + 1, months }
})

const width = computed(() => LEFT + grid.value.weeks * STEP)
const height = TOP + 7 * STEP
/** Three weekday names down the side (the 1st, 3rd and 5th row) */
const weekdays = computed(() =>
  [0, 2, 4].map((row) => {
    const d = new Date(2024, 0, 7 + ((firstDay.value + row) % 7)) // 2024-01-07 is a Sunday
    return { y: TOP + row * STEP + CELL - 2, label: d.toLocaleDateString(props.locale, { weekday: 'short' }) }
  }),
)
const fill = (level: number) => (level === 0 ? 'color-mix(in srgb, var(--p-text-color) 7%, transparent)' : `color-mix(in srgb, ${props.color} ${[0, 30, 52, 76, 100][level]}%, var(--p-content-background))`)

const picked = ref<number | null>(null)
const peak = computed(() => grid.value.cells.reduce<(typeof grid.value.cells)[number] | null>((best, c) => (!best || c.value > best.value ? c : best), null))
const readout = computed(() => {
  const c = picked.value != null ? grid.value.cells[picked.value] : peak.value
  if (!c) return ''
  const when = c.d.toLocaleDateString(props.locale, { weekday: 'short', day: 'numeric', month: 'short' })
  return `${picked.value == null ? `${props.peakLabel} · ` : ''}${when} · ${props.format(c.value)}`
})
</script>

<template>
  <div class="hm">
    <p class="hm__readout" aria-live="polite">{{ readout }}</p>
    <svg class="hm__grid" :viewBox="`0 0 ${width} ${height}`" :style="{ maxWidth: `${width * 2.2}px` }" role="img" :aria-label="readout" @mouseleave="picked = null">
      <text v-for="m in grid.months" :key="`m${m.x}`" :x="m.x" y="10" class="hm__label">{{ m.label }}</text>
      <text v-for="w in weekdays" :key="`w${w.y}`" x="0" :y="w.y" class="hm__label">{{ w.label }}</text>
      <rect
        v-for="(c, i) in grid.cells"
        :key="c.date"
        :x="c.x"
        :y="c.y"
        :width="CELL"
        :height="CELL"
        rx="3.5"
        :fill="fill(c.level)"
        class="hm__cell"
        :class="{ 'hm__cell--on': picked === i }"
        :style="{ animationDelay: `${Math.min(i * 6, 600)}ms` }"
        @mouseenter="picked = i"
        @click="picked = picked === i ? null : i"
      />
    </svg>
    <div class="hm__legend" aria-hidden="true">
      <span>{{ lessLabel }}</span>
      <i v-for="l in 5" :key="l" :style="{ background: fill(l - 1) }" />
      <span>{{ moreLabel }}</span>
    </div>
  </div>
</template>

<style scoped>
.hm {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
.hm__readout {
  min-height: 1.25rem;
  margin: 0;
  color: var(--p-text-color);
  font-size: 0.85rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.hm__grid {
  display: block;
  width: 100%;
  /* a short range (a few weeks) stays in the middle of the tile, its squares at most about 28 px */
  margin-inline: auto;
  height: auto;
  overflow: visible;
}
.hm__label {
  fill: var(--p-text-muted-color);
  font-size: 7px;
}
.hm__cell {
  cursor: pointer;
  transform-box: fill-box;
  transform-origin: center;
  animation: hm-in 0.45s cubic-bezier(0.32, 0.72, 0, 1) both;
  transition: stroke 0.15s;
}
.hm__cell--on {
  stroke: var(--p-text-color);
  stroke-width: 1.5;
}
@keyframes hm-in {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
}
.hm__legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  color: var(--p-text-muted-color);
  font-size: 0.7rem;
}
.hm__legend i {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 0.2rem;
}
.hm__legend span {
  margin-inline: 0.25rem;
}
@media (prefers-reduced-motion: reduce) {
  .hm__cell {
    animation: none;
  }
}
</style>
