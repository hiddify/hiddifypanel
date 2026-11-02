<script setup lang="ts">
/** One short line under the package length: when it starts or ends. `waiting`: it starts at the first connection. */
export type TimeState = 'pending' | 'waiting' | 'running' | 'ended'
const ICON: Record<TimeState, string> = { pending: 'pi pi-replay', waiting: 'pi pi-hourglass', running: 'pi pi-calendar', ended: 'pi pi-calendar-times' }
defineProps<{ state: TimeState }>()
</script>

<template>
  <div class="ptl" :class="`ptl--${state}`">
    <i :class="ICON[state]" />
    <span class="ptl__text"><slot /></span>
    <slot name="action" />
  </div>
</template>

<style scoped>
.ptl {
  --tone: var(--p-green-600, #16a34a);
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 1.9rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.ptl > i {
  font-size: 0.8rem;
  color: var(--tone);
}
.ptl--waiting {
  --tone: var(--p-sky-500, #0ea5e9);
}
.ptl--pending {
  --tone: var(--p-amber-600, #d97706);
  color: var(--tone);
  font-weight: 600;
}
.ptl--ended {
  --tone: var(--p-red-500, #ef4444);
}
.ptl__text {
  flex: 1;
  min-width: 0;
}
.ptl__text :deep(b) {
  color: var(--p-text-color);
}
.ptl__text :deep(.ptl__late) {
  color: var(--p-red-500, #ef4444);
}
</style>
