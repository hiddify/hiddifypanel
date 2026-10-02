<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useRouter } from 'vue-router'
import type { RestartMode } from '@/shared/utils/restart-mode'

const mode = defineModel<RestartMode>({ required: true })

const { t } = useI18n()
const router = useRouter()

const action = computed(() => {
  switch (mode.value) {
    case 'reinstall':
      return { run: 'install', label: t('actions.reinstall'), icon: 'pi pi-refresh', text: t('applyNotice.reinstall'), danger: true }
    case 'update':
      return { run: 'update', label: t('actions.update'), icon: 'pi pi-upload', text: t('applyNotice.update'), danger: true }
    case 'apply_config':
      return { run: 'apply', label: t('actions.applyConfigs'), icon: 'pi pi-bolt', text: t('applyNotice.apply'), danger: false }
    default:
      return null
  }
})

/** The Apply page asks (when needed), runs it and shows its live progress. */
function run() {
  const current = action.value
  if (current) void router.push({ name: 'apply', query: { run: current.run } })
}
</script>

<template>
  <Transition name="apply-notice">
    <Message v-if="action" :severity="action.danger ? 'warn' : 'info'" class="mb-4" :closable="false">
      <div class="flex flex-wrap items-center justify-between gap-3 w-full">
        <span>{{ action.text }}</span>
        <div class="flex gap-2">
          <Button size="small" :icon="action.icon" :label="action.label" :severity="action.danger ? 'danger' : undefined" @click="run" />
          <Button size="small" text severity="secondary" :label="t('applyNotice.later')" @click="mode = 'nothing'" />
        </div>
      </div>
    </Message>
  </Transition>
</template>

<style scoped>
.apply-notice-enter-active,
.apply-notice-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.apply-notice-enter-from,
.apply-notice-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
