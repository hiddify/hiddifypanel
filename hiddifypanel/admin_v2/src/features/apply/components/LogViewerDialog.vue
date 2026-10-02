<script setup lang="ts">
/** Read a past log (its end), refresh it, or download all of it. */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { applyApi, formatSize, type LogFile } from '@/features/apply/api'
import TerminalView from '@/features/apply/components/TerminalView.vue'
import { AnsiParser, type AnsiSpan } from '@/shared/utils/ansi'

const props = defineProps<{ file: LogFile | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ cleared: [] }>()
const { t } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const spans = ref<AnsiSpan[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const truncated = ref(false)

async function load() {
  if (!props.file) return
  loading.value = true
  error.value = null
  try {
    const chunk = await applyApi.tail(props.file.name)
    spans.value = new AnsiParser().parse(chunk.text)
    truncated.value = chunk.size > chunk.offset - chunk.text.length + 1 && chunk.size > 64 * 1024
  } catch (err) {
    error.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}
function clear() {
  const file = props.file
  if (!file) return
  dangerConfirm({
    header: t('apply.log.clear'),
    message: t('apply.log.clearConfirm', { name: file.name }),
    acceptLabel: t('apply.log.clear'),
    accept: async () => {
      try {
        await applyApi.clear(file.name)
        spans.value = []
        toast.add({ severity: 'success', summary: t('apply.log.cleared'), life: 2500 })
        emit('cleared')
      } catch (err) {
        toast.add({ severity: 'error', summary: t('apply.log.clearFailed'), detail: apiErrorMessage(err), life: 5000 })
      }
    },
  })
}
watch(visible, (open) => {
  if (open) {
    spans.value = []
    void load()
  }
})
</script>

<template>
  <Dialog v-model:visible="visible" modal maximizable :draggable="false" :header="file?.name" :style="{ width: 'min(60rem, calc(100vw - 1.5rem))' }" :breakpoints="{ '640px': '100vw' }">
    <p v-if="file" class="lv-sub">{{ formatSize(file.size) }} · {{ new Date(file.mtime * 1000).toLocaleString() }}<template v-if="truncated"> · {{ t('apply.log.showingEnd') }}</template></p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <TerminalView :spans="spans" height="min(60vh, 34rem)" :empty="loading ? t('apply.log.loading') : undefined" />
    <template #footer>
      <Button v-if="file" :label="t('apply.log.clear')" icon="pi pi-trash" severity="danger" text @click="clear" />
      <Button :label="t('legacy.refresh')" icon="pi pi-refresh" severity="secondary" text :loading="loading" @click="load" />
      <a v-if="file" :href="applyApi.downloadUrl(file.name)" download class="lv-download"><Button :label="t('apply.log.download')" icon="pi pi-download" severity="secondary" outlined /></a>
      <Button :label="t('donation.close')" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.lv-sub {
  margin: 0 0 0.7rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.lv-download {
  text-decoration: none;
}
</style>
