<template>
  <Panel v-if="result" ref="rootEl" :header="t('validation.title')" class="validation-panel mb-3">
    <Message v-if="result.ok" severity="success" :closable="false">{{ t('common.validationOk') }}</Message>
    <template v-else>
      <Message severity="error" :closable="false" class="mb-0">
        <div class="font-semibold mb-2">{{ t('common.validationFailed') }}</div>
        <ul class="validation-issue-list mb-0">
          <li v-for="(e, i) in result.errors" :key="'e' + i" class="validation-issue">
            <Tag v-if="e.code" severity="danger" :value="e.code" class="text-xs mr-2" />
            <span class="validation-issue-message">{{ e.message }}</span>
            <pre v-if="e.detail?.excerpt" class="validation-issue-detail">{{ e.detail.excerpt }}</pre>
          </li>
        </ul>
      </Message>
    </template>

    <Fieldset v-if="result.warnings?.length" :legend="t('validation.warnings')" class="mt-3 mb-0">
      <ul class="validation-issue-list">
        <li v-for="(w, i) in result.warnings" :key="'w' + i" class="validation-issue">
          <Tag v-if="w.code" severity="warn" :value="w.code" class="text-xs mr-2" />
          <span class="validation-issue-message">{{ w.message }}</span>
        </li>
      </ul>
    </Fieldset>
    <Fieldset v-if="result.compiled_preview" :legend="t('validation.preview')" class="mt-3 mb-0">
      <ScrollPanel class="config-scroll-panel" :style="{ width: '100%', height: '240px' }">
        <pre class="validation-preview-pre">{{ result.compiled_preview }}</pre>
      </ScrollPanel>
    </Fieldset>
  </Panel>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import Message from 'primevue/message'
import Fieldset from 'primevue/fieldset'
import Tag from 'primevue/tag'
import ScrollPanel from 'primevue/scrollpanel'
import type { ValidationResult } from '@/core/api/generated'

const props = defineProps<{
  result: ValidationResult | null
}>()

const { t } = useI18n()
const rootEl = ref<{ $el?: HTMLElement } | HTMLElement | null>(null)

function panelElement(): HTMLElement | null {
  const el = rootEl.value
  if (!el) return null
  if (el instanceof HTMLElement) return el
  return el.$el ?? null
}

async function scrollIntoView() {
  await nextTick()
  panelElement()?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(
  () => props.result,
  (result) => {
    if (result && !result.ok) void scrollIntoView()
  },
)

defineExpose({ scrollIntoView })
</script>

<style scoped>
.validation-issue-list {
  margin: 0;
  padding-inline-start: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.validation-issue-message {
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.875rem;
}

.validation-issue-detail {
  margin: 0.35rem 0 0;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--surface-ground);
  border-radius: var(--content-border-radius);
  max-height: 12rem;
  overflow: auto;
}

.validation-preview-pre {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre;
  user-select: text;
}

.config-scroll-panel :deep(.p-scrollpanel-content) {
  user-select: text;
}
</style>
