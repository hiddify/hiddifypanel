<script setup lang="ts">
/**
 * One recent sync, in words: what was exchanged, in which direction, and (opened) the users, admins, outbounds or
 * domains themselves by name. The JSON it carried stays behind "Technical data", with secret values hidden.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { rawJson, type NodeAdminItem, type NodeSyncEntry, type NodeUserItem } from '@/features/node-home/api'
import { formatBytes } from '@/shared/utils/format-metrics'

const props = defineProps<{
  entry: NodeSyncEntry
  open: boolean
  /** The node's users and admins: names for the ids a sync carries */
  users?: NodeUserItem[]
  admins?: NodeAdminItem[]
  ago: string
  at: string
}>()
const emit = defineEmits<{ toggle: [] }>()
const { t, te } = useI18n()

const KIND_ICON: Record<string, string> = {
  users: 'pi pi-users',
  admins: 'pi pi-sitemap',
  domains: 'pi pi-globe',
  outbounds: 'pi pi-directions',
  usage: 'pi pi-chart-bar',
}
const KIND_COLOR: Record<string, string> = { users: '#6366f1', admins: '#8b5cf6', domains: '#0ea5e9', outbounds: '#14b8a6', usage: '#f59e0b' }

const e = computed(() => props.entry)
const n = computed(() => e.value.count ?? e.value.items?.length ?? 0)
/** in: from the main panel · out: to it · check: compared with it */
const direction = computed<'in' | 'out' | 'check'>(() =>
  e.value.source === 'inventory' ? 'check' : e.value.kind === 'domains' || e.value.kind === 'usage' ? 'out' : 'in',
)
const what = computed(() => (te(`nodeSync.noun.${e.value.kind}`) ? t(`nodeSync.noun.${e.value.kind}`, { n: n.value }, n.value) : t(`nodeSync.kind.${e.value.kind}`)))
const num = (key: string) => Number(e.value.detail[key] ?? 0)

const sentence = computed(() => {
  const x = e.value
  if (!x.ok) return t('nodeSync.say.failed', { what: t(`nodeSync.kind.${x.kind}`) })
  if (x.kind === 'usage') return n.value ? t('nodeSync.say.usageSent', { what: t('nodeSync.noun.users', { n: n.value }, n.value) }) : t('nodeSync.say.usageNone')
  if (x.source === 'inventory') return t('nodeSync.say.checked', { what: what.value })
  if (direction.value === 'out') return t('nodeSync.say.sent', { what: what.value })
  if (x.source === 'register') return t('nodeSync.say.receivedRegister', { what: what.value })
  if (x.source === 'http_sync') return t('nodeSync.say.receivedHttp', { what: what.value })
  return t('nodeSync.say.received', { what: what.value })
})
/** The small print after the sentence: what else happened */
const extras = computed(() => {
  const x = e.value
  const out: string[] = []
  if (!x.ok && x.detail.error) out.push(String(x.detail.error).replace(/(https?:\/\/[^/\s]+)\/\S*/g, '$1/…'))
  if (x.source === 'inventory') {
    const missing = num('missing')
    const removed = num('removed')
    if (!missing && !removed) out.push(t('nodeSync.x.matched'))
    if (missing) out.push(t('nodeSync.x.missing', { n: missing }, missing))
    if (removed) out.push(t('nodeSync.x.removed', { n: removed }, removed))
  }
  if (x.detail.more === true) out.push(t('nodeSync.x.more'))
  if (num('missing_sent')) out.push(t('nodeSync.x.missingSent', { n: num('missing_sent') }, num('missing_sent')))
  if (x.kind === 'usage' && num('users_back')) out.push(t('nodeSync.x.usersBack', { n: num('users_back') }, num('users_back')))
  return out
})

// Opened: the rows themselves, read from the JSON the sync carried (else the short labels the node kept)
interface Row {
  icon: string
  name: string
  tags: { text: string; tone?: 'ok' | 'off' | 'muted' }[]
}
const rows = ref<Row[] | null>(null)
const raw = ref('')
const rawOpen = ref(false)
const hasData = computed(() => !!(e.value.items?.length || e.value.raw_z))
const names = computed(() => {
  const map = new Map<string, string>()
  for (const u of props.users ?? []) map.set(u.uuid, u.name)
  for (const a of props.admins ?? []) map.set(a.uuid, a.name)
  return map
})
const nameOf = (uuid: string) => names.value.get(uuid) || `${t('nodeSync.unknownName')} · ${uuid.slice(0, 8)}`
const gb = (v: unknown) => `${Math.round(Number(v ?? 0) * 100) / 100} GB`
const modeText = (mode: string) => (te(`admins.mode.${mode}`) ? t(`admins.mode.${mode}`) : mode)

function rowOf(item: unknown): Row {
  const kind = e.value.kind
  if (typeof item === 'string') return { icon: KIND_ICON[kind] ?? 'pi pi-circle', name: nameOf(item), tags: [] }
  const o = item as Record<string, unknown>
  if (kind === 'usage') {
    const up = Number(o.upload ?? 0)
    const down = Number(o.download ?? 0)
    return { icon: 'pi pi-user', name: nameOf(String(o.uuid ?? '')), tags: [{ text: `↑ ${formatBytes(up, 1)}`, tone: 'muted' }, { text: `↓ ${formatBytes(down, 1)}`, tone: 'muted' }] }
  }
  if (kind === 'users') {
    const tags: Row['tags'] = [{ text: o.enable === false ? t('nodeSync.disabled') : t('nodeSync.on'), tone: o.enable === false ? 'off' : 'ok' }]
    if (o.usage_limit_GB !== undefined) tags.push({ text: `${gb(o.current_usage_GB)} / ${gb(o.usage_limit_GB)}`, tone: 'muted' })
    return { icon: 'pi pi-user', name: String(o.name || nameOf(String(o.uuid ?? ''))), tags }
  }
  if (kind === 'admins') return { icon: 'pi pi-id-card', name: String(o.name || nameOf(String(o.uuid ?? ''))), tags: o.mode ? [{ text: modeText(String(o.mode)), tone: 'muted' }] : [] }
  if (kind === 'outbounds') {
    const tags: Row['tags'] = []
    if (o.mode) tags.push({ text: String(o.mode), tone: 'muted' })
    if (o.enabled !== undefined) tags.push({ text: o.enabled ? t('nodeSync.on') : t('nodeSync.disabled'), tone: o.enabled ? 'ok' : 'off' })
    return { icon: 'pi pi-directions', name: String(o.name ?? o.slug ?? ''), tags }
  }
  // domains
  return { icon: 'pi pi-globe', name: String(o.domain ?? o.name ?? ''), tags: o.mode ? [{ text: String(o.mode), tone: 'muted' }] : [] }
}

/** Keys whose values are secrets (a user's keys, passwords, tokens): never shown */
const SECRET = /private|password|passwd|secret|token|api_?key|^wg_|_pk$|^pk$|telegram_id/i
function hideSecrets(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(hideSecrets)
  if (value && typeof value === 'object')
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, SECRET.test(k) && v !== null && v !== '' ? '••••••' : hideSecrets(v)]))
  return value
}

async function load() {
  rows.value = null
  raw.value = ''
  let parsed: unknown[] | null = null
  try {
    const text = await rawJson(e.value)
    if (text && !e.value.raw_truncated) parsed = JSON.parse(text)
    raw.value = parsed ? JSON.stringify(hideSecrets(parsed), null, 2) : text ? t('nodeSync.rawPartial') : ''
  } catch {
    raw.value = t('nodeSync.rawUnreadable')
  }
  if (Array.isArray(parsed)) rows.value = parsed.slice(0, 200).map(rowOf)
  else rows.value = (e.value.items ?? []).map((label) => ({ icon: KIND_ICON[e.value.kind] ?? 'pi pi-circle', name: label, tags: [] }))
}
function toggle() {
  if (!hasData.value) return
  if (!props.open) void load()
  emit('toggle')
}
const more = computed(() => Math.max(0, n.value - (rows.value?.length ?? 0)))
</script>

<template>
  <li class="sle" :class="{ 'sle--bad': !entry.ok, 'sle--open': open }" :style="{ '--sle-c': KIND_COLOR[entry.kind] ?? 'var(--p-primary-color)' }">
    <button type="button" class="sle__head" :disabled="!hasData" :aria-expanded="hasData ? open : undefined" @click="toggle">
      <span class="sle__icon" aria-hidden="true"><i :class="entry.ok ? KIND_ICON[entry.kind] ?? 'pi pi-circle' : 'pi pi-times'" /></span>
      <span class="sle__text">
        <span class="sle__say">{{ sentence }}</span>
        <span class="sle__meta">
          <span class="sle__dir" :class="`sle__dir--${direction}`">
            <i :class="direction === 'in' ? 'pi pi-arrow-down' : direction === 'out' ? 'pi pi-arrow-up' : 'pi pi-check-square'" aria-hidden="true" />{{ t(`nodeSync.dir.${direction}`) }}
          </span>
          <span class="sle__source" :title="t(`nodeSync.sourceHint.${entry.source}`)">{{ t(`nodeSync.source.${entry.source}`) }}</span>
          <span v-for="(x, i) in extras" :key="i" class="sle__extra">{{ x }}</span>
        </span>
      </span>
      <span class="sle__time" :title="at">{{ ago }}</span>
      <i v-if="hasData" class="pi sle__caret" :class="open ? 'pi-chevron-up' : 'pi-chevron-down'" aria-hidden="true" />
    </button>

    <div v-if="open" class="sle__body">
      <p v-if="rows === null" class="sle__muted"><i class="pi pi-spin pi-spinner" /></p>
      <template v-else>
        <ul v-if="rows.length" class="sle__rows">
          <li v-for="(r, i) in rows" :key="i" class="sle__row">
            <i :class="r.icon" class="sle__row-icon" aria-hidden="true" />
            <span class="sle__row-name">{{ r.name }}</span>
            <span v-for="(tag, j) in r.tags" :key="j" class="sle__tag" :class="tag.tone && `sle__tag--${tag.tone}`">{{ tag.text }}</span>
          </li>
        </ul>
        <p v-if="more" class="sle__muted">{{ t('nodeSync.itemsMore', { n: more }) }}</p>
        <div v-if="raw" class="sle__tech">
          <button type="button" class="sle__tech-toggle" :aria-expanded="rawOpen" @click="rawOpen = !rawOpen">
            <i class="pi pi-code" aria-hidden="true" />{{ t('nodeSync.tech') }}
            <span class="sle__muted">· {{ t('nodeSync.techHidden') }}</span>
            <i class="pi" :class="rawOpen ? 'pi-angle-up' : 'pi-angle-down'" aria-hidden="true" />
          </button>
          <pre v-if="rawOpen" class="sle__raw" dir="ltr">{{ raw }}</pre>
        </div>
      </template>
    </div>
  </li>
</template>

<style scoped>
.sle {
  --sle-c: var(--p-primary-color);
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  background: var(--p-content-background);
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.sle--open {
  border-color: color-mix(in srgb, var(--sle-c) 40%, var(--p-content-border-color));
  box-shadow: 0 4px 16px -8px color-mix(in srgb, var(--sle-c) 45%, transparent);
}
.sle--bad {
  --sle-c: var(--p-red-500, #ef4444);
  background: color-mix(in srgb, var(--sle-c) 5%, var(--p-content-background));
}
.sle__head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
  border-radius: 12px;
}
.sle__head:disabled {
  cursor: default;
}
.sle__head:not(:disabled):hover {
  background: color-mix(in srgb, var(--sle-c) 5%, transparent);
}
.sle__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 10px;
  color: var(--sle-c);
  background: color-mix(in srgb, var(--sle-c) 14%, transparent);
}
.sle__text {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
}
.sle__say {
  font-size: 0.88rem;
  font-weight: 600;
}
.sle__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.45rem;
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
}
.sle__dir {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-weight: 600;
}
.sle__dir i {
  font-size: 0.65rem;
}
.sle__dir--in {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 12%, transparent);
}
.sle__dir--out {
  color: var(--p-blue-600, #2563eb);
  background: color-mix(in srgb, var(--p-blue-500, #3b82f6) 12%, transparent);
}
.sle__dir--check {
  color: var(--p-purple-600, #9333ea);
  background: color-mix(in srgb, var(--p-purple-500, #a855f7) 12%, transparent);
}
.sle__source {
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  background: var(--p-content-hover-background);
  cursor: help;
}
.sle__extra + .sle__extra::before,
.sle__source + .sle__extra::before {
  content: '·';
  margin-inline-end: 0.45rem;
}
.sle--bad .sle__extra {
  color: var(--sle-c);
  overflow-wrap: anywhere;
}
.sle__time {
  flex: none;
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.sle__caret {
  flex: none;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.sle__body {
  padding: 0 0.75rem 0.75rem;
}
.sle__rows {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  max-height: 16rem;
  margin: 0;
  padding: 0.5rem;
  overflow: auto;
  list-style: none;
  border-radius: 10px;
  background: var(--p-content-hover-background);
}
.sle__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  padding: 0.35rem 0.5rem;
  border-radius: 8px;
  background: var(--p-content-background);
  font-size: 0.82rem;
}
.sle__row-icon {
  font-size: 0.8rem;
  color: var(--sle-c);
}
.sle__row-name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.sle__tag {
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  white-space: nowrap;
}
.sle__tag--ok {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 12%, transparent);
}
.sle__tag--off {
  color: var(--p-red-600, #dc2626);
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 12%, transparent);
}
.sle__tag--muted {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
}
.sle__muted {
  margin: 0.4rem 0 0;
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
}
.sle__tech {
  margin-top: 0.5rem;
}
.sle__tech-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0;
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.sle__tech-toggle:hover {
  color: var(--p-primary-color);
}
.sle__tech-toggle .sle__muted {
  margin: 0;
}
.sle__raw {
  max-height: 18rem;
  margin: 0.35rem 0 0;
  padding: 0.6rem;
  overflow: auto;
  border-radius: 8px;
  background: var(--p-content-hover-background);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.74rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
