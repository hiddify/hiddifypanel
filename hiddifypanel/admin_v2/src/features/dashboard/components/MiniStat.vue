<script setup lang="ts">
defineProps<{
  label: string
  value: string
  accent?: string
  icon?: string
}>()
</script>

<template>
  <div class="mini" :style="accent ? { '--mini-accent': accent } : undefined">
    <span v-if="icon" class="mini__icon"><i :class="icon" /></span>
    <span v-else-if="accent" class="mini__dot" />
    <div class="min-w-0">
      <p class="mini__label">{{ label }}</p>
      <p class="mini__value">{{ value }}</p>
    </div>
  </div>
</template>

<style scoped>
.mini {
  --mini-accent: var(--p-primary-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.mini__dot {
  width: 0.55rem;
  height: 0.55rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--mini-accent);
}
.mini__icon {
  flex-shrink: 0;
  color: var(--mini-accent);
  font-size: 0.8rem;
}
.mini__label {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.mini__value {
  margin: 0.1rem 0 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
