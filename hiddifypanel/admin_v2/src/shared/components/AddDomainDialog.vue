<template>
  <Dialog
    :visible="visible"
    :header="t('domain.addTitle')"
    modal
    class="w-full max-w-lg"
    @update:visible="emit('update:visible', $event)"
  >
    <HorizontalField :label="t('domain.domain')" input-id="new-domain">
      <InputText id="new-domain" v-model="form.domain" class="w-full" />
    </HorizontalField>
    <HorizontalField :label="t('domain.alias')" input-id="new-alias">
      <InputText id="new-alias" v-model="form.alias" class="w-full" />
    </HorizontalField>
    <HorizontalField :label="t('domain.mode')" input-id="new-mode">
      <Select
        id="new-mode"
        v-model="form.mode"
        :options="modeOptions"
        option-label="label"
        option-value="value"
        class="w-full"
      />
    </HorizontalField>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="close" />
      <Button :label="t('common.add')" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import { domainsApi, type DomainOption } from '@/core/api/generated'

const ALL_MODES = [
  'direct-valid',
  'direct-fake',
  'direct-reality',
  'direct-dns',
  'relay-valid',
  'relay-fake',
  'relay-reality',
  'cdn',
] as const

const props = defineProps<{
  visible: boolean
  /** Restrict mode choices; first entry is the default when the dialog opens. */
  allowedModes?: string[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  created: [domain: DomainOption]
}>()

const { t } = useI18n()
const toast = useToast()
const saving = ref(false)
const form = ref({ domain: '', alias: '', mode: 'direct-valid' })

const resolvedModes = computed(() => {
  const modes = props.allowedModes?.filter(Boolean) ?? []
  return modes.length ? modes : [...ALL_MODES]
})

const modeOptions = computed(() =>
  resolvedModes.value.map((value) => ({
    label: t(`proxy.domainModeLabels.${value}`, value),
    value,
  })),
)

function defaultMode(): string {
  return resolvedModes.value[0] ?? 'direct-valid'
}

function resetForm() {
  form.value = { domain: '', alias: '', mode: defaultMode() }
}

function close() {
  emit('update:visible', false)
}

async function submit() {
  if (!form.value.domain.trim()) return
  saving.value = true
  try {
    const created = await domainsApi.create({
      domain: form.value.domain.trim(),
      alias: form.value.alias.trim() || undefined,
      mode: form.value.mode || defaultMode(),
    })
    emit('created', created)
    close()
    resetForm()
  } catch {
    toast.add({ severity: 'error', summary: t('domain.addFailed'), life: 5000 })
  } finally {
    saving.value = false
  }
}

watch(
  () => props.visible,
  (open) => {
    if (open) resetForm()
  },
)
</script>
