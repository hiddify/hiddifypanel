<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps<{
  count: number
  saving?: boolean
}>()

const emit = defineEmits<{
  save: []
  discard: []
}>()

const { t } = useI18n()
</script>

<template>
  <Transition name="savebar">
    <div v-if="count > 0" class="savebar">
      <div class="savebar__inner">
        <span class="savebar__count">
          <i class="pi pi-circle-fill" />
          {{ t('saveBar.unsaved', { count }, count) }}
        </span>
        <div class="savebar__actions">
          <Button :label="t('saveBar.discard')" severity="secondary" outlined :disabled="saving" @click="emit('discard')" />
          <Button :label="t('common.save')" icon="pi pi-check" :loading="saving" @click="emit('save')" />
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.savebar {
  position: fixed;
  inset-inline: 0;
  bottom: 0;
  z-index: 50;
  display: flex;
  justify-content: center;
  padding: 0.75rem 1rem calc(0.75rem + env(safe-area-inset-bottom));
  pointer-events: none;
}
.savebar__inner {
  pointer-events: auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  width: min(100%, 44rem);
  padding: 0.75rem 1rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  box-shadow: 0 12px 32px -12px rgba(0, 0, 0, 0.35);
}
.savebar__count {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}
.savebar__count i {
  font-size: 0.55rem;
  color: var(--p-orange-400, #fb923c);
  animation: savebar-pulse 1.6s ease-in-out infinite;
}
.savebar__actions {
  display: flex;
  gap: 0.5rem;
}
@keyframes savebar-pulse {
  50% {
    opacity: 0.35;
  }
}
.savebar-enter-active,
.savebar-leave-active {
  transition:
    transform 0.28s cubic-bezier(0.2, 0.8, 0.2, 1),
    opacity 0.2s ease;
}
.savebar-enter-from,
.savebar-leave-to {
  transform: translateY(120%);
  opacity: 0;
}
@media (max-width: 640px) {
  .savebar__inner {
    border-radius: 14px;
  }
  .savebar__actions {
    flex: 1;
    justify-content: flex-end;
  }
}
@media (prefers-reduced-motion: reduce) {
  .savebar__count i {
    animation: none;
  }
}
</style>
