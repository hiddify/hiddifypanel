<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { openLegacyAction, systemActionUrls } from '@/core/panelShell'
import type { RestartMode } from '@/shared/utils/restart-mode'

const mode = defineModel<RestartMode>({ required: true })

const { t } = useI18n()
const dangerConfirm = useDangerConfirm()

const action = computed(() => {
  switch (mode.value) {
    case 'reinstall':
      return { url: systemActionUrls.value.reinstall, label: t('actions.reinstall'), icon: 'pi pi-refresh', text: t('applyNotice.reinstall'), danger: true }
    case 'update':
      return { url: systemActionUrls.value.update, label: t('actions.update'), icon: 'pi pi-upload', text: t('applyNotice.update'), danger: true }
    case 'apply_config':
      return { url: systemActionUrls.value.apply_configs, label: t('actions.applyConfigs'), icon: 'pi pi-bolt', text: t('applyNotice.apply'), danger: false }
    default:
      return null
  }
})

function run() {
  const current = action.value
  if (!current?.url) return
  const url = current.url
  const title = current.label
  dangerConfirm({ header: title, message: t('actions.confirm'), accept: () => openLegacyAction({ title, url, method: 'post' }) })
}
</script>

<template>
  <Transition name="apply-notice">
    <Message v-if="action" :severity="action.danger ? 'warn' : 'info'" class="mb-4" :closable="false">
      <div class="flex flex-wrap items-center justify-between gap-3 w-full">
        <span>{{ action.text }}</span>
        <div class="flex gap-2">
          <Button v-if="action.url" size="small" :icon="action.icon" :label="action.label" :severity="action.danger ? 'danger' : undefined" @click="run" />
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
