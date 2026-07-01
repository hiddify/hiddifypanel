<script setup lang="ts">
import { ref } from 'vue'
import EditorToolbar from '@/shared/components/EditorToolbar.vue'
import Json5Editor from '@/shared/components/Json5Editor.vue'
import JinjaTextEditor from '@/shared/components/JinjaTextEditor.vue'
import type { ProxyTemplate } from '@/core/api/generated'
import type { UaPreset } from '@/shared/composables/usePreviewSettings'

const props = withDefaults(
  defineProps<{
    modelValue: string
    variant?: 'json' | 'plain'
    height?: string
    rows?: number
    core?: string
    category?: string
    explicitSlugs?: string[]
    showToolbar?: boolean
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
    variant: 'json',
    showToolbar: true,
    showInclude: true,
    listScope: 'category',
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
  'update:modelValue': [value: string]
  'update:overridden': [value: boolean]
  'insert-template': [template: ProxyTemplate]
  reset: []
  focus: []
  preview: [params: Record<string, unknown>]
}>()

const editorRef = ref<{ insertText: (text: string) => void } | null>(null)

function insertSnippet(snippet: string) {
  editorRef.value?.insertText(snippet)
}

function onTemplate(tpl: ProxyTemplate) {
  emit('insert-template', tpl)
}

function onEditorFocus() {
  emit('focus')
}

defineExpose({ insertText: insertSnippet })
</script>

<template>
  <div class="templated-editor flex flex-col gap-1">
    <EditorToolbar
      v-if="showToolbar"
      :core="core"
      :category="category"
      :template-text="modelValue"
      :explicit-slugs="explicitSlugs"
      :show-include="showInclude"
      :read-only="readOnly"
      :list-scope="listScope"
      :show-override="showOverride"
      :overridden="overridden"
      :override-field="overrideField"
      :show-preview="showPreview"
      :require-preview-user="requirePreviewUser"
      :ua-presets="uaPresets"
      :preview-disabled="previewDisabled"
      @insert-variable="insertSnippet"
      @insert-template="onTemplate"
      @update:overridden="emit('update:overridden', $event)"
      @reset="emit('reset')"
      @preview="emit('preview', $event)"
    />
    <div :class="{ 'builtin-content-locked': readOnly }">
      <Json5Editor
        v-if="variant === 'json'"
        ref="editorRef"
        :model-value="modelValue"
        :height="height"
        :read-only="readOnly"
        @update:model-value="emit('update:modelValue', $event)"
        @focus="onEditorFocus"
      />
      <JinjaTextEditor
        v-else
        ref="editorRef"
        :model-value="modelValue"
        :height="height"
        :rows="rows"
        :read-only="readOnly"
        @update:model-value="emit('update:modelValue', $event)"
        @focus="onEditorFocus"
      />
    </div>
  </div>
</template>

<style scoped>
.builtin-content-locked {
  opacity: 0.72;
  pointer-events: none;
}
</style>
