<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** Percent change; `null` means there is no baseline to compare against. */
  value: number | null
  label?: string
  /** Set when growth is a bad thing (e.g. resource pressure). */
  invert?: boolean
}>()

const tone = computed(() => {
  if (props.value === null || Math.abs(props.value) < 0.05) return 'flat'
  const positive = props.value > 0
  return positive === !props.invert ? 'up' : 'down'
})

const icon = computed(() => {
  if (props.value === null || Math.abs(props.value) < 0.05) return 'pi pi-minus'
  return props.value > 0 ? 'pi pi-arrow-up-right' : 'pi pi-arrow-down-right'
})

const text = computed(() => {
  if (props.value === null) return '—'
  const rounded = Math.abs(props.value) >= 1000 ? Math.round(props.value) : props.value
  return `${props.value > 0 ? '+' : ''}${rounded}%`
})
</script>

<template>
  <span class="trend" :class="`trend--${tone}`">
    <i :class="icon" />
    <span>{{ text }}</span>
    <span v-if="label" class="trend__label">{{ label }}</span>
  </span>
</template>

<style scoped>
.trend {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
}
.trend i {
  font-size: 0.65rem;
}
.trend__label {
  font-weight: 500;
  opacity: 0.75;
}
.trend--up {
  color: var(--p-green-600);
  background: color-mix(in srgb, var(--p-green-500) 14%, transparent);
}
.trend--down {
  color: var(--p-red-500);
  background: color-mix(in srgb, var(--p-red-500) 14%, transparent);
}
.trend--flat {
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
:global(.app-dark) .trend--up {
  color: var(--p-green-400);
}
</style>
