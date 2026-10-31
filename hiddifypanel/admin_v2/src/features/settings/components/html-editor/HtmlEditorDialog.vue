<script setup lang="ts">
/**
 * The panel's own HTML editor for the support box (no outside site): Preview edits the text as it looks on the user
 * page, Source shows its HTML. Lite has the everyday tools, Full all of them. OK and Apply put the text in the setting
 * (saved with the settings), Cancel drops what was not applied.
 */
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import EditorIcon, { type EditorIconName } from './EditorIcon.vue'
import HtmlSourceEditor from './HtmlSourceEditor.vue'
import SupportFrame from './SupportFrame.vue'
import { BLOCK_STYLES, SNIPPETS, caretBlock, escapeAttr } from './support-frame'

const props = defineProps<{ modelValue: string; title: string; maxlength?: number }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()

type Mode = 'preview' | 'source'
type Level = 'lite' | 'full'
const LEVEL_KEY = 'admin_v2_html_editor_level'

const draft = ref('')
const mode = ref<Mode>('preview')
const level = ref<Level>(readLevel())
const wrap = ref(true)
const frame = ref<InstanceType<typeof SupportFrame> | null>(null)
const source = ref<InstanceType<typeof HtmlSourceEditor> | null>(null)

function readLevel(): Level {
  try {
    return localStorage.getItem(LEVEL_KEY) === 'full' ? 'full' : 'lite'
  } catch {
    return 'lite'
  }
}
watch(level, (value) => {
  try {
    localStorage.setItem(LEVEL_KEY, value)
  } catch {
    /* private window: the choice is not kept */
  }
})

watch(visible, (open) => {
  if (!open) return
  draft.value = props.modelValue ?? ''
  mode.value = 'preview'
})

const length = computed(() => draft.value.length)
const tooLong = computed(() => Boolean(props.maxlength && length.value > props.maxlength))
const unapplied = computed(() => draft.value !== (props.modelValue ?? ''))

function apply() {
  if (tooLong.value) return
  emit('update:modelValue', draft.value)
}
function ok() {
  if (tooLong.value) return
  apply()
  visible.value = false
}
function cancel() {
  visible.value = false
}

// ---- Preview (visual) editing: commands on the frame's document ----

const active = reactive(new Set<string>())
const block = ref('p')

function frameParts() {
  const doc = frame.value?.document()
  const content = frame.value?.content()
  return doc && content ? { doc, content } : null
}

/** The caret must be in the text before a command: at the end when it is not. */
function focusContent() {
  const parts = frameParts()
  if (!parts) return null
  const { doc, content } = parts
  content.focus()
  const sel = doc.getSelection()
  if (sel && (!sel.rangeCount || !content.contains(sel.anchorNode))) {
    const range = doc.createRange()
    range.selectNodeContents(content)
    range.collapse(false)
    sel.removeAllRanges()
    sel.addRange(range)
  }
  return parts
}

/** Tags the user page resets: those the tools made (no style yet, or another tag's) get theirs. */
function styleBlocks(content: HTMLElement) {
  const ours = new Set(Object.values(BLOCK_STYLES))
  for (const [tag, style] of Object.entries(BLOCK_STYLES)) {
    if (tag === 'p') continue
    for (const el of content.querySelectorAll<HTMLElement>(tag)) {
      const current = el.getAttribute('style')
      if (!current || (ours.has(current) && current !== style)) el.setAttribute('style', style)
    }
  }
}

function done(content: HTMLElement) {
  styleBlocks(content)
  frame.value?.sync()
  refreshState()
}

function exec(command: string, value?: string) {
  const parts = focusContent()
  if (!parts) return
  parts.doc.execCommand(command, false, value)
  done(parts.content)
}

function insertHtml(html: string) {
  exec('insertHTML', html)
}

function selectedText(): string {
  return frameParts()?.doc.getSelection()?.toString() ?? ''
}

function setFontSize(px: string) {
  const parts = focusContent()
  if (!parts || !px) return
  parts.doc.execCommand('fontSize', false, '7')
  for (const el of parts.content.querySelectorAll<HTMLElement>('span[style*="xxx-large"], font[size="7"]')) {
    if (el.tagName === 'FONT') {
      const span = parts.doc.createElement('span')
      span.innerHTML = el.innerHTML
      el.replaceWith(span)
      span.style.fontSize = px
    } else el.style.fontSize = px
  }
  done(parts.content)
}

function setDirection(dir: 'ltr' | 'rtl') {
  const parts = focusContent()
  if (!parts) return
  let el = caretBlock(parts.doc, parts.content)
  if (!el) {
    parts.doc.execCommand('formatBlock', false, 'p')
    el = caretBlock(parts.doc, parts.content)
  }
  if (el) {
    el.setAttribute('dir', dir)
    el.style.textAlign = dir === 'rtl' ? 'right' : 'left'
  }
  done(parts.content)
}

const STATES = ['bold', 'italic', 'underline', 'strikeThrough', 'subscript', 'superscript', 'justifyLeft', 'justifyCenter', 'justifyRight', 'justifyFull', 'insertUnorderedList', 'insertOrderedList']
function refreshState() {
  const doc = frameParts()?.doc
  if (!doc || mode.value !== 'preview') return
  active.clear()
  for (const name of STATES) {
    try {
      if (doc.queryCommandState(name)) active.add(name)
    } catch {
      /* not supported here */
    }
  }
  const value = String(doc.queryCommandValue('formatBlock') || 'p').toLowerCase()
  block.value = BLOCKS.value.some((b) => b.value === value) ? value : 'p'
}

// ---- toolbar ----

interface Tool {
  id: string
  icon: EditorIconName
  label: string
  run: (event: MouseEvent) => void
  state?: string
  full?: boolean
  color?: string
}

const textColor = ref('#e03131')
const markColor = ref('#ffec99')
const colorPop = ref<InstanceType<typeof Popover> | null>(null)
const colorTarget = ref<'fore' | 'mark'>('fore')
const linkPop = ref<InstanceType<typeof Popover> | null>(null)
const imagePop = ref<InstanceType<typeof Popover> | null>(null)
const tablePop = ref<InstanceType<typeof Popover> | null>(null)
const buttonPop = ref<InstanceType<typeof Popover> | null>(null)
const emojiPop = ref<InstanceType<typeof Popover> | null>(null)
const symbolPop = ref<InstanceType<typeof Popover> | null>(null)

const link = reactive({ url: 'https://', text: '', newTab: true })
const image = reactive({ url: 'https://', alt: '', width: '' })
const button = reactive({ text: '', url: 'https://t.me/' })
const tableHover = reactive({ rows: 0, cols: 0 })

function openColor(event: MouseEvent, target: 'fore' | 'mark') {
  colorTarget.value = target
  colorPop.value?.toggle(event)
}

const tools = computed<Tool[][]>(() => {
  const all: Tool[][] = [
    [
      { id: 'bold', icon: 'bold', label: t('settings.htmlEditor.tools.bold'), run: () => exec('bold'), state: 'bold' },
      { id: 'italic', icon: 'italic', label: t('settings.htmlEditor.tools.italic'), run: () => exec('italic'), state: 'italic' },
      { id: 'underline', icon: 'underline', label: t('settings.htmlEditor.tools.underline'), run: () => exec('underline'), state: 'underline' },
      { id: 'strike', icon: 'strike', label: t('settings.htmlEditor.tools.strike'), run: () => exec('strikeThrough'), state: 'strikeThrough', full: true },
      { id: 'sub', icon: 'subscript', label: t('settings.htmlEditor.tools.subscript'), run: () => exec('subscript'), state: 'subscript', full: true },
      { id: 'sup', icon: 'superscript', label: t('settings.htmlEditor.tools.superscript'), run: () => exec('superscript'), state: 'superscript', full: true },
      { id: 'clear', icon: 'clear', label: t('settings.htmlEditor.tools.clear'), run: () => exec('removeFormat'), full: true },
    ],
    [
      { id: 'fore', icon: 'textColor', label: t('settings.htmlEditor.tools.textColor'), run: (e) => openColor(e, 'fore'), color: textColor.value },
      { id: 'mark', icon: 'highlight', label: t('settings.htmlEditor.tools.highlight'), run: (e) => openColor(e, 'mark'), color: markColor.value, full: true },
    ],
    [
      { id: 'left', icon: 'alignLeft', label: t('settings.htmlEditor.tools.alignLeft'), run: () => exec('justifyLeft'), state: 'justifyLeft' },
      { id: 'center', icon: 'alignCenter', label: t('settings.htmlEditor.tools.alignCenter'), run: () => exec('justifyCenter'), state: 'justifyCenter' },
      { id: 'right', icon: 'alignRight', label: t('settings.htmlEditor.tools.alignRight'), run: () => exec('justifyRight'), state: 'justifyRight' },
      { id: 'justify', icon: 'alignJustify', label: t('settings.htmlEditor.tools.alignJustify'), run: () => exec('justifyFull'), state: 'justifyFull', full: true },
    ],
    [
      { id: 'ul', icon: 'listBullet', label: t('settings.htmlEditor.tools.bulletList'), run: () => exec('insertUnorderedList'), state: 'insertUnorderedList' },
      { id: 'ol', icon: 'listNumber', label: t('settings.htmlEditor.tools.numberList'), run: () => exec('insertOrderedList'), state: 'insertOrderedList' },
      { id: 'outdent', icon: 'outdent', label: t('settings.htmlEditor.tools.outdent'), run: () => exec('outdent'), full: true },
      { id: 'indent', icon: 'indent', label: t('settings.htmlEditor.tools.indent'), run: () => exec('indent'), full: true },
      { id: 'quote', icon: 'quote', label: t('settings.htmlEditor.tools.quote'), run: () => onBlock('blockquote'), full: true },
    ],
    [
      { id: 'link', icon: 'link', label: t('settings.htmlEditor.tools.link'), run: (e) => openLink(e) },
      { id: 'unlink', icon: 'unlink', label: t('settings.htmlEditor.tools.unlink'), run: () => exec('unlink'), full: true },
      { id: 'image', icon: 'image', label: t('settings.htmlEditor.tools.image'), run: (e) => imagePop.value?.toggle(e), full: true },
      { id: 'table', icon: 'table', label: t('settings.htmlEditor.tools.table'), run: (e) => tablePop.value?.toggle(e), full: true },
      { id: 'hr', icon: 'hr', label: t('settings.htmlEditor.tools.hr'), run: () => insertHtml(SNIPPETS.hr), full: true },
    ],
    [
      { id: 'box', icon: 'box', label: t('settings.htmlEditor.tools.box'), run: () => insertHtml(SNIPPETS.box(escapeAttr(selectedText()) || t('settings.htmlEditor.sampleText'))), full: true },
      { id: 'button', icon: 'button', label: t('settings.htmlEditor.tools.button'), run: (e) => openButton(e) },
      { id: 'emoji', icon: 'emoji', label: t('settings.htmlEditor.tools.emoji'), run: (e) => emojiPop.value?.toggle(e) },
      { id: 'symbol', icon: 'symbol', label: t('settings.htmlEditor.tools.symbol'), run: (e) => symbolPop.value?.toggle(e), full: true },
    ],
    [
      { id: 'ltr', icon: 'ltr', label: t('settings.htmlEditor.tools.ltr'), run: () => setDirection('ltr'), full: true },
      { id: 'rtl', icon: 'rtl', label: t('settings.htmlEditor.tools.rtl'), run: () => setDirection('rtl'), full: true },
    ],
  ]
  return all.map((group) => group.filter((tool) => level.value === 'full' || !tool.full)).filter((group) => group.length)
})

const BLOCKS = computed(() => {
  const lite = [
    { value: 'p', label: t('settings.htmlEditor.blocks.p') },
    { value: 'h2', label: t('settings.htmlEditor.blocks.h', { n: 2 }) },
    { value: 'h3', label: t('settings.htmlEditor.blocks.h', { n: 3 }) },
  ]
  if (level.value === 'lite') return lite
  return [
    lite[0],
    ...[1, 2, 3, 4, 5, 6].map((n) => ({ value: `h${n}`, label: t('settings.htmlEditor.blocks.h', { n }) })),
    { value: 'pre', label: t('settings.htmlEditor.blocks.pre') },
    { value: 'blockquote', label: t('settings.htmlEditor.blocks.quote') },
  ]
})
const FONTS = computed(() => [
  { value: '', label: t('settings.htmlEditor.fonts.default') },
  { value: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif', label: 'Sans-serif' },
  { value: 'Georgia, Times New Roman, serif', label: 'Serif' },
  { value: 'ui-monospace, Consolas, monospace', label: 'Monospace' },
  { value: 'Vazirmatn, Tahoma, sans-serif', label: 'Vazirmatn' },
])
const SIZES = ['12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px']
const fontName = ref('')
const fontSize = ref('')

/** A chosen format brings its own look: the new block drops the style it copied from the old one (a box, a heading). */
/** After a list choice: the caret back in the text (the Select takes the focus while it closes). */
function refocus() {
  frameParts()?.content.focus()
}

function onBlock(value: string) {
  const parts = focusContent()
  if (!parts) return
  parts.doc.execCommand('formatBlock', false, value)
  const el = caretBlock(parts.doc, parts.content)
  if (el?.tagName.toLowerCase() === value) {
    el.removeAttribute('align')
    if (BLOCK_STYLES[value] && value !== 'p') el.setAttribute('style', BLOCK_STYLES[value])
    else el.removeAttribute('style')
  }
  done(parts.content)
}
function onFont(value: string) {
  if (value) exec('fontName', value)
  else exec('removeFormat')
  fontName.value = ''
}
function onSize(value: string) {
  setFontSize(value)
  fontSize.value = ''
}

const SWATCHES = ['#000000', '#495057', '#868e96', '#ffffff', '#e03131', '#f76707', '#f59f00', '#2f9e44', '#0c8599', '#1971c2', '#455fe9', '#7048e8', '#ae3ec9', '#d6336c', '#ffe3e3', '#fff3bf', '#d3f9d8', '#d0ebff', '#e5dbff', '#ffec99']
function pickColor(color: string) {
  if (colorTarget.value === 'fore') {
    textColor.value = color
    exec('foreColor', color)
  } else {
    markColor.value = color
    exec('hiliteColor', color)
  }
  colorPop.value?.hide()
}

function openLink(event: MouseEvent) {
  const anchor = frameParts()?.doc.getSelection()?.anchorNode?.parentElement?.closest('a')
  link.url = anchor?.getAttribute('href') || 'https://'
  link.text = selectedText()
  link.newTab = anchor ? anchor.getAttribute('target') === '_blank' : true
  linkPop.value?.toggle(event)
}
function insertLink() {
  const url = link.url.trim()
  if (!url || url === 'https://') return
  const target = link.newTab ? ' target="_blank" rel="noopener"' : ''
  const text = link.text.trim() || url
  if (selectedText()) {
    exec('createLink', url)
    const parts = frameParts()
    for (const a of parts?.content.querySelectorAll<HTMLAnchorElement>('a') ?? []) {
      if (a.getAttribute('href') !== url) continue
      if (link.newTab) a.setAttribute('target', '_blank')
      else a.removeAttribute('target')
    }
    if (parts) done(parts.content)
  } else insertHtml(`<a href="${escapeAttr(url)}"${target} style="${BLOCK_STYLES.a}">${escapeAttr(text)}</a>`)
  linkPop.value?.hide()
}
function insertImage() {
  const url = image.url.trim()
  if (!url || url === 'https://') return
  insertHtml(SNIPPETS.image(url, image.alt.trim(), image.width.trim()))
  imagePop.value?.hide()
}
function insertTable(rows: number, cols: number) {
  insertHtml(SNIPPETS.table(rows, cols))
  tablePop.value?.hide()
}
function openButton(event: MouseEvent) {
  button.text = selectedText() || t('settings.htmlEditor.sampleButton')
  buttonPop.value?.toggle(event)
}
function insertButton() {
  const url = button.url.trim()
  if (!url) return
  insertHtml(SNIPPETS.button(escapeAttr(button.text.trim() || url), url))
  buttonPop.value?.hide()
}

const EMOJIS = ['😀', '😊', '😍', '🤩', '😎', '🤝', '👋', '👍', '🙏', '👏', '💪', '🔥', '⭐', '✨', '🎉', '🎁', '💎', '❤️', '💙', '💚', '✅', '❌', '⚠️', '📢', '📣', '💬', '📞', '📧', '📱', '💻', '🌐', '🔒', '🔑', '🚀', '⚡', '🕒', '📅', '💰', '🆓', '🆕', '👉', '👇', '➡️', '⬅️', '🎯', '📌', '🛡️', '🌍']
const SYMBOLS = ['©', '®', '™', '€', '£', '¥', '$', '°', '±', '×', '÷', '≈', '≠', '≤', '≥', '∞', '→', '←', '↑', '↓', '↔', '⇒', '•', '·', '…', '«', '»', '“', '”', '‘', '’', '—', '–', '§', '¶', '†', '✓', '✔', '✗', '★', '☆', '♥', '☎', '✉', '♪', '☀', '☂', '⌘']
function insertText(text: string, pop: InstanceType<typeof Popover> | null) {
  exec('insertText', text)
  pop?.hide()
}

// ---- Source ----

function switchMode(next: Mode) {
  if (next === mode.value) return
  if (mode.value === 'preview') {
    const content = frameParts()?.content
    if (content) draft.value = content.innerHTML
  }
  mode.value = next
  if (next === 'preview') nextTick(refreshState)
}

function undo() {
  if (mode.value === 'source') source.value?.undo()
  else exec('undo')
}
function redo() {
  if (mode.value === 'source') source.value?.redo()
  else exec('redo')
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    maximizable
    :draggable="false"
    class="hed-dialog"
    :style="{ width: 'min(64rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '720px': '100vw' }"
    :pt="{ content: { class: 'hed-dialog__content' }, footer: { class: 'hed-dialog__footer' } }"
  >
    <template #header>
      <div class="hed-head">
        <span class="hed-head__icon" aria-hidden="true"><EditorIcon name="code" /></span>
        <div class="min-w-0">
          <div class="hed-head__title">{{ t('settings.htmlEditor.title') }}</div>
          <div class="hed-head__sub">{{ title }}</div>
        </div>
      </div>
    </template>

    <div class="hed">
      <div class="hed-bar">
        <div class="hed-seg" role="tablist" :aria-label="t('settings.htmlEditor.view')">
          <button type="button" role="tab" autofocus class="hed-seg__btn" :class="{ 'hed-seg__btn--on': mode === 'preview' }" :aria-selected="mode === 'preview'" @click="switchMode('preview')">
            <EditorIcon name="eye" />{{ t('settings.htmlEditor.preview') }}
          </button>
          <button type="button" role="tab" class="hed-seg__btn" :class="{ 'hed-seg__btn--on': mode === 'source' }" :aria-selected="mode === 'source'" @click="switchMode('source')">
            <EditorIcon name="code" />{{ t('settings.htmlEditor.source') }}
          </button>
        </div>
        <div class="hed-seg hed-seg--level" role="radiogroup" :aria-label="t('settings.htmlEditor.toolset')">
          <button type="button" role="radio" class="hed-seg__btn" :class="{ 'hed-seg__btn--on': level === 'lite' }" :aria-checked="level === 'lite'" @click="level = 'lite'">
            <EditorIcon name="sparkle" />{{ t('settings.htmlEditor.lite') }}
          </button>
          <button type="button" role="radio" class="hed-seg__btn" :class="{ 'hed-seg__btn--on': level === 'full' }" :aria-checked="level === 'full'" @click="level = 'full'">
            <EditorIcon name="layers" />{{ t('settings.htmlEditor.full') }}
          </button>
        </div>
      </div>

      <div class="hed-toolbar" role="toolbar" :aria-label="t('settings.htmlEditor.toolbar')" @mousedown="($event.target as HTMLElement).closest('button') && $event.preventDefault()">
        <div class="hed-group">
          <button v-tooltip.bottom="t('settings.htmlEditor.tools.undo')" type="button" class="hed-tool" :aria-label="t('settings.htmlEditor.tools.undo')" @click="undo"><EditorIcon name="undo" /></button>
          <button v-tooltip.bottom="t('settings.htmlEditor.tools.redo')" type="button" class="hed-tool" :aria-label="t('settings.htmlEditor.tools.redo')" @click="redo"><EditorIcon name="redo" /></button>
        </div>

        <template v-if="mode === 'preview'">
          <div class="hed-group hed-group--selects">
            <Select :model-value="block" :options="BLOCKS" option-label="label" option-value="value" class="hed-select hed-select--block" size="small" :aria-label="t('settings.htmlEditor.blockFormat')" @update:model-value="onBlock" @hide="refocus" />
            <template v-if="level === 'full'">
              <Select v-model="fontName" :options="FONTS" option-label="label" option-value="value" class="hed-select" size="small" :placeholder="t('settings.htmlEditor.font')" :aria-label="t('settings.htmlEditor.font')" @update:model-value="onFont" @hide="refocus" />
              <Select v-model="fontSize" :options="SIZES" class="hed-select hed-select--size" size="small" :placeholder="t('settings.htmlEditor.size')" :aria-label="t('settings.htmlEditor.size')" @update:model-value="onSize" @hide="refocus" />
            </template>
          </div>
          <div v-for="(group, i) in tools" :key="i" class="hed-group">
            <button
              v-for="tool in group"
              :key="tool.id"
              v-tooltip.bottom="tool.label"
              type="button"
              class="hed-tool"
              :class="{ 'hed-tool--on': tool.state && active.has(tool.state) }"
              :aria-label="tool.label"
              :aria-pressed="tool.state ? active.has(tool.state) : undefined"
              @click="tool.run($event)"
            >
              <EditorIcon :name="tool.icon" :color="tool.color" />
            </button>
          </div>
        </template>
        <template v-else>
          <div class="hed-group">
            <button type="button" class="hed-tool hed-tool--text" @click="source?.format()"><EditorIcon name="format" />{{ t('settings.htmlEditor.formatCode') }}</button>
            <button type="button" class="hed-tool hed-tool--text" :class="{ 'hed-tool--on': wrap }" :aria-pressed="wrap" @click="wrap = !wrap"><EditorIcon name="wrap" />{{ t('settings.htmlEditor.wrap') }}</button>
          </div>
          <span class="hed-toolbar__hint">{{ t('settings.htmlEditor.sourceHint') }}</span>
        </template>
      </div>

      <div class="hed-canvas" :class="{ 'hed-canvas--source': mode === 'source' }">
        <SupportFrame v-if="mode === 'preview'" ref="frame" v-model:html="draft" editable @selectionchange="refreshState" />
        <HtmlSourceEditor v-else ref="source" v-model="draft" :wrap="wrap" />
      </div>
    </div>

    <template #footer>
      <div class="hed-foot">
        <div class="hed-foot__info">
          <span class="hed-count" :class="{ 'hed-count--over': tooLong }" dir="ltr">{{ length }}<template v-if="maxlength"> / {{ maxlength }}</template></span>
          <span v-if="tooLong" class="hed-foot__warn"><i class="pi pi-exclamation-circle" />{{ t('settings.htmlEditor.tooLong') }}</span>
          <span v-else class="hed-foot__hint">{{ unapplied ? t('settings.htmlEditor.unapplied') : t('settings.htmlEditor.saveHint') }}</span>
        </div>
        <div class="hed-foot__actions">
          <Button :label="t('settings.htmlEditor.cancel')" severity="secondary" text @click="cancel" />
          <Button :label="t('settings.htmlEditor.apply')" icon="pi pi-check-circle" severity="secondary" outlined :disabled="!unapplied || tooLong" @click="apply" />
          <Button :label="t('settings.htmlEditor.ok')" icon="pi pi-check" :disabled="tooLong" @click="ok" />
        </div>
      </div>
    </template>
  </Dialog>

  <Popover ref="colorPop">
    <div class="hed-pop">
      <div class="hed-pop__title">{{ colorTarget === 'fore' ? t('settings.htmlEditor.tools.textColor') : t('settings.htmlEditor.tools.highlight') }}</div>
      <div class="hed-swatches">
        <button v-for="c in SWATCHES" :key="c" type="button" class="hed-swatch" :style="{ background: c }" :aria-label="c" @mousedown.prevent @click="pickColor(c)" />
      </div>
      <label class="hed-custom-color">
        <input type="color" :value="colorTarget === 'fore' ? textColor : markColor" @change="pickColor(($event.target as HTMLInputElement).value)" />
        {{ t('settings.htmlEditor.customColor') }}
      </label>
    </div>
  </Popover>

  <Popover ref="linkPop">
    <form class="hed-pop hed-form" @submit.prevent="insertLink">
      <div class="hed-pop__title">{{ t('settings.htmlEditor.tools.link') }}</div>
      <label>{{ t('settings.htmlEditor.url') }}<InputText v-model="link.url" dir="ltr" size="small" autofocus /></label>
      <label>{{ t('settings.htmlEditor.linkText') }}<InputText v-model="link.text" size="small" :placeholder="t('settings.htmlEditor.linkTextHint')" /></label>
      <label class="hed-check"><input v-model="link.newTab" type="checkbox" />{{ t('settings.htmlEditor.newTab') }}</label>
      <Button type="submit" :label="t('settings.htmlEditor.insert')" size="small" />
    </form>
  </Popover>

  <Popover ref="imagePop">
    <form class="hed-pop hed-form" @submit.prevent="insertImage">
      <div class="hed-pop__title">{{ t('settings.htmlEditor.tools.image') }}</div>
      <label>{{ t('settings.htmlEditor.imageUrl') }}<InputText v-model="image.url" dir="ltr" size="small" autofocus /></label>
      <label>{{ t('settings.htmlEditor.alt') }}<InputText v-model="image.alt" size="small" /></label>
      <label>{{ t('settings.htmlEditor.width') }}<InputText v-model="image.width" dir="ltr" size="small" placeholder="120" /></label>
      <Button type="submit" :label="t('settings.htmlEditor.insert')" size="small" />
    </form>
  </Popover>

  <Popover ref="tablePop">
    <div class="hed-pop">
      <div class="hed-pop__title">{{ tableHover.rows ? `${tableHover.rows} × ${tableHover.cols}` : t('settings.htmlEditor.tools.table') }}</div>
      <div class="hed-grid" dir="ltr" @mouseleave="tableHover.rows = tableHover.cols = 0">
        <template v-for="r in 6" :key="r">
          <button
            v-for="c in 6"
            :key="`${r}-${c}`"
            type="button"
            class="hed-grid__cell"
            :class="{ 'hed-grid__cell--on': r <= tableHover.rows && c <= tableHover.cols }"
            :aria-label="`${r} × ${c}`"
            @mouseenter="(tableHover.rows = r), (tableHover.cols = c)"
            @mousedown.prevent
            @click="insertTable(r, c)"
          />
        </template>
      </div>
    </div>
  </Popover>

  <Popover ref="buttonPop">
    <form class="hed-pop hed-form" @submit.prevent="insertButton">
      <div class="hed-pop__title">{{ t('settings.htmlEditor.tools.button') }}</div>
      <label>{{ t('settings.htmlEditor.buttonText') }}<InputText v-model="button.text" size="small" autofocus /></label>
      <label>{{ t('settings.htmlEditor.url') }}<InputText v-model="button.url" dir="ltr" size="small" /></label>
      <Button type="submit" :label="t('settings.htmlEditor.insert')" size="small" />
    </form>
  </Popover>

  <Popover ref="emojiPop">
    <div class="hed-pop">
      <div class="hed-chars hed-chars--emoji">
        <button v-for="e in EMOJIS" :key="e" type="button" class="hed-char" @mousedown.prevent @click="insertText(e, emojiPop)">{{ e }}</button>
      </div>
    </div>
  </Popover>

  <Popover ref="symbolPop">
    <div class="hed-pop">
      <div class="hed-chars">
        <button v-for="s in SYMBOLS" :key="s" type="button" class="hed-char" @mousedown.prevent @click="insertText(s, symbolPop)">{{ s }}</button>
      </div>
    </div>
  </Popover>
</template>

<style scoped>
.hed-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.hed-head__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, var(--p-primary-400), var(--p-primary-600));
  box-shadow: 0 6px 16px -8px var(--p-primary-500);
}
.hed-head__title {
  font-size: 1.1rem;
  font-weight: 700;
}
.hed-head__sub {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hed {
  display: flex;
  flex-direction: column;
  height: min(70vh, 44rem);
  min-height: 24rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
  overflow: hidden;
  background: var(--p-content-background);
}
.hed-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-primary-color) 4%, var(--p-content-background));
}
.hed-seg {
  display: inline-flex;
  padding: 3px;
  gap: 2px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.hed-seg__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.85rem;
  border: 0;
  border-radius: 8px;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}
.hed-seg__btn :deep(.editor-icon) {
  width: 16px;
  height: 16px;
}
.hed-seg__btn:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 1px;
}
.hed-seg__btn:hover {
  color: var(--p-text-color);
}
.hed-seg__btn--on {
  color: var(--p-primary-color);
  background: var(--p-content-background);
  box-shadow: 0 1px 3px rgb(15 23 42 / 12%);
}
.hed-seg--level .hed-seg__btn--on {
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
}
.hed-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.35rem;
  padding: 0.45rem 0.6rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.hed-group {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding-inline-end: 0.35rem;
  border-inline-end: 1px solid var(--p-content-border-color);
}
.hed-group:last-child {
  border-inline-end: 0;
}
.hed-group--selects {
  gap: 0.35rem;
}
.hed-tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-width: 2rem;
  height: 2rem;
  padding: 0 0.4rem;
  border: 0;
  border-radius: 8px;
  font: inherit;
  font-size: 0.8rem;
  color: var(--p-text-color);
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s;
}
.hed-tool:hover {
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
.hed-tool:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 1px;
}
.hed-tool--on {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.hed-tool--text {
  padding: 0 0.6rem;
}
.hed-toolbar__hint {
  margin-inline-start: auto;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.hed-select {
  width: 8.5rem;
}
.hed-select--block {
  width: 9.5rem;
}
.hed-select--size {
  width: 6rem;
}
.hed-canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #f4f5fa;
}
.hed-canvas--source {
  background: var(--p-content-background);
}
.hed-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
}
.hed-foot__info {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.hed-count {
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.hed-count--over {
  color: var(--p-red-600, #dc2626);
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 14%, transparent);
}
.hed-foot__warn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--p-red-600, #dc2626);
}
.hed-foot__actions {
  display: flex;
  gap: 0.5rem;
  margin-inline-start: auto;
}
.hed-pop {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  min-width: 12rem;
}
.hed-pop__title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.hed-form {
  width: 16rem;
}
.hed-form label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
}
.hed-form .hed-check {
  flex-direction: row;
  align-items: center;
  gap: 0.4rem;
}
.hed-swatches {
  display: grid;
  grid-template-columns: repeat(7, 1.6rem);
  gap: 0.35rem;
}
.hed-swatch {
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 6px;
  border: 1px solid rgb(0 0 0 / 12%);
  cursor: pointer;
  transition: transform 0.12s;
}
.hed-swatch:hover {
  transform: scale(1.12);
}
.hed-custom-color {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  cursor: pointer;
}
.hed-custom-color input {
  width: 1.8rem;
  height: 1.8rem;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}
.hed-grid {
  display: grid;
  grid-template-columns: repeat(6, 1.35rem);
  gap: 3px;
}
.hed-grid__cell {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 4px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  cursor: pointer;
}
.hed-grid__cell--on {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 22%, transparent);
}
.hed-chars {
  display: grid;
  grid-template-columns: repeat(8, 2rem);
  gap: 2px;
}
.hed-char {
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 8px;
  font-size: 1rem;
  background: transparent;
  cursor: pointer;
}
.hed-chars--emoji .hed-char {
  font-size: 1.2rem;
}
.hed-char:hover {
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
@media (max-width: 720px) {
  .hed {
    height: calc(100dvh - 12rem);
    border-radius: 10px;
  }
  .hed-select,
  .hed-select--block {
    width: 7.5rem;
  }
  .hed-toolbar__hint {
    display: none;
  }
  .hed-foot__info {
    width: 100%;
  }
}
</style>

<style>
.hed-dialog .hed-dialog__content {
  padding-bottom: 0.75rem;
}
.p-dialog-maximized.hed-dialog .hed {
  height: 100%;
}
.p-dialog-maximized.hed-dialog .hed-dialog__content {
  display: flex;
  flex-direction: column;
}
</style>
