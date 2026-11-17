<script setup lang="ts">
/**
 * The view switch of a dashboard tile: an iOS segmented control of icons, its glass thumb gliding to the chosen one.
 * Icons only (each with its name as a tooltip and for screen readers), so it stays small next to the tile's title.
 */
import { computed } from 'vue'

export interface ChartViewOption {
  value: string
  icon: string
  label: string
}

const props = defineProps<{ options: ChartViewOption[]; label: string }>()
const model = defineModel<string>({ required: true })
const index = computed(() =>
  Math.max(
    0,
    props.options.findIndex((o) => o.value === model.value),
  ),
)
</script>

<template>
  <div class="cvs" role="radiogroup" :aria-label="label" :style="{ '--n': options.length, '--i': index }">
    <span class="cvs__thumb" aria-hidden="true" />
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      class="cvs__item"
      :class="{ 'cvs__item--on': option.value === model }"
      :aria-checked="option.value === model"
      :aria-label="option.label"
      :title="option.label"
      @click="model = option.value"
    >
      <i :class="option.icon" />
    </button>
  </div>
</template>

<style scoped>
.cvs {
  --cell: 1.95rem;
  position: relative;
  display: inline-grid;
  grid-auto-flow: column;
  grid-auto-columns: var(--cell);
  flex: none;
  padding: 0.18rem;
  border-radius: 0.7rem;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
  box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
/* the glass thumb under the chosen view; it glides with the iOS curve */
.cvs__thumb {
  position: absolute;
  top: 0.18rem;
  bottom: 0.18rem;
  inset-inline-start: 0.18rem;
  width: var(--cell);
  border-radius: 0.55rem;
  background: var(--p-content-background);
  box-shadow:
    0 2px 6px -1px rgb(0 0 0 / 0.16),
    0 0 0 0.5px rgb(0 0 0 / 0.04);
  transform: translateX(calc(var(--i) * var(--cell)));
  transition: transform 0.38s cubic-bezier(0.32, 0.72, 0, 1);
}
html[dir='rtl'] .cvs__thumb {
  transform: translateX(calc(var(--i) * var(--cell) * -1));
}
.cvs__item {
  position: relative;
  display: grid;
  place-items: center;
  height: 1.7rem;
  border: 0;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition: color 0.2s;
}
.cvs__item i {
  font-size: 0.82rem;
}
.cvs__item:hover {
  color: var(--p-text-color);
}
.cvs__item--on {
  color: var(--p-primary-color);
}
.cvs__item:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
  border-radius: 0.5rem;
}
@media (prefers-reduced-motion: reduce) {
  .cvs__thumb {
    transition: none;
  }
}
</style>

<style>
/* The tile's body as its view changes: the old view fades out, the new one fades and settles in */
.cv-enter-active {
  transition:
    opacity 0.32s ease,
    transform 0.42s cubic-bezier(0.32, 0.72, 0, 1);
}
.cv-leave-active {
  transition: opacity 0.14s ease;
}
.cv-enter-from {
  opacity: 0;
  transform: translateY(6px) scale(0.985);
}
.cv-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .cv-enter-active,
  .cv-leave-active {
    transition: none;
  }
}
</style>
