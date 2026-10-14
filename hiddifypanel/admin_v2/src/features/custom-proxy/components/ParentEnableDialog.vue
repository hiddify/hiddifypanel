<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import { apiErrorMessage } from '@/core/api/client'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import { settingsApi, type SettingField, type SettingValue } from '@/features/settings/api'
import { parentEnablePrompt } from '@/features/custom-proxy/parent-enable'

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const fields = ref<SettingField[]>([])
const values = ref<Record<string, SettingValue>>({})
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const pendingApply = ref<RestartMode>('nothing')

const visible = computed({
  get: () => parentEnablePrompt.visible,
  set: (v: boolean) => (parentEnablePrompt.visible = v),
})

/** The value that lifts the block: on for a switch, "both" for a core choice (it serves every proxy). */
function unblockingValue(field: SettingField): SettingValue {
  if (field.type === 'bool') return true
  const both = field.choices?.find((c) => c.value === 'both')
  return both?.value ?? field.value
}

watch(
  () => parentEnablePrompt.visible,
  async (open) => {
    if (!open) return
    error.value = ''
    fields.value = []
    loading.value = true
    try {
      const keys = new Set(parentEnablePrompt.blocked.map((b) => b.key))
      const all = (await settingsApi.list()).flatMap((c) => c.fields)
      fields.value = all.filter((f) => keys.has(f.key))
      values.value = Object.fromEntries(fields.value.map((f) => [f.key, unblockingValue(f)]))
    } catch (err) {
      error.value = apiErrorMessage(err)
    } finally {
      loading.value = false
    }
  },
)

/** Every blocker is one we can set here; otherwise only the settings link is offered. */
const canQuickEnable = computed(() => fields.value.length > 0 && fields.value.length === parentEnablePrompt.blocked.length)

async function quickEnable() {
  saving.value = true
  error.value = ''
  try {
    const res = await settingsApi.update(values.value)
    pendingApply.value = strongerRestartMode(pendingApply.value, res.restart_mode)
    for (const warning of res.warnings) toast.add({ severity: 'warn', summary: warning, life: 8000 })
    await parentEnablePrompt.onEnabled?.()
    parentEnablePrompt.visible = false
    toast.add({ severity: 'success', summary: t('proxy.quickEnableDone'), life: 3000 })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    saving.value = false
  }
}

/** Opens the admin_v2 settings page in a new tab, at the first blocking setting. */
function openSettings() {
  const key = parentEnablePrompt.blocked[0]?.key
  const { href } = router.resolve({ name: 'settings', query: key ? { key } : {} })
  window.open(href, '_blank', 'noopener,noreferrer')
  parentEnablePrompt.visible = false
}
</script>

<template>
  <ApplyNotice v-model="pendingApply" />
  <Dialog v-model:visible="visible" modal :header="t('proxy.cannotEnable')" :style="{ width: '32rem' }" :breakpoints="{ '575px': '95vw' }">
    <p class="mb-3">{{ t('proxy.quickEnableHint') }}</p>
    <div v-if="loading" class="flex justify-center py-4"><i class="pi pi-spin pi-spinner text-2xl" /></div>
    <div v-else class="flex flex-col gap-3">
      <div v-for="field in fields" :key="field.key" class="flex items-center justify-between gap-3">
        <label :for="`pe-${field.key}`" class="font-medium">{{ field.label }}</label>
        <ToggleSwitch v-if="field.type === 'bool'" :input-id="`pe-${field.key}`" v-model="values[field.key] as boolean" />
        <Select
          v-else-if="field.choices?.length"
          :input-id="`pe-${field.key}`"
          v-model="values[field.key]"
          :options="field.choices"
          option-label="label"
          option-value="value"
          class="min-w-48"
        />
      </div>
      <ul v-if="!canQuickEnable" class="list-disc ps-5">
        <li v-for="b in parentEnablePrompt.blocked" :key="b.key">{{ b.label }}</li>
      </ul>
    </div>
    <Message v-if="error" severity="error" class="mt-3" :closable="false">{{ error }}</Message>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="visible = false" />
      <Button :label="t('proxy.goToSettings')" severity="secondary" text icon="pi pi-external-link" @click="openSettings" />
      <Button v-if="canQuickEnable" :label="t('proxy.quickEnable')" icon="pi pi-bolt" :loading="saving" @click="quickEnable" />
    </template>
  </Dialog>
</template>
