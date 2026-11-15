<script setup lang="ts">
/**
 * Ranked bars: one row per item, largest first, one hue (the largest in full colour, the rest lighter), the name and
 * the value written on the row. Bars on one baseline compare closer values more exactly than slices or rings.
 */
import { computed, onMounted, ref } from 'vue'

const props = defineProps<{ items: { label: string; value: number; hint?: string }[]; color: string; format: (value: number) => string }>()

const rows = computed(() => [...props.items].sort((a, b) => b.value - a.value))
const max = computed(() => Math.max(...props.items.map((i) => i.value), 0))
const shown = ref(false)
onMounted(() => requestAnimationFrame(() => requestAnimationFrame(() => (shown.value = true))))
</script>

<template>
  <ol class="rb">
    <li v-for="(row, i) in rows" :key="row.label" class="rb__row">
      <div class="rb__text">
        <span class="rb__name"
          >{{ row.label }}<small v-if="row.hint">{{ row.hint }}</small></span
        >
        <b class="rb__value">{{ format(row.value) }}</b>
      </div>
      <div class="rb__track">
        <span
          class="rb__bar"
          :style="{
            width: shown && max ? `${Math.max(1.5, (row.value / max) * 100)}%` : '0%',
            background: i === 0 ? color : `color-mix(in srgb, ${color} 45%, var(--p-content-background))`,
            transitionDelay: `${i * 70}ms`,
          }"
        />
      </div>
    </li>
  </ol>
</template>

<style scoped>
.rb {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  gap: 0.8rem;
  min-width: 0;
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
}
.rb__text {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.3rem;
  font-size: 0.85rem;
}
.rb__name {
  min-width: 0;
  overflow: hidden;
  color: var(--p-text-muted-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rb__name small {
  margin-inline-start: 0.35rem;
  opacity: 0.8;
}
.rb__value {
  flex: none;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.rb__track {
  height: 0.6rem;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.rb__bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.9s cubic-bezier(0.32, 0.72, 0, 1);
}
@media (prefers-reduced-motion: reduce) {
  .rb__bar {
    transition: none;
  }
}
</style>
