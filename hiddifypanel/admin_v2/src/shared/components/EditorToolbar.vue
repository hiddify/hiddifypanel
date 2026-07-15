<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import VariableInsertDialog from '@/shared/components/VariableInsertDialog.vue'
import TemplateIncludeMenu from '@/shared/components/TemplateIncludeMenu.vue'
import BuiltinFieldOverride from '@/shared/components/BuiltinFieldOverride.vue'
import EditorPreviewButton from '@/shared/components/EditorPreviewButton.vue'
import type { ProxyTemplate } from '@/core/api/generated'
import type { UaPreset } from '@/shared/composables/usePreviewSettings'

withDefaults(
  defineProps<{
    core?: string
    category?: string
    templateText?: string
    explicitSlugs?: string[]
    showInclude?: boolean
    readOnly?: boolean
    listScope?: 'category' | 'core'
    showOverride?: boolean
    overridden?: boolean
    overrideField?: string
    showPreview?: boolean
    requirePreviewUser?: boolean
    uaPresets?: UaPreset[]
    previewDisabled?: boolean
  }>(),
  {
    showOverride: false,
    overridden: false,
    overrideField: 'field',
    showPreview: false,
    requirePreviewUser: false,
    uaPresets: () => [],
    previewDisabled: false,
  },
)

const emit = defineEmits<{
  'insert-variable': [snippet: string]
  'insert-template': [template: ProxyTemplate]
  'update:overridden': [value: boolean]
  reset: []
  preview: [params: Record<string, unknown>]
}>()

const { t } = useI18n()
const varDialogVisible = ref(false)

function onVariable(snippet: string) {
  emit('insert-variable', snippet)
}
</script>

<template>
  <div class="editor-toolbar">
    <Button
      icon="pi pi-code"
      :label="t('editor.insertVariable')"
      severity="secondary"
      size="small"
      class="editor-toolbar-control"
      @click="varDialogVisible = true"
    />
    <TemplateIncludeMenu
      v-if="showInclude !== false"
      class="editor-toolbar-control"
      :core="core"
      :category="category"
      :template-text="templateText"
      :explicit-slugs="explicitSlugs"
      :read-only="readOnly"
      :list-scope="listScope"
      @select="emit('insert-template', $event)"
    />
    <VariableInsertDialog v-model:visible="varDialogVisible" @select="onVariable" />
    <BuiltinFieldOverride
      v-if="showOverride"
      class="editor-toolbar-control"
      :field-id="overrideField"
      :overridden="overridden"
      @update:overridden="emit('update:overridden', $event)"
      @reset="emit('reset')"
    />
    <EditorPreviewButton
      v-if="showPreview"
      class="editor-toolbar-control"
      :require-user="requirePreviewUser"
      :ua-presets="uaPresets"
      :disabled="previewDisabled"
      @preview="emit('preview', $event)"
    />
  </div>
</template>

<style scoped>
.editor-toolbar {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-width: 0;
  overflow-x: auto;
  padding-block: 0.25rem;
}

.editor-toolbar-control {
  flex: 0 0 auto;
}

.editor-toolbar :deep(.p-button) {
  flex: 0 0 auto;
  white-space: nowrap;
}

.editor-toolbar :deep(.p-inputgroup) {
  flex: 0 0 auto;
  width: auto;
}
</style>
