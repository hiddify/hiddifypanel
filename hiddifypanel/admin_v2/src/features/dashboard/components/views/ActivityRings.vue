<script setup lang="ts">
/**
 * Activity rings, as on a watch: one ring per reading (outermost first), each closed in proportion to the largest
 * reading, so the readings compare at a glance. The legend beside them names each ring with its value (identity
 * never rests on colour alone). The rings draw themselves in when shown.
 */
import { computed, onMounted, ref } from 'vue'

const props = defineProps<{ items: { label: string; value: number; color: string }[]; format: (value: number) => string }>()

const SIZE = 150
const STROKE = 13
const GAP = 4
const max = computed(() => Math.max(...props.items.map((i) => i.value), 0))
const rings = computed(() =>
  props.items.slice(0, 4).map((item, i) => {
    const r = SIZE / 2 - STROKE / 2 - i * (STROKE + GAP)
    const length = 2 * Math.PI * r
    const share = max.value ? item.value / max.value : 0
    return { ...item, r, length, share }
  }),
)
const shown = ref(false)
onMounted(() => requestAnimationFrame(() => requestAnimationFrame(() => (shown.value = true))))
</script>

<template>
  <div class="ar">
    <svg class="ar__rings" :viewBox="`0 0 ${SIZE} ${SIZE}`" role="img" :aria-label="items.map((i) => `${i.label} ${format(i.value)}`).join(', ')">
      <g v-for="(ring, i) in rings" :key="ring.label" :style="{ '--c': ring.color }">
        <circle :cx="SIZE / 2" :cy="SIZE / 2" :r="ring.r" class="ar__track" :stroke-width="STROKE" />
        <circle
          :cx="SIZE / 2"
          :cy="SIZE / 2"
          :r="ring.r"
          class="ar__ring"
          :stroke-width="STROKE"
          :stroke-dasharray="ring.length"
          :stroke-dashoffset="shown ? ring.length * (1 - Math.max(ring.share, 0.012)) : ring.length"
          :style="{ transitionDelay: `${i * 90}ms` }"
          :transform="`rotate(-90 ${SIZE / 2} ${SIZE / 2})`"
        />
      </g>
    </svg>
    <ul class="ar__legend">
      <li v-for="ring in rings" :key="ring.label">
        <span class="ar__dot" :style="{ background: ring.color }" />
        <span class="ar__name">{{ ring.label }}</span>
        <b class="ar__value">{{ format(ring.value) }}</b>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  align-content: center;
  justify-content: center;
  /* in the middle of a tile taller than the rings (beside a taller one) */
  height: 100%;
  gap: 1rem 1.5rem;
  min-width: 0;
  padding-block: 0.25rem;
}
.ar__rings {
  flex: none;
  width: min(10rem, 46%);
  min-width: 8rem;
  height: auto;
}
.ar__track {
  fill: none;
  stroke: color-mix(in srgb, var(--c) 16%, transparent);
}
.ar__ring {
  fill: none;
  stroke: var(--c);
  stroke-linecap: round;
  transition: stroke-dashoffset 1.1s cubic-bezier(0.32, 0.72, 0, 1);
}
.ar__legend {
  display: flex;
  flex: 1 1 10rem;
  flex-direction: column;
  gap: 0.55rem;
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ar__legend li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-size: 0.85rem;
}
.ar__dot {
  flex: none;
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
}
.ar__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--p-text-muted-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ar__value {
  flex: none;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
@media (prefers-reduced-motion: reduce) {
  .ar__ring {
    transition: none;
  }
}
</style>
