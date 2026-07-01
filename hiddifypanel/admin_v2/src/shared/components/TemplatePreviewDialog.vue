<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import ScrollPanel from 'primevue/scrollpanel'
import ProgressSpinner from 'primevue/progressspinner'
import LineNumberedCode from '@/shared/components/LineNumberedCode.vue'
import type { TemplatePreviewResult } from '@/core/api/generated'

const props = defineProps<{
  loading?: boolean
  result: TemplatePreviewResult | null
}>()

const visible = defineModel<boolean>('visible', { default: false })

const { t } = useI18n()

const displayText = computed(() => {
  if (!props.result) return ''
  if (props.result.skipped) return 'SKIP'
  const text = props.result.rendered ?? ''
  const trimmed = text.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return text
  }
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2)
  } catch {
    return text
  }
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    class="w-full max-w-3xl"
    :header="t('editor.previewTitle')"
  >
    <div v-if="loading" class="flex justify-center py-8">
      <ProgressSpinner style="width: 2.5rem; height: 2.5rem" />
    </div>
    <div v-else-if="result" class="flex flex-col gap-3">
      <Message v-if="result.skipped" severity="info" :closable="false">
        SKIP
      </Message>
      <Message v-else-if="result.error" severity="error" :closable="false">
        {{ result.error }}
      </Message>
      <Message v-else-if="result.ok" severity="success" :closable="false">
        {{ t('editor.previewOk') }}
      </Message>
      <Message v-else severity="warn" :closable="false">
        {{ t('editor.previewPartial') }}
      </Message>

      <ul v-if="result.warnings?.length" class="m-0 pl-4 text-sm">
        <li v-for="(warning, index) in result.warnings" :key="index">
          {{ warning.message }}
        </li>
      </ul>

      <ScrollPanel v-if="displayText" class="preview-scroll-panel" :style="{ width: '100%', height: '420px' }">
        <LineNumberedCode :text="displayText" />
      </ScrollPanel>
    </div>
  </Dialog>
</template>

<style scoped>
.preview-scroll-panel :deep(.p-scrollpanel-content) {
  user-select: text;
}
</style>
