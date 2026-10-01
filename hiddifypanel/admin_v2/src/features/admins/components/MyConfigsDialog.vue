<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import AdditionalConfigsEditor from '@/shared/components/AdditionalConfigsEditor.vue'
import { apiErrorMessage } from '@/core/api/client'
import { adminsApi, type AdminRow } from '@/features/admins/api'
import { cleanConfigRows, configRowProblem, type AdditionalConfig } from '@/shared/utils/additional-configs'

/** The signed-in admin's own row: everything else about it is locked, but its users' configs can be changed. */
const props = defineProps<{ admin: AdminRow | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [rows: AdditionalConfig[]] }>()

const { t } = useI18n()
const rows = ref<AdditionalConfig[]>([])
const touched = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)

watch(
  visible,
  (open) => {
    if (!open) return
    rows.value = (props.admin?.additional_configs ?? []).map((row) => [...row] as AdditionalConfig)
    touched.value = false
    error.value = null
  },
  { immediate: true },
)

async function save() {
  touched.value = true
  if (rows.value.some((r) => configRowProblem(r)) || busy.value) return
  busy.value = true
  error.value = null
  try {
    emit('saved', await adminsApi.saveMyConfigs(cleanConfigRows(rows.value)))
    visible.value = false
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="!busy"
    :header="t('account.configsTitle')"
    :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div class="flex flex-col gap-3">
      <p class="m-0 text-muted-color text-sm">{{ t('account.configsSub') }}</p>
      <AdditionalConfigsEditor v-model="rows" :disabled="busy" :show-errors="touched" />
      <Message v-if="error" severity="error" :closable="false"><span class="whitespace-pre-line">{{ error }}</span></Message>
      <div class="flex justify-end gap-2">
        <Button :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button icon="pi pi-check" :label="t('account.configsSave')" :loading="busy" @click="save" />
      </div>
    </div>
  </Dialog>
</template>
