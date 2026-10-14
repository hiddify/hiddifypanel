<template>
  <div class="fe">
    <div v-if="loadState !== 'ready'" class="fe-loading">
      <template v-if="loadState === 'error'"><i class="pi pi-exclamation-triangle" /> {{ t('editor.loadFailed') }}</template>
      <template v-else><i class="pi pi-spin pi-spinner" /> {{ t('editor.loading') }}</template>
    </div>
    <div ref="container" class="fe-editor" dir="ltr" />
  </div>
</template>

<script setup lang="ts">
/**
 * A file of the SSH server in the editor the panel's other editors use (Monaco, shared/monaco): the language is picked from the
 * file's name, Ctrl/⌘+S saves.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Monaco } from '@/shared/monaco/monaco'
import { ensureMonaco } from '@/shared/monaco/setup'

const props = defineProps<{ modelValue: string; path: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; save: [] }>()

const { t } = useI18n()
const container = ref<HTMLElement | null>(null)
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
let editor: Monaco.editor.IStandaloneCodeEditor | null = null
let unmounted = false

/** By file name: what Monaco knows (others are plain text). */
const BY_NAME: [RegExp, string][] = [
  [/\.(json|json5)$/i, 'json'],
  [/\.(ya?ml)$/i, 'yaml'],
  [/\.(sh|bash|zsh|env)$|(^|\/)\.(bashrc|profile|bash_profile|zshrc)$/i, 'shell'],
  [/\.py$/i, 'python'],
  [/\.(js|mjs|cjs)$/i, 'javascript'],
  [/\.ts$/i, 'typescript'],
  [/\.(html?|j2)$/i, 'html'],
  [/\.css$/i, 'css'],
  [/\.(ini|cfg|conf|toml|service|timer)$/i, 'ini'],
  [/(^|\/)nginx[^/]*\.conf$|\.nginx$/i, 'nginx'],
  [/\.xml$/i, 'xml'],
  [/\.(md|markdown)$/i, 'markdown'],
  [/\.sql$/i, 'sql'],
  [/(^|\/)Dockerfile$/i, 'dockerfile'],
  [/\.go$/i, 'go'],
  [/\.lua$/i, 'lua'],
]

function languageOf(monaco: typeof Monaco, path: string): string {
  const known = new Set(monaco.languages.getLanguages().map((l) => l.id))
  for (const [pattern, id] of BY_NAME) if (pattern.test(path) && known.has(id)) return id
  return 'plaintext'
}

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
    value: props.modelValue,
    language: languageOf(monaco, props.path),
    theme: editorTheme(),
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: 13,
    tabSize: 2,
    renderWhitespace: 'boundary',
  })
  editor.onDidChangeModelContent(() => emit('update:modelValue', editor!.getValue()))
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => emit('save'))
  editor.focus()
})

watch(
  () => props.modelValue,
  (v) => {
    if (editor && v !== editor.getValue()) editor.setValue(v)
  },
)

onBeforeUnmount(() => {
  unmounted = true
  editor?.dispose()
})
</script>

<style scoped>
.fe {
  position: relative;
  height: 100%;
  min-height: 18rem;
}
.fe-editor {
  height: 100%;
  min-height: 18rem;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--p-content-border-color);
}
.fe-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}
</style>
