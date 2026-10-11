<template>
  <div class="jt" dir="ltr">
    <template v-if="container">
      <div class="jt__head">
      <button type="button" class="jt__row jt__tog" :aria-expanded="isOpen" @click="open = !open">
        <i class="pi" :class="isOpen ? 'pi-chevron-down' : 'pi-chevron-right'" />
        <span v-if="label != null" class="jt__key"><template v-for="(seg, i) in marks(String(label))" :key="i"><mark v-if="seg.m">{{ seg.t }}</mark><template v-else>{{ seg.t }}</template></template></span><span v-if="label != null" class="jt__p">:</span>
        <span class="jt__p">{{ isOpen ? bracket[0] : `${bracket[0]} ${summary} ${bracket[1]}` }}</span>
      </button>
      <button v-if="editable" type="button" class="jt__copy" :aria-label="t('common.edit')" :title="t('common.edit')" @click="emit('editNode', path, value)"><i class="pi pi-pencil" /></button>
      <button type="button" class="jt__copy" :aria-label="t('common.copy')" :title="t('common.copy')" @click="copy"><i class="pi pi-copy" /></button>
      </div>
      <div v-if="isOpen" class="jt__kids">
        <JsonTree v-for="[k, v] in shownEntries" :key="k" :label="k" :value="v" :depth="depth + 1" :open-depth="openDepth" :query="childQuery" :editable="editable" :path="[...path, k]" @set="(p, v) => emit('set', p, v)" @edit-node="(p, v) => emit('editNode', p, v)" />
      </div>
      <div v-if="isOpen" class="jt__row jt__close"><span class="jt__p">{{ bracket[1] }}</span></div>
    </template>
    <div v-else class="jt__row">
      <span v-if="label != null" class="jt__key"><template v-for="(seg, i) in marks(String(label))" :key="i"><mark v-if="seg.m">{{ seg.t }}</mark><template v-else>{{ seg.t }}</template></template></span><span v-if="label != null" class="jt__p">:</span>
      <span v-if="editing" class="jt__edit"><input ref="input" v-model="draft" class="jt__input" spellcheck="false" @keydown.enter.prevent="commit" @keydown.esc.prevent="editing = false" @blur="commit" /></span>
      <span v-else class="jt__val" :class="[`jt__val--${kind}`, { 'jt__val--editable': editable }]" :title="editable ? t('common.edit') : undefined" @click="startEdit"><template v-for="(seg, i) in marks(shown)" :key="i"><mark v-if="seg.m">{{ seg.t }}</mark><template v-else>{{ seg.t }}</template></template></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'

defineOptions({ name: 'JsonTree' })
const { t } = useI18n()
const toast = useToast()
const props = withDefaults(defineProps<{ value: unknown; label?: string | number | null; depth?: number; openDepth?: number; query?: string; editable?: boolean; path?: (string | number)[] }>(), { label: null, depth: 0, openDepth: 2, query: '', editable: false, path: () => [] })
const emit = defineEmits<{ set: [path: (string | number)[], value: unknown]; editNode: [path: (string | number)[], value: unknown] }>()

// Editing a value in place: a boolean flips, text and numbers are typed (Enter keeps it, Esc leaves it).
const editing = ref(false)
const draft = ref('')
const input = ref<HTMLInputElement | null>(null)

function startEdit() {
  if (!props.editable || container.value) return
  if (typeof props.value === 'boolean') {
    emit('set', props.path, !props.value)
    return
  }
  draft.value = typeof props.value === 'string' ? props.value : JSON.stringify(props.value)
  editing.value = true
  void nextTick(() => input.value?.select())
}

function commit() {
  if (!editing.value) return
  editing.value = false
  let v: unknown = draft.value
  if (typeof props.value === 'number') {
    const n = Number(draft.value)
    if (draft.value.trim() === '' || !Number.isFinite(n)) return
    v = n
  } else if (props.value === null) {
    try {
      v = JSON.parse(draft.value)
    } catch {
      v = draft.value
    }
  }
  if (v !== props.value) emit('set', props.path, v)
}

async function copy() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(props.value, null, 2))
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    /* clipboard blocked */
  }
}

const container = computed(() => props.value !== null && typeof props.value === 'object')
const isArray = computed(() => Array.isArray(props.value))
const bracket = computed(() => (isArray.value ? ['[', ']'] : ['{', '}']))
const entries = computed(() => (container.value ? Object.entries(props.value as object) : []))
const summary = computed(() => (isArray.value ? `${entries.value.length} items` : `${entries.value.length} keys`))
const open = ref(props.depth < props.openDepth)

// Search: nothing is hidden. A node whose key matches, or that holds a match, is opened (the way to it too); the rest stays as it was.
const q = computed(() => props.query.trim().toLowerCase())
const shownEntries = computed(() => entries.value)
const childQuery = computed(() => props.query)
const isOpen = computed(() => (q.value && container.value && (labelHit.value || entries.value.some(([k, v]) => hasMatch(v, k, q.value))) ? true : open.value))
const labelHit = computed(() => props.label != null && String(props.label).toLowerCase().includes(q.value))

function hasMatch(v: unknown, key: string | number | null, needle: string): boolean {
  if (key != null && String(key).toLowerCase().includes(needle)) return true
  if (v !== null && typeof v === 'object') return Object.entries(v).some(([k, c]) => hasMatch(c, k, needle))
  return String(v).toLowerCase().includes(needle)
}

/** The text cut into plain and matching parts, to highlight the matches. */
function marks(text: string): { t: string; m: boolean }[] {
  const needle = q.value
  if (!needle) return [{ t: text, m: false }]
  const out: { t: string; m: boolean }[] = []
  const low = text.toLowerCase()
  let at = 0
  for (let i = low.indexOf(needle); i >= 0; i = low.indexOf(needle, at)) {
    if (i > at) out.push({ t: text.slice(at, i), m: false })
    out.push({ t: text.slice(i, i + needle.length), m: true })
    at = i + needle.length
  }
  if (at < text.length) out.push({ t: text.slice(at), m: false })
  return out
}

const kind = computed(() => (props.value === null ? 'null' : typeof props.value))
const shown = computed(() => (typeof props.value === 'string' ? JSON.stringify(props.value) : String(props.value)))
</script>

<style scoped>
.jt {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
  line-height: 1.55;
}
.jt__row {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
  min-width: 0;
}
.jt__head {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
}
.jt__copy {
  padding: 0 0.3rem;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--p-text-muted-color);
  font-size: 0.7rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}
.jt__head:hover .jt__copy,
.jt__copy:focus-visible {
  opacity: 1;
}
@media (hover: none) {
  .jt__copy {
    opacity: 0.8;
  }
}
.jt__copy:hover {
  color: var(--p-primary-color);
}
.jt__tog {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
  text-align: start;
}
.jt__tog:hover .jt__p {
  color: var(--p-primary-color);
}
.jt__tog > i {
  font-size: 0.65rem;
  width: 0.9rem;
  color: var(--p-text-muted-color);
}
.jt__kids {
  margin-inline-start: 0.55rem;
  padding-inline-start: 0.8rem;
  border-inline-start: 1px dashed var(--p-content-border-color);
}
.jt__close {
  padding-inline-start: 0.9rem;
}
.jt__kids > .jt > .jt__row:not(.jt__tog) {
  padding-inline-start: 0.9rem;
}
.jt mark {
  padding: 0 0.1rem;
  border-radius: 3px;
  color: inherit;
  background: color-mix(in srgb, var(--p-amber-400, #fbbf24) 55%, transparent);
}
.jt__key {
  color: var(--p-primary-color);
  font-weight: 600;
}
.jt__p {
  color: var(--p-text-muted-color);
}
.jt__val {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.jt__val--editable {
  cursor: text;
  border-radius: 3px;
}
.jt__val--editable:hover {
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.jt__input {
  min-width: 10rem;
  width: min(32rem, 70vw);
  padding: 0 0.3rem;
  border: 1px solid var(--p-primary-color);
  border-radius: 4px;
  background: var(--p-content-background);
  color: inherit;
  font: inherit;
}
.jt__val--string {
  color: var(--p-green-600, #16a34a);
}
.jt__val--number {
  color: var(--p-amber-600, #d97706);
}
.jt__val--boolean {
  color: var(--p-purple-500, #a855f7);
}
.jt__val--null {
  color: var(--p-text-muted-color);
  font-style: italic;
}
</style>
