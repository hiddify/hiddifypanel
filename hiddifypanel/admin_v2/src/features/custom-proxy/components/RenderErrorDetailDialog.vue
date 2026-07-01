<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import ScrollPanel from 'primevue/scrollpanel'
import Message from 'primevue/message'
import type { RenderErrorDetail } from '@/core/api/generated'
import LineNumberedCode from '@/shared/components/LineNumberedCode.vue'
import { hasRenderableErrorDetail } from '@/shared/utils/render-error-detail'

const visible = defineModel<boolean>('visible', { default: false })

const props = defineProps<{
  detail: RenderErrorDetail | null
}>()

const { t } = useI18n()

const sourceView = ref<'rendered' | 'template'>('rendered')

watch(
  () => props.detail,
  (detail) => {
    sourceView.value = detail?.template_source ? 'template' : 'rendered'
  },
  { immediate: true },
)

const dialogTitle = computed(() => {
  const label = props.detail?.label?.trim()
  return label ? t('proxy.renderErrorDetailTitle', { label }) : t('proxy.renderErrorDetail')
})

const sourceOptions = computed(() => {
  const options: Array<{ value: 'rendered' | 'template'; label: string }> = []
  if (props.detail?.source || props.detail?.excerpt) {
    options.push({ value: 'rendered', label: t('proxy.renderErrorRenderedSource') })
  }
  if (props.detail?.template_source || props.detail?.template_excerpt) {
    options.push({ value: 'template', label: t('proxy.renderErrorTemplateSource') })
  }
  return options
})

const displaySource = computed(() => {
  const detail = props.detail
  if (!detail) return ''
  if (sourceView.value === 'template') {
    return detail.template_source || detail.template_excerpt || ''
  }
  return detail.source || detail.excerpt || ''
})

const locationText = computed(() => {
  const detail = props.detail
  if (!detail?.line) return ''
  if (detail.column) {
    return `Line ${detail.line}, column ${detail.column}`
  }
  return `Line ${detail.line}`
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    append-to="body"
    class="w-full max-w-4xl"
    :header="dialogTitle"
    :draggable="false"
  >
    <div v-if="detail && hasRenderableErrorDetail(detail)" class="flex flex-col gap-3">
      <Message severity="error" :closable="false">
        {{ detail.message }}
      </Message>

      <div class="flex flex-wrap items-center gap-3 text-sm text-surface-500">
        <span v-if="detail.phase">{{ detail.phase }}</span>
        <span v-if="locationText">{{ locationText }}</span>
      </div>

      <Select
        v-if="sourceOptions.length > 1"
        v-model="sourceView"
        :options="sourceOptions"
        option-label="label"
        option-value="value"
        class="w-full max-w-sm"
      />

      <ScrollPanel class="render-error-scroll" :style="{ width: '100%', height: '420px' }">
        <LineNumberedCode :text="displaySource" :highlight-line="detail.line ?? undefined" />
      </ScrollPanel>
    </div>
    <Message v-else severity="warn" :closable="false">
      {{ detail?.message || t('proxy.renderErrorNoDetail') }}
    </Message>
  </Dialog>
</template>

<style scoped>
.render-error-scroll :deep(.p-scrollpanel-content) {
  user-select: text;
}
</style>
