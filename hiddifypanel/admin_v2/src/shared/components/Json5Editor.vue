<template>
  <div class="json5-editor">
    <div ref="container" :style="{ height: height ?? '320px', width: '100%' }" />
    <p v-if="localError" class="text-red-500 text-sm mt-1 mb-0">{{ localError }}</p>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { JINJA_JSON_LANGUAGE, setupMonaco } from '@/shared/monaco/setup'
import { validateJinjaJson } from '@/shared/utils/jinja-json'

const props = defineProps<{
  modelValue: string
  height?: string
  readOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const container = ref<HTMLElement | null>(null)
const localError = ref<string | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null

function editorTheme(): string {
  return document.documentElement.classList.contains('app-dark') ? 'vs-dark' : 'vs'
}

function validateLocal(text: string) {
  localError.value = validateJinjaJson(text)
}

function insertText(text: string) {
  if (!editor || !text) return
  const selection = editor.getSelection()
  if (!selection) return
  editor.executeEdits('insert', [{ range: selection, text, forceMoveMarkers: true }])
  editor.focus()
}

defineExpose({ insertText })

onMounted(() => {
  setupMonaco()
  if (!container.value) return
  editor = monaco.editor.create(container.value, {
    value: props.modelValue ?? '',
    language: JINJA_JSON_LANGUAGE,
    theme: editorTheme(),
    readOnly: Boolean(props.readOnly),
    domReadOnly: Boolean(props.readOnly),
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    lineNumbers: 'on',
    glyphMargin: false,
    folding: false,
    renderLineHighlight: 'none',
    overviewRulerLanes: 0,
    hideCursorInOverviewRuler: true,
    scrollbar: { vertical: 'auto', horizontal: 'auto' },
  })
  editor.onDidChangeModelContent(() => {
    const v = editor!.getValue()
    emit('update:modelValue', v)
    validateLocal(v)
  })
  validateLocal(props.modelValue ?? '')
})

watch(
  () => props.readOnly,
  (readOnly) => {
    editor?.updateOptions({ readOnly: Boolean(readOnly), domReadOnly: Boolean(readOnly) })
  },
)

watch(
  () => props.modelValue,
  (v) => {
    if (editor && v !== editor.getValue()) {
      editor.setValue(v ?? '')
      validateLocal(v ?? '')
    }
  },
)

onBeforeUnmount(() => {
  editor?.dispose()
})
</script>
