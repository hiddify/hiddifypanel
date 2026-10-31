<script setup lang="ts">
/** The HTML source in Monaco (the panel's code editor): highlighting, tag completion, formatting. */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Monaco } from '@/shared/monaco/monaco'
import { ensureMonaco } from '@/shared/monaco/setup'

const props = defineProps<{ modelValue: string; wrap: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { t } = useI18n()
const container = ref<HTMLElement | null>(null)
const state = ref<'loading' | 'ready' | 'error'>('loading')
let editor: Monaco.editor.IStandaloneCodeEditor | null = null
let unmounted = false

const theme = () => (document.documentElement.classList.contains('app-dark') ? 'vs-dark' : 'vs')

onMounted(async () => {
  let monaco: typeof Monaco
  try {
    monaco = await ensureMonaco()
  } catch (err) {
    console.error(err)
    state.value = 'error'
    return
  }
  if (unmounted || !container.value) return
  state.value = 'ready'
  editor = monaco.editor.create(container.value, {
    value: props.modelValue,
    language: 'html',
    theme: theme(),
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    wordWrap: props.wrap ? 'on' : 'off',
    fontSize: 13,
    tabSize: 2,
    lineNumbersMinChars: 3,
    padding: { top: 12, bottom: 12 },
    renderLineHighlight: 'gutter',
    scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
  })
  editor.onDidChangeModelContent(() => emit('update:modelValue', editor!.getValue()))
  editor.focus()
})

watch(
  () => props.modelValue,
  (value) => {
    if (editor && value !== editor.getValue()) editor.setValue(value)
  },
)
watch(
  () => props.wrap,
  (wrap) => editor?.updateOptions({ wordWrap: wrap ? 'on' : 'off' }),
)

onBeforeUnmount(() => {
  unmounted = true
  editor?.dispose()
})

defineExpose({
  format: () => editor?.getAction('editor.action.formatDocument')?.run(),
  undo: () => editor?.trigger('toolbar', 'undo', null),
  redo: () => editor?.trigger('toolbar', 'redo', null),
})
</script>

<template>
  <div class="hse">
    <div ref="container" class="hse__editor" dir="ltr" />
    <div v-if="state !== 'ready'" class="hse__state">
      <i :class="state === 'loading' ? 'pi pi-spin pi-spinner' : 'pi pi-exclamation-triangle'" />
      {{ state === 'loading' ? t('settings.htmlEditor.loadingSource') : t('settings.htmlEditor.sourceFailed') }}
    </div>
  </div>
</template>

<style scoped>
.hse {
  position: relative;
  height: 100%;
}
.hse__editor {
  position: absolute;
  inset: 0;
}
.hse__state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}
</style>
