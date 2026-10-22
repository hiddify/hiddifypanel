<script setup lang="ts">
/** A numbered step's title, with its explanation behind an info toggle (short page, nothing hidden). */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps<{ number?: number; icon?: string; title: string; hint?: string }>()
const { t } = useI18n()
const open = ref(false)
</script>

<template>
  <header class="sh">
    <span class="sh__badge">
      <i v-if="icon" :class="icon" />
      <template v-else>{{ number }}</template>
    </span>
    <h3 class="sh__title">{{ title }}</h3>
    <slot name="actions" />
    <Button v-if="hint" icon="pi pi-info-circle" text rounded size="small" :aria-label="t('cleanIp.help')" :aria-expanded="open" @click="open = !open" />
  </header>
  <Transition name="sh-fade">
    <p v-if="hint && open" class="sh__hint">{{ hint }}</p>
  </Transition>
</template>

<style scoped>
.sh {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.9rem;
}
.sh__badge {
  inline-size: 1.9rem;
  block-size: 1.9rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.sh__title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 1.05rem;
}
.sh__hint {
  margin: -0.4rem 0 0.9rem;
  padding: 0.65rem 0.8rem;
  font-size: 0.84rem;
  line-height: 1.6;
  color: var(--p-text-muted-color);
  border-radius: 0.6rem;
  background: var(--p-content-hover-background);
}
.sh-fade-enter-active,
.sh-fade-leave-active {
  transition: opacity 0.15s ease;
}
.sh-fade-enter-from,
.sh-fade-leave-to {
  opacity: 0;
}
</style>
