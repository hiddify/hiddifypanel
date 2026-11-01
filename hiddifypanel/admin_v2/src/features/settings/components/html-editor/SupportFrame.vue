<script setup lang="ts">
/**
 * The user page's support box in a sandboxed iframe (``allow-same-origin`` only: the panel edits it, nothing in it runs).
 * ``editable``: the text is edited in place and every change is emitted.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { caretBlock, frameDocument } from './support-frame'

const props = defineProps<{ html: string; editable?: boolean }>()
const emit = defineEmits<{ 'update:html': [value: string]; selectionchange: [] }>()

const { t } = useI18n()
const frame = ref<HTMLIFrameElement | null>(null)
const dir = (document.documentElement.getAttribute('dir') === 'rtl' ? 'rtl' : 'ltr') as 'ltr' | 'rtl'
const srcdoc = computed(() =>
  frameDocument({ title: t('settings.htmlEditor.boxTitle'), more: t('settings.htmlEditor.boxMore'), placeholder: t('settings.htmlEditor.placeholder') }, dir, Boolean(props.editable)),
)

let content: HTMLElement | null = null
let lastEmitted: string | null = null

function onInput(event?: Event) {
  if (!content) return
  // Enter at the end of a styled block (a box, a coloured line): the browser repeats it; the new empty line starts plain
  const doc = frame.value?.contentDocument
  if (doc && (event as InputEvent | undefined)?.inputType === 'insertParagraph') {
    const block = caretBlock(doc, content)
    const before = block?.previousElementSibling
    if (block && before && !block.textContent?.trim() && block.hasAttribute('style') && block.getAttribute('style') === before.getAttribute('style')) {
      const p = doc.createElement('p')
      p.innerHTML = '<br>'
      block.replaceWith(p)
      const range = doc.createRange()
      range.setStart(p, 0)
      range.collapse(true)
      doc.getSelection()?.removeAllRanges()
      doc.getSelection()?.addRange(range)
    }
  }
  lastEmitted = content.innerHTML
  emit('update:html', lastEmitted)
}

function onLoad() {
  const doc = frame.value?.contentDocument
  content = doc?.getElementById('content') ?? null
  if (!doc || !content) return
  content.innerHTML = props.html
  if (!props.editable) return
  doc.execCommand('styleWithCSS', false, 'true')
  doc.execCommand('defaultParagraphSeparator', false, 'p')
  content.addEventListener('input', onInput)
  doc.addEventListener('selectionchange', () => emit('selectionchange'))
}

watch(
  () => props.html,
  (value) => {
    // its own edits come back through v-model: rewriting them would move the caret
    if (content && value !== lastEmitted && value !== content.innerHTML) content.innerHTML = value
  },
)

onBeforeUnmount(() => content?.removeEventListener('input', onInput))

defineExpose({
  document: () => frame.value?.contentDocument ?? null,
  content: () => content,
  /** after a change made by the panel (a command, an inserted block): tell v-model */
  sync: () => onInput(),
})
</script>

<template>
  <iframe ref="frame" class="support-frame" sandbox="allow-same-origin" :srcdoc="srcdoc" :title="t('settings.htmlEditor.boxTitle')" @load="onLoad" />
</template>

<style scoped>
.support-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #f4f5fa;
}
</style>
