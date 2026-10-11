<template>
  <!-- JSON subscription (xray, hiddify-core, sing-box): a collapsible tree -->
  <div v-if="json !== undefined" class="sv">
    <div class="sv__bar">
      <Tag value="JSON" severity="info" />
      <span class="sv__count">{{ jsonSummary }}</span>
      <IconField class="sv__search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="search" :placeholder="t('configTester.sub.search')" dir="auto" spellcheck="false" fluid />
      </IconField>
      <Button icon="pi pi-angle-double-down" :label="t('configTester.sub.expandAll')" size="small" text @click="setDepth(99)" />
      <Button icon="pi pi-angle-double-up" :label="t('configTester.sub.collapseAll')" size="small" text @click="setDepth(1)" />
    </div>
    <div class="sv__tree"><JsonTree :key="treeKey" :value="json" :open-depth="depth" :query="search" />
      <p v-if="search.trim() && !jsonHits" class="sv__empty">{{ t('configTester.sub.noMatch') }}</p></div>
  </div>

  <!-- Share links: one line each; click one to edit it -->
  <div v-else class="sv">
    <div class="sv__bar">
      <Tag :value="t('configTester.sub.links')" severity="info" />
      <span class="sv__count">{{ search.trim() ? t('configTester.sub.countOf', { n: filtered.length, total: lines.length }) : t('configTester.sub.count', { n: lines.length }) }}</span>
      <IconField class="sv__search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="search" :placeholder="t('configTester.sub.search')" dir="auto" spellcheck="false" fluid />
      </IconField>
      <small class="sv__hint"><i class="pi pi-pencil" /> {{ t('configTester.sub.clickToEdit') }}</small>
    </div>
    <p v-if="!filtered.length" class="sv__empty">{{ search.trim() ? t('configTester.sub.noMatch') : t('configTester.sub.none') }}</p>
    <ul class="sv__list">
      <li v-for="{ l, i } in filtered" :key="i" class="sv__item" :class="{ 'is-open': openIndex === i }">
        <div class="sv__head">
          <button type="button" class="sv__line" :aria-expanded="openIndex === i" @click="toggle(i)">
            <i class="pi" :class="openIndex === i ? 'pi-chevron-down' : 'pi-chevron-right'" />
            <span class="sv__proto" dir="ltr">{{ protocolOf(l.text) }}</span>
            <span class="sv__text" dir="ltr">{{ l.text }}</span>
            <Tag v-if="search.trim() && !plainMatch(l)" :value="t('configTester.sub.inDecoded')" severity="warn" class="sv__decoded" />
          </button>
          <Button icon="pi pi-copy" text rounded size="small" class="sv__copy" :aria-label="t('configTester.sub.copyLink')" v-tooltip.top="t('configTester.sub.copyLink')" @click="copy(l.text)" />
        </div>
        <div v-if="openIndex === i" class="sv__edit">
          <SublinkEditor v-model:links="editing" id-prefix="ct-sub-" @change="onEdit(i)" />
          <div class="sv__edit-actions">
            <Button icon="pi pi-copy" :label="t('configTester.sub.copyLink')" size="small" severity="secondary" outlined @click="copy(l.text)" />
            <Button v-if="l.text !== l.original" icon="pi pi-undo" :label="t('configTester.sub.reset')" size="small" severity="secondary" text @click="reset(i)" />
          </div>
          <Message v-if="editError" severity="error" :closable="false">{{ editError }}</Message>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import JsonTree from '@/features/config-tester/components/JsonTree.vue'
import SublinkEditor from '@/features/utils/components/SublinkEditor.vue'
import { parseSublinks, tryStringifySublinks, unwrapSubscriptionText, type PrettyLink } from '@/shared/utils/sublink-pretty'

/**
 * What the panel answered: JSON as a tree, share links one per line (also when the whole body is base64);
 * a line opens the same editor as Utils (parse, edit, copy).
 */
const props = defineProps<{ raw: string }>()
const { t } = useI18n()
const toast = useToast()

const json = computed<unknown>(() => {
  const text = props.raw.trim()
  if (!text.startsWith('{') && !text.startsWith('[')) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return undefined
  }
})
const jsonSummary = computed(() => {
  const v = json.value
  if (Array.isArray(v)) return t('configTester.sub.items', { n: v.length })
  return v && typeof v === 'object' ? t('configTester.sub.keys', { n: Object.keys(v).length }) : ''
})
const search = ref('')
const needle = computed(() => search.value.trim().toLowerCase())

const jsonHits = computed(() => !needle.value || (json.value !== undefined && deepHas(json.value, needle.value)))
function deepHas(v: unknown, n: string): boolean {
  if (v !== null && typeof v === 'object') return Object.entries(v).some(([k, c]) => k.toLowerCase().includes(n) || deepHas(c, n))
  return String(v).toLowerCase().includes(n)
}

/** Base64 pieces of a link (vmess body, shadowsocks user info, ...) decoded, with the link itself percent-decoded, for searching. */
function decodedText(link: string): string {
  const parts: string[] = []
  try {
    parts.push(decodeURIComponent(link))
  } catch {
    /* not percent-encoded text */
  }
  for (const token of link.match(/[A-Za-z0-9+/_-]{12,}={0,2}/g) ?? []) {
    try {
      const b64 = token.replace(/^\/+/, '').replace(/-/g, '+').replace(/_/g, '/')
      const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
      const text = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
      // keep it only when it reads as text, not as random bytes
      if (/^[\x09\x0a\x0d\x20-\x7e\u00a0-\uffff]+$/.test(text)) parts.push(text)
    } catch {
      /* not base64 */
    }
  }
  return parts.join('\n').toLowerCase()
}
const decodedCache = new Map<string, string>()
function decodedOf(text: string): string {
  let d = decodedCache.get(text)
  if (d === undefined) decodedCache.set(text, (d = decodedText(text)))
  return d
}
function plainMatch(l: { text: string }): boolean {
  return l.text.toLowerCase().includes(needle.value)
}

const depth = ref(2)
// Jump to the first match once the tree has opened up to it.
watch(search, () => {
  if (!needle.value) return
  void nextTick(() => document.querySelector('.sv__tree mark')?.scrollIntoView({ block: 'center', behavior: 'smooth' }))
})
const treeKey = ref(0)
function setDepth(d: number) {
  depth.value = d
  treeKey.value++
}

interface Line {
  text: string
  original: string
}
const lines = ref<Line[]>([])
const openIndex = ref<number | null>(null)
/** The lines that match the search in the link or in what its base64 parts say. */
const filtered = computed(() => lines.value.map((l, i) => ({ l, i })).filter(({ l }) => !needle.value || plainMatch(l) || decodedOf(l.text).includes(needle.value)))
watch(
  () => props.raw,
  (raw) => {
    const { text } = unwrapSubscriptionText(raw)
    lines.value = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('#') && !l.startsWith('//'))
      .map((l) => ({ text: l, original: l }))
    openIndex.value = null
  },
  { immediate: true },
)

const editing = ref<PrettyLink[]>([])
const editError = ref('')
let syncing = false

function toggle(i: number) {
  if (openIndex.value === i) {
    openIndex.value = null
    return
  }
  openIndex.value = i
  load(i)
}
function load(i: number) {
  syncing = true
  editing.value = parseSublinks(lines.value[i].text)
  editError.value = ''
  queueMicrotask(() => (syncing = false))
}
function onEdit(i: number) {
  if (syncing) return
  const { text, error } = tryStringifySublinks(editing.value)
  editError.value = error ?? ''
  if (!error) lines.value[i].text = text
}
function reset(i: number) {
  lines.value[i].text = lines.value[i].original
  load(i)
}
function protocolOf(line: string): string {
  const m = line.match(/^([a-z][a-z0-9+.-]*):\/\//i)
  return m ? m[1].toLowerCase() : '?'
}
async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    /* clipboard blocked */
  }
}
</script>

<style scoped>
.sv__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.7rem;
}
.sv__search {
  flex: 1 1 14rem;
  min-width: 0;
  max-width: 24rem;
  margin-inline-start: auto;
}
.sv__decoded {
  flex-shrink: 0;
  font-size: 0.62rem;
}
.sv__count,
.sv__hint {
  color: var(--p-text-muted-color);
  font-size: 0.82rem;
}
.sv__tree {
  max-height: 60vh;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.sv__empty {
  margin: 0;
  color: var(--p-text-muted-color);
}
.sv__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.sv__item {
  flex-shrink: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  background: var(--p-content-background);
  overflow: hidden;
}
.sv__item.is-open {
  border-color: var(--p-primary-color);
}
.sv__head {
  display: flex;
  align-items: center;
}
.sv__copy {
  flex-shrink: 0;
  margin-inline-end: 0.3rem;
}
.sv__line {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex: 1;
  min-width: 0;
  padding: 0.55rem 0.7rem;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.sv__line:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.sv__line > i {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}
.sv__proto {
  flex-shrink: 0;
  padding: 0.05rem 0.5rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.sv__text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
}
.sv__edit {
  padding: 0.7rem;
  border-top: 1px solid var(--p-content-border-color);
}
.sv__edit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.7rem;
}
</style>
