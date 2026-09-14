<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    values: number[]
    color?: string
    height?: number
    filled?: boolean
  }>(),
  { color: 'var(--p-primary-color)', height: 40, filled: true },
)

const WIDTH = 100
const gradientId = `spark-${Math.random().toString(36).slice(2, 9)}`

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
</script>

<template>
  <svg
    class="sparkline"
    :viewBox="`0 0 ${WIDTH} ${height}`"
    :style="{ height: `${height}px`, color }"
    preserveAspectRatio="none"
    aria-hidden="true"
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
</template>

<style scoped>
.sparkline {
  display: block;
  width: 100%;
}
</style>
