<template>
  <div class="jinja-text-editor">
    <div v-if="loadState !== 'ready'" class="monaco-loading" :class="{ 'monaco-loading--error': loadState === 'error' }">
      <template v-if="loadState === 'error'"><i class="pi pi-exclamation-triangle" /> {{ t('editor.loadFailed') }}</template>
      <template v-else><i class="pi pi-spin pi-spinner" /> {{ t('editor.loading') }}</template>
    </div>
    <div ref="container" dir="ltr" :style="{ minHeight: height ?? `${Math.max(rows ?? 6, 4) * 1.35}rem`, width: '100%' }" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Monaco } from '@/shared/monaco/monaco'
import { ensureMonaco } from '@/shared/monaco/setup'
import { fitEditorToContent } from '@/shared/monaco/fitContent'

const props = defineProps<{
  modelValue: string
  rows?: number
  height?: string
  readOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  focus: []
}>()

const { t } = useI18n()
const container = ref<HTMLElement | null>(null)
/** Monaco loads on first use (see shared/monaco/monaco.ts). */
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
let editor: Monaco.editor.IStandaloneCodeEditor | null = null
let unmounted = false
let stopFitting: (() => void) | null = null

function editorTheme(): string {
  return document.documentElement.classList.contains('app-dark') ? 'vs-dark' : 'vs'
}

onMounted(async () => {
  let monaco: typeof Monaco
  try {
    monaco = await ensureMonaco()
  } catch (err) {
    console.error(err)
    loadState.value = 'error'
    return
  }
  if (unmounted || !container.value) return
  loadState.value = 'ready'
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
    scrollbar: { vertical: 'auto', horizontal: 'auto', alwaysConsumeMouseWheel: false },
  })
  stopFitting = fitEditorToContent(editor, container.value)
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor!.getValue())
  })
  editor.onDidFocusEditorWidget(() => {
    emit('focus')
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
  unmounted = true
  stopFitting?.()
  editor?.dispose()
})
</script>

<style scoped>
.monaco-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.monaco-loading--error {
  color: var(--p-red-500, #ef4444);
}
</style>

