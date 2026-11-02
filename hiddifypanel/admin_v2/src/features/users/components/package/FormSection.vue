<script setup lang="ts">
/**
 * A card of the user forms (add, edit, add many): an icon and a title, or a header that opens and closes the card
 * (`collapsible`), with a short line of what is set inside while it is closed. One look for every user form.
 */
const props = defineProps<{ icon: string; title: string; collapsible?: boolean; summary?: string }>()
const open = defineModel<boolean>('open', { default: true })
</script>

<template>
  <section class="fsec">
    <button v-if="props.collapsible" type="button" class="fsec__toggle" :aria-expanded="open" @click="open = !open">
      <i :class="icon" />
      <span class="flex-1">{{ title }}</span>
      <i class="pi pi-angle-down fsec__caret" :class="{ 'fsec__caret--open': open }" />
    </button>
    <h4 v-else class="fsec__title"><i :class="icon" />{{ title }}<slot name="title-end" /></h4>
    <p v-if="props.collapsible && !open && summary" class="fsec__summary">{{ summary }}</p>
    <slot v-if="!props.collapsible || open" />
  </section>
</template>

<style scoped>
.fsec {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.fsec__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.fsec__title i {
  color: var(--p-primary-color);
}
.fsec__toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: start;
  cursor: pointer;
}
.fsec__toggle:hover {
  color: var(--p-primary-color);
}
.fsec__caret {
  transition: transform 0.25s ease;
}
.fsec__caret--open {
  transform: rotate(180deg);
}
.fsec__summary {
  margin: -0.35rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
@media (max-width: 640px) {
  .fsec {
    padding: 0.85rem;
  }
}
</style>
