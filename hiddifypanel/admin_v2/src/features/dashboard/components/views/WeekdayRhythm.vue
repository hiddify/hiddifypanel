<script setup lang="ts">
/**
 * The week's rhythm: the average of each weekday over the range, as seven columns. The busiest weekday is in the
 * tile's colour, the others in a lighter shade of it (emphasis, one hue), so the answer to "which day is busiest?"
 * is seen at once; the readout names it, or the column under the finger or the mouse.
 */
import { computed, ref } from 'vue'

const props = defineProps<{
  points: { date: string; value: number }[]
  color: string
  format: (value: number) => string
  locale: string
  busiestLabel: string
  averageLabel: string
}>()

const firstDay = computed(() => (props.locale.startsWith('fa') ? 6 : 1))
const days = computed(() => {
  const sum = Array(7).fill(0)
  const count = Array(7).fill(0)
  for (const p of props.points) {
    const wd = new Date(`${p.date}T00:00:00`).getDay()
    sum[wd] += p.value
    count[wd] += 1
  }
  return Array.from({ length: 7 }, (_, i) => {
    const wd = (firstDay.value + i) % 7
    const d = new Date(2024, 0, 7 + wd)
    return {
      wd,
      short: d.toLocaleDateString(props.locale, { weekday: 'narrow' }),
      long: d.toLocaleDateString(props.locale, { weekday: 'long' }),
      value: count[wd] ? sum[wd] / count[wd] : 0,
    }
  })
})
const max = computed(() => Math.max(...days.value.map((d) => d.value), 0))
const busiest = computed(() => days.value.reduce((b, d) => (d.value > b.value ? d : b), days.value[0]!))

const W = 280
const H = 150
const BOTTOM = 18
const col = W / 7
const barW = col * 0.56
const bars = computed(() =>
  days.value.map((d, i) => {
    const h = max.value ? Math.max(3, (d.value / max.value) * (H - BOTTOM - 6)) : 3
    return { ...d, x: i * col + (col - barW) / 2, y: H - BOTTOM - h, h }
  }),
)
const picked = ref<number | null>(null)
const readout = computed(() => {
  const d = picked.value != null ? days.value[picked.value]! : busiest.value
  return picked.value != null ? `${d.long} · ${props.averageLabel} ${props.format(d.value)}` : `${props.busiestLabel} · ${d.long} · ${props.format(d.value)}`
})
</script>

<template>
  <div class="wr">
    <p class="wr__readout" aria-live="polite">{{ readout }}</p>
    <svg class="wr__chart" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="readout" @mouseleave="picked = null">
      <line x1="0" :x2="W" :y1="H - BOTTOM" :y2="H - BOTTOM" class="wr__base" />
      <g v-for="(b, i) in bars" :key="b.wd" class="wr__col" @mouseenter="picked = i" @click="picked = picked === i ? null : i">
        <rect :x="i * col" y="0" :width="col" :height="H" fill="transparent" />
        <path
          :d="`M${b.x} ${H - BOTTOM}V${b.y + 4}a4 4 0 0 1 4-4h${barW - 8}a4 4 0 0 1 4 4V${H - BOTTOM}z`"
          :fill="b.wd === busiest.wd ? color : `color-mix(in srgb, ${color} 34%, var(--p-content-background))`"
          class="wr__bar"
          :class="{ 'wr__bar--on': picked === i }"
          :style="{ animationDelay: `${i * 45}ms` }"
        />
        <text :x="i * col + col / 2" :y="H - 4" text-anchor="middle" class="wr__label" :class="{ 'wr__label--on': b.wd === busiest.wd }">{{ b.short }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.wr {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
.wr__readout {
  min-height: 1.25rem;
  margin: 0;
  color: var(--p-text-color);
  font-size: 0.85rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.wr__chart {
  display: block;
  width: 100%;
  max-height: 15rem;
  overflow: visible;
}
.wr__base {
  stroke: color-mix(in srgb, var(--p-text-color) 12%, transparent);
}
.wr__col {
  cursor: pointer;
}
.wr__bar {
  transform-box: fill-box;
  transform-origin: bottom;
  animation: wr-grow 0.6s cubic-bezier(0.32, 0.72, 0, 1) both;
  transition: filter 0.15s;
}
.wr__bar--on {
  filter: brightness(1.08) saturate(1.1);
}
@keyframes wr-grow {
  from {
    transform: scaleY(0);
  }
}
.wr__label {
  fill: var(--p-text-muted-color);
  font-size: 10px;
}
.wr__label--on {
  fill: var(--p-text-color);
  font-weight: 700;
}
@media (prefers-reduced-motion: reduce) {
  .wr__bar {
    animation: none;
  }
}
</style>
