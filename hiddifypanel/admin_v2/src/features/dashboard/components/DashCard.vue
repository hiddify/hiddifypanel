<script setup lang="ts">
defineProps<{
  title?: string
  subtitle?: string
  icon?: string
  /** Hex color used for the icon halo and the top accent line. */
  accent?: string
  loading?: boolean
  padded?: boolean
}>()
</script>

<template>
  <section class="dash-card" :style="accent ? { '--dash-accent': accent } : undefined">
    <div v-if="accent" class="dash-card__accent" />
    <header v-if="title || $slots.actions" class="dash-card__header">
      <div class="dash-card__heading">
        <span v-if="icon" class="dash-card__icon"><i :class="icon" /></span>
        <div class="min-w-0">
          <h3 class="dash-card__title">{{ title }}</h3>
          <p v-if="subtitle" class="dash-card__subtitle">{{ subtitle }}</p>
        </div>
      </div>
      <div v-if="$slots.actions" class="dash-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="dash-card__body" :class="{ 'dash-card__body--padded': padded }">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="dash-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.dash-card {
  --dash-accent: var(--p-primary-color);
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  background: var(--p-content-background);
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%), 0 8px 24px -18px rgb(15 23 42 / 30%);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.dash-card:hover {
  box-shadow: 0 1px 2px rgb(0 0 0 / 5%), 0 18px 36px -22px rgb(15 23 42 / 38%);
}
.dash-card__accent {
  height: 3px;
  background: linear-gradient(90deg, var(--dash-accent), color-mix(in srgb, var(--dash-accent) 25%, transparent));
}
.dash-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem 0.5rem;
}
.dash-card__heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.dash-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.75rem;
  color: var(--dash-accent);
  background: color-mix(in srgb, var(--dash-accent) 14%, transparent);
}
.dash-card__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--p-text-color);
}
.dash-card__subtitle {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.dash-card__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}
.dash-card__body {
  flex: 1;
  min-height: 0;
}
.dash-card__body--padded {
  padding: 0.5rem 1.25rem 1.25rem;
}
.dash-card__footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-text-color) 3%, transparent);
}
</style>
