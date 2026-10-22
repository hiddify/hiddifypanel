<script setup lang="ts">
/** One step of a top-to-bottom flow: its number (a check when done) on a rail joining the steps, a title, then its content. */
defineProps<{ number: number; title: string; hint?: string; done?: boolean; last?: boolean }>()
</script>

<template>
  <section class="fs" :class="{ 'fs--done': done, 'fs--last': last }">
    <div class="fs__rail">
      <span class="fs__badge">
        <i v-if="done" class="pi pi-check" />
        <template v-else>{{ number }}</template>
      </span>
    </div>
    <div class="fs__body">
      <h3 class="fs__title">{{ title }}</h3>
      <p v-if="hint" class="fs__hint">{{ hint }}</p>
      <slot />
    </div>
  </section>
</template>

<style scoped>
.fs {
  display: flex;
  gap: 0.9rem;
}
.fs__rail {
  position: relative;
  flex: none;
  display: flex;
  justify-content: center;
  inline-size: 2.1rem;
}
/* the line down to the next step */
.fs:not(.fs--last) .fs__rail::after {
  content: '';
  position: absolute;
  inset-block: 2.4rem -0.4rem;
  inset-inline-start: calc(50% - 1px);
  border-inline-start: 2px solid var(--p-content-border-color);
}
.fs--done:not(.fs--last) .fs__rail::after {
  border-color: color-mix(in srgb, var(--p-green-500) 55%, var(--p-content-border-color));
}
.fs__badge {
  position: relative;
  z-index: 1;
  inline-size: 2.1rem;
  block-size: 2.1rem;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-weight: 700;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, var(--p-content-background));
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}
.fs--done .fs__badge {
  color: #fff;
  background: var(--p-green-500);
}
.fs__body {
  flex: 1;
  min-width: 0;
  padding-bottom: 1.6rem;
}
.fs--last .fs__body {
  padding-bottom: 0;
}
.fs__title {
  margin: 0.3rem 0 0;
  font-size: 1.05rem;
}
.fs__hint {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.fs__body > :deep(:not(.fs__title):not(.fs__hint):first-of-type) {
  margin-top: 0.85rem;
}
</style>
