<template>
  <div class="jinja-text-editor">
    <div ref="container" :style="{ height: height ?? `${Math.max(rows ?? 6, 4) * 1.35}rem`, width: '100%' }" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { setupMonaco } from '@/shared/monaco/setup'

const props = defineProps<{
  modelValue: string
  rows?: number
  height?: string
  readOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const container = ref<HTMLElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null

function editorTheme(): string {
  return document.documentElement.classList.contains('app-dark') ? 'vs-dark' : 'vs'
}

onMounted(() => {
  setupMonaco()
  if (!container.value) return
  editor = monaco.editor.create(container.value, {
    value: props.modelValue ?? '',
    language: 'plaintext',
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
    renderLineHighlight: 'line',
    overviewRulerLanes: 0,
    hideCursorInOverviewRuler: true,
    scrollbar: { vertical: 'auto', horizontal: 'auto' },
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor!.getValue())
  })
})

function insertText(text: string) {
  if (!editor || !text) return
  const selection = editor.getSelection()
  if (!selection) return
  editor.executeEdits('insert', [{ range: selection, text, forceMoveMarkers: true }])
  editor.focus()
}

defineExpose({ insertText })

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
    }
  },
)

onBeforeUnmount(() => {
  editor?.dispose()
})
</script>
