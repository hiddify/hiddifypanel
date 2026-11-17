<script setup lang="ts">
/** The network's numbers over the live window: for download and upload, the rate now, a sparkline, and its average,
 *  peak, 95th percentile and the bytes moved. */
import { computed } from 'vue'
import Sparkline from '../Sparkline.vue'

export interface NetSide {
  key: string
  label: string
  icon: string
  color: string
  values: number[]
}

const props = defineProps<{
  sides: NetSide[]
  /** Sample times (ms), the same length as the values */
  times: number[]
  labels: string[]
  rate: (bytesPerSecond: number) => string
  bytes: (bytes: number) => string
  names: { now: string; average: string; peak: string; p95: string; moved: string }
}>()

function percentile(values: number[], p: number): number {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  return sorted[Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1)]!
}

const cards = computed(() =>
  props.sides.map((side) => {
    const values = side.values
    const n = values.length
    let moved = 0
    for (let i = 1; i < n; i++) moved += (values[i]! * Math.max(0, (props.times[i] ?? 0) - (props.times[i - 1] ?? 0))) / 1000
    const peak = n ? Math.max(...values) : 0
    return {
      ...side,
      now: n ? values[n - 1]! : 0,
      rows: [
        { key: 'average', label: props.names.average, value: props.rate(n ? values.reduce((a, b) => a + b, 0) / n : 0) },
        { key: 'peak', label: props.names.peak, value: props.rate(peak) },
        { key: 'p95', label: props.names.p95, value: props.rate(percentile(values, 95)) },
        { key: 'moved', label: props.names.moved, value: props.bytes(moved) },
      ],
    }
  }),
)
const split = (text: string) => {
  const cut = text.lastIndexOf(' ')
  return cut > 0 ? [text.slice(0, cut), text.slice(cut + 1)] : [text, '']
}
</script>

<template>
  <div class="ns">
    <article v-for="card in cards" :key="card.key" class="ns__card" :style="{ '--ns-color': card.color }">
      <header class="ns__head">
        <span class="ns__badge"><i :class="card.icon" /></span>
        <span class="ns__label">{{ card.label }}</span>
        <span class="ns__now-label">{{ names.now }}</span>
      </header>
      <p class="ns__now" dir="ltr">
        {{ split(rate(card.now))[0] }}<small>{{ split(rate(card.now))[1] }}</small>
      </p>
      <Sparkline :values="card.values" :color="card.color" :height="38" :labels="labels" :formatter="rate" class="ns__spark" />
      <dl class="ns__rows">
        <div v-for="row in card.rows" :key="row.key" class="ns__row">
          <dt>{{ row.label }}</dt>
          <dd dir="ltr">{{ row.value }}</dd>
        </div>
      </dl>
    </article>
  </div>
</template>

<style scoped>
.ns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  gap: 0.75rem;
}
.ns__card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
  padding: 0.8rem 0.9rem 0.7rem;
  border-radius: 0.95rem;
  background: radial-gradient(120% 90% at 100% 0%, color-mix(in srgb, var(--ns-color) 14%, transparent), transparent 60%), color-mix(in srgb, var(--p-text-color) 3.5%, var(--p-content-background));
  animation: ns-in 0.5s cubic-bezier(0.32, 0.72, 0, 1) both;
}
.ns__card + .ns__card {
  animation-delay: 0.06s;
}
@keyframes ns-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}
.ns__head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.ns__badge {
  display: grid;
  place-items: center;
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 0.45rem;
  color: #fff;
  background: var(--ns-color);
}
.ns__badge i {
  font-size: 0.65rem;
}
.ns__label {
  flex: 1;
  font-size: 0.82rem;
  font-weight: 600;
}
.ns__now-label {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
}
.ns__now {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  text-align: start;
}
html[dir='rtl'] .ns__now {
  text-align: end;
}
.ns__now small {
  margin-inline-start: 0.3rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.ns__rows {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.4rem 0.75rem;
  margin: 0.2rem 0 0;
}
.ns__row {
  min-width: 0;
}
.ns__row dt {
  font-size: 0.66rem;
  color: var(--p-text-muted-color);
}
.ns__row dd {
  margin: 0;
  overflow: hidden;
  font-size: 0.84rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}
html[dir='rtl'] .ns__row dd {
  text-align: end;
}
@media (prefers-reduced-motion: reduce) {
  .ns__card {
    animation: none;
  }
}
</style>
