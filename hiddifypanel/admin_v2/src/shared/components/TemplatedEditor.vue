<script setup lang="ts">
import { ref } from 'vue'
import EditorToolbar from '@/shared/components/EditorToolbar.vue'
import Json5Editor from '@/shared/components/Json5Editor.vue'
import JinjaTextEditor from '@/shared/components/JinjaTextEditor.vue'
import type { ProxyTemplate } from '@/core/api/generated'

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
  }>(),
  {
    variant: 'json',
    showToolbar: true,
    showInclude: true,
    listScope: 'category',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'insert-template': [template: ProxyTemplate]
}>()

const editorRef = ref<{ insertText: (text: string) => void } | null>(null)

function insertSnippet(snippet: string) {
  editorRef.value?.insertText(snippet)
}

function onTemplate(tpl: ProxyTemplate) {
  emit('insert-template', tpl)
}
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
      @insert-variable="insertSnippet"
      @insert-template="onTemplate"
    />
    <Json5Editor
      v-if="variant === 'json'"
      ref="editorRef"
      :model-value="modelValue"
      :height="height"
      :read-only="readOnly"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <JinjaTextEditor
      v-else
      ref="editorRef"
      :model-value="modelValue"
      :height="height"
      :rows="rows"
      :read-only="readOnly"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </div>
</template>
