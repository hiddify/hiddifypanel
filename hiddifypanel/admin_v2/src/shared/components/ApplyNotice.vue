<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ApplyRunDialog from '@/features/apply/components/ApplyRunDialog.vue'
import type { ApplyAction } from '@/features/apply/api'
import { ref } from 'vue'
import type { RestartMode } from '@/shared/utils/restart-mode'

const mode = defineModel<RestartMode>({ required: true })

const { t } = useI18n()
const dialogVisible = ref(false)
const dialogAction = ref<ApplyAction | null>(null)

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

/** Runs it in a dialog over this page (asks first when it is disruptive, then shows the live progress). */
function run() {
  const current = action.value
  if (!current) return
  dialogAction.value = current.run as ApplyAction
  dialogVisible.value = true
}

/** It went through: nothing is waiting to be applied any more. */
function onFinished(_action: ApplyAction, ok: boolean) {
  if (ok) mode.value = 'nothing'
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
  <ApplyRunDialog v-model:visible="dialogVisible" :action="dialogAction" @finished="onFinished" />
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
