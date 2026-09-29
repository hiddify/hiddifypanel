<template>
  <div class="nodes-page">
    <div class="nodes-head">
      <PageHeader :title="t('nodes.title')" :subtitle="t('nodes.subtitle')" />
      <Button v-if="nodes.length" icon="pi pi-plus" :label="t('nodes.addNode')" class="nodes-head__add" @click="addVisible = true" />
    </div>

    <!-- Summary -->
    <section v-if="nodes.length" class="nodes-summary">
      <div v-for="item in summary" :key="item.status" class="nodes-summary__item" :class="`nodes-summary__item--${item.status}`">
        <span class="nodes-dot" :class="`nodes-dot--${item.status}`" />
        <span class="nodes-summary__count">{{ item.count }}</span>
        <span class="nodes-summary__label">{{ t(`nodes.status.${item.status}`) }}</span>
      </div>
      <Button
        class="nodes-summary__refresh"
        icon="pi pi-refresh"
        text
        rounded
        severity="secondary"
        :loading="refreshing"
        :aria-label="t('nodes.refresh')"
        v-tooltip.left="t('nodes.refresh')"
        @click="refresh"
      />
    </section>

    <!-- Loading -->
    <div v-if="loading" class="nodes-grid">
      <Skeleton v-for="i in 3" :key="i" height="13rem" border-radius="16px" />
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <!-- Empty state -->
    <section v-else-if="!nodes.length" class="nodes-empty">
      <div class="nodes-empty__art" aria-hidden="true">
        <span class="nodes-empty__hub"><i class="pi pi-server" /></span>
        <span class="nodes-empty__sat nodes-empty__sat--a"><i class="pi pi-server" /></span>
        <span class="nodes-empty__sat nodes-empty__sat--b"><i class="pi pi-server" /></span>
        <span class="nodes-empty__sat nodes-empty__sat--c"><i class="pi pi-server" /></span>
      </div>
      <h3 class="nodes-empty__title">{{ t('nodes.empty.title') }}</h3>
      <p class="nodes-empty__text">{{ t('nodes.empty.text') }}</p>
      <ul class="nodes-empty__points">
        <li><i class="pi pi-users" />{{ t('nodes.empty.point1') }}</li>
        <li><i class="pi pi-chart-bar" />{{ t('nodes.empty.point2') }}</li>
        <li><i class="pi pi-link" />{{ t('nodes.empty.point3') }}</li>
      </ul>
      <Button icon="pi pi-plus" :label="t('nodes.empty.cta')" size="large" @click="addVisible = true" />
    </section>

    <!-- Node cards -->
    <TransitionGroup v-else name="nodes-card" tag="div" class="nodes-grid">
      <article
        v-for="(node, index) in nodes"
        :key="node.id"
        class="node-card"
        :class="[`node-card--${node.status}`, { 'node-card--new': node.id === justAdded }]"
        :style="{ '--node-delay': `${Math.min(index, 10) * 50}ms` }"
      >
        <header class="node-card__head">
          <span class="node-card__icon"><i class="pi pi-server" /></span>
          <div class="min-w-0 flex-1">
            <form v-if="editing === node.id" class="node-card__rename" @submit.prevent="saveName(node)">
              <InputText
                :ref="(el) => focusRename(el)"
                v-model="editName"
                size="small"
                class="flex-1 min-w-0"
                maxlength="100"
                :disabled="renaming"
                :aria-label="t('nodes.rename')"
                @keydown.esc.prevent="cancelRename"
              />
              <Button type="submit" icon="pi pi-check" size="small" text rounded :loading="renaming" :disabled="!editName.trim()" :aria-label="t('common.save')" />
              <Button type="button" icon="pi pi-times" size="small" text rounded severity="secondary" :disabled="renaming" :aria-label="t('common.cancel')" @click="cancelRename" />
            </form>
            <button v-else type="button" class="node-card__name" :title="t('nodes.rename')" @click="startRename(node)">
              <span class="node-card__name-text">{{ node.name }}</span>
              <i class="pi pi-pencil node-card__name-edit" />
            </button>
            <div class="node-card__host" dir="ltr">{{ node.host || '—' }}</div>
          </div>
          <span class="node-status" :class="`node-status--${node.status}`">
            <span class="nodes-dot" :class="`nodes-dot--${node.status}`" />
            {{ t(`nodes.status.${node.status}`) }}
          </span>
        </header>

        <dl class="node-card__facts">
          <div>
            <dt>{{ t('nodes.lastSeen') }}</dt>
            <dd :title="node.last_seen ? new Date(node.last_seen).toLocaleString() : ''">{{ relativeTime(node.last_seen) }}</dd>
          </div>
          <div>
            <dt>{{ t('nodes.connection') }}</dt>
            <dd>
              <span v-if="pings[node.id]?.state === 'checking'" class="node-check node-check--checking"><i class="pi pi-spin pi-spinner" />{{ t('nodes.checking') }}</span>
              <span v-else-if="pings[node.id]?.state === 'ok'" class="node-check node-check--ok">
                <i class="pi pi-check-circle" />{{ t('nodes.reachable') }}
                <span v-if="pings[node.id]?.version" class="node-version" :class="{ 'node-version--diff': pings[node.id]?.version !== panelVersion }" :title="versionTitle(pings[node.id]?.version)">
                  v{{ pings[node.id]?.version }}
                </span>
              </span>
              <span v-else-if="pings[node.id]?.state === 'fail'" class="node-check node-check--fail" :title="pings[node.id]?.error">
                <i class="pi pi-times-circle" />{{ t('nodes.unreachable') }}
              </span>
              <span v-else class="text-muted-color">—</span>
            </dd>
          </div>
        </dl>

        <div v-if="node.domains.length" class="node-card__domains">
          <TransitionGroup name="node-domain">
            <span v-for="domain in shownDomains(node)" :key="domain" class="node-domain" dir="ltr" :title="domain">{{ domain }}</span>
          </TransitionGroup>
          <button
            v-if="node.domains.length > DOMAIN_PREVIEW"
            type="button"
            class="node-domain node-domain--more"
            :aria-expanded="expandedDomains.has(node.id)"
            @click="toggleDomains(node.id)"
          >
            <template v-if="expandedDomains.has(node.id)"><i class="pi pi-angle-up" />{{ t('nodes.showLess') }}</template>
            <template v-else>+{{ node.domains.length - DOMAIN_PREVIEW }} <i class="pi pi-angle-down" /></template>
          </button>
        </div>

        <button type="button" class="node-card__more" :aria-expanded="expandedInfo.has(node.id)" @click="toggleInfo(node.id)">
          <i class="pi pi-info-circle" />
          <span class="flex-1">{{ t('nodes.moreInfo') }}</span>
          <i class="pi pi-angle-down node-card__more-caret" :class="{ 'node-card__more-caret--open': expandedInfo.has(node.id) }" />
        </button>
        <div class="node-card__info-wrap" :class="{ 'node-card__info-wrap--open': expandedInfo.has(node.id) }">
          <dl class="node-card__info">
            <div class="node-card__info-row node-card__info-row--wide">
              <dt><i class="pi pi-chart-line" />{{ t('nodes.info.lastUsage') }}</dt>
              <dd v-if="node.details.last_usage_report" :title="new Date(node.details.last_usage_report.time).toLocaleString()">
                {{ relativeTime(node.details.last_usage_report.time) }}
                <span class="text-muted-color">·
                  {{ t('nodes.info.usageReport', { users: formatCount(node.details.last_usage_report.users), traffic: formatBytes(node.details.last_usage_report.bytes) }, node.details.last_usage_report.users) }}
                </span>
              </dd>
              <dd v-else class="text-muted-color">{{ t('nodes.info.noUsageYet') }}</dd>
            </div>
            <div class="node-card__info-row">
              <dt><i class="pi pi-arrow-right-arrow-left" />{{ t('nodes.info.todayTraffic') }}</dt>
              <dd>{{ formatBytes(node.details.today_usage) }}</dd>
            </div>
            <div class="node-card__info-row">
              <dt><i class="pi pi-users" />{{ t('nodes.info.todayOnline') }}</dt>
              <dd>{{ formatCount(node.details.today_online) }}</dd>
            </div>
            <div class="node-card__info-row">
              <dt><i class="pi pi-arrow-down-left" />{{ t('nodes.info.fromNode') }}</dt>
              <dd :title="node.details.last_from_node ? new Date(node.details.last_from_node).toLocaleString() : ''">{{ relativeTime(node.details.last_from_node) }}</dd>
            </div>
            <div class="node-card__info-row">
              <dt><i class="pi pi-arrow-up-right" />{{ t('nodes.info.toNode') }}</dt>
              <dd :title="node.details.last_to_node ? new Date(node.details.last_to_node).toLocaleString() : ''">{{ relativeTime(node.details.last_to_node) }}</dd>
            </div>
          </dl>
        </div>

        <footer class="node-card__actions">
          <Button
            v-if="node.admin_url"
            as="a"
            :href="node.admin_url"
            target="_blank"
            rel="noopener"
            icon="pi pi-external-link"
            :label="t('nodes.openAdmin')"
            class="node-card__open"
          />
          <Button
            icon="pi pi-sync"
            severity="secondary"
            outlined
            :loading="syncing === node.id"
            :aria-label="t('nodes.syncNow')"
            v-tooltip.top="t('nodes.syncNow')"
            @click="syncNode(node)"
          />
          <Button
            icon="pi pi-wifi"
            severity="secondary"
            outlined
            :aria-label="t('nodes.checkConnection')"
            v-tooltip.top="t('nodes.checkConnection')"
            @click="pingNode(node)"
          />
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            :aria-label="t('nodes.remove')"
            v-tooltip.top="t('nodes.remove')"
            @click="confirmRemove(node)"
          />
        </footer>
      </article>
    </TransitionGroup>

    <AddNodeDialog v-model:visible="addVisible" @added="onAdded" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { formatBytes, formatCount } from '@/shared/utils/format-metrics'
import AddNodeDialog from '@/features/nodes/components/AddNodeDialog.vue'
import { nodesApi, type NodeStatus, type PanelNode } from '@/features/nodes/api'

interface PingState {
  state: 'checking' | 'ok' | 'fail'
  version?: string
  error?: string
}

const REFRESH_MS = 60_000
const DOMAIN_PREVIEW = 3

const { t, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const nodes = ref<PanelNode[]>([])
const panelVersion = ref('')
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref<string | null>(null)
const addVisible = ref(false)
const syncing = ref<number | null>(null)
const justAdded = ref<number | null>(null)
const pings = reactive<Record<number, PingState>>({})
const expandedDomains = ref<Set<number>>(new Set())
const expandedInfo = ref<Set<number>>(new Set())
const editing = ref<number | null>(null)
const editName = ref('')
const renaming = ref(false)
const now = ref(Date.now())
let timer: number | undefined

const summary = computed(() =>
  (['online', 'late', 'offline', 'never'] as NodeStatus[])
    .map((status) => ({ status, count: nodes.value.filter((node) => node.status === status).length }))
    .filter((item) => item.count > 0 || item.status === 'online'),
)

function relativeTime(iso: string | null): string {
  if (!iso) return t('nodes.neverSeen')
  const seconds = Math.round((new Date(iso).getTime() - now.value) / 1000)
  if (Math.abs(seconds) < 60) return t('nodes.justNow')
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit)
  }
  return rtf.format(seconds, 'second')
}

function shownDomains(node: PanelNode): string[] {
  return expandedDomains.value.has(node.id) ? node.domains : node.domains.slice(0, DOMAIN_PREVIEW)
}

function toggleInfo(id: number) {
  const next = new Set(expandedInfo.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedInfo.value = next
}

function toggleDomains(id: number) {
  const next = new Set(expandedDomains.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedDomains.value = next
}

function startRename(node: PanelNode) {
  editing.value = node.id
  editName.value = node.name
}

function cancelRename() {
  editing.value = null
}

let focusedFor: number | null = null
function focusRename(el: unknown) {
  // Focus once per edit, not on every re-render.
  if (!el || focusedFor === editing.value) return
  focusedFor = editing.value
  const input = (el as { $el?: HTMLInputElement }).$el
  input?.focus()
  input?.select()
}

async function saveName(node: PanelNode) {
  const name = editName.value.trim()
  if (!name || renaming.value) return
  if (name === node.name) {
    cancelRename()
    return
  }
  renaming.value = true
  try {
    const res = await nodesApi.rename(node.id, name)
    const index = nodes.value.findIndex((row) => row.id === node.id)
    if (index >= 0) nodes.value[index] = res.node
    editing.value = null
    focusedFor = null
    if (res.synced_to_node) toast.add({ severity: 'success', summary: t('nodes.renamed', { name }), life: 3000 })
    else toast.add({ severity: 'warn', summary: t('nodes.renamedHereOnly', { name }), detail: t('nodes.renamedHereOnlyDetail'), life: 7000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    renaming.value = false
  }
}

function versionTitle(version?: string): string {
  if (!version) return ''
  return version === panelVersion.value ? t('nodes.sameVersion') : t('nodes.differentVersion', { node: version, panel: panelVersion.value })
}

async function pingNode(node: PanelNode) {
  pings[node.id] = { state: 'checking' }
  try {
    const res = await nodesApi.ping(node.id)
    pings[node.id] = res.online ? { state: 'ok', version: res.version } : { state: 'fail', error: res.error }
  } catch (err) {
    pings[node.id] = { state: 'fail', error: apiErrorMessage(err) }
  }
}

async function load(silent = false) {
  if (!silent) loading.value = true
  loadError.value = null
  try {
    const res = await nodesApi.list()
    nodes.value = res.nodes
    panelVersion.value = res.panel_version
    now.value = Date.now()
  } catch (err) {
    if (!silent) loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function refresh() {
  refreshing.value = true
  await load(true)
  await Promise.all(nodes.value.map((node) => pingNode(node)))
  refreshing.value = false
}

async function syncNode(node: PanelNode) {
  syncing.value = node.id
  try {
    await nodesApi.sync(node.id)
    toast.add({ severity: 'success', summary: t('nodes.synced', { name: node.name }), life: 3000 })
    await load(true)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('nodes.syncFailed', { name: node.name }), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    syncing.value = null
  }
}

function confirmRemove(node: PanelNode) {
  dangerConfirm({
    header: t('nodes.removeTitle', { name: node.name }),
    message: t('nodes.removeMessage'),
    acceptLabel: t('nodes.remove'),
    accept: async () => {
      try {
        const unlinked = await nodesApi.remove(node.id)
        nodes.value = nodes.value.filter((row) => row.id !== node.id)
        if (unlinked) toast.add({ severity: 'success', summary: t('nodes.removed', { name: node.name }), life: 3000 })
        else toast.add({ severity: 'warn', summary: t('nodes.removed', { name: node.name }), detail: t('nodes.removedNotUnlinked'), life: 9000 })
      } catch (err) {
        toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

async function onAdded(node: PanelNode | null) {
  toast.add({ severity: 'success', summary: t('nodes.add.success'), life: 3000 })
  await load(true)
  if (node) {
    justAdded.value = node.id
    window.setTimeout(() => (justAdded.value = null), 2500)
    void pingNode(node)
  }
}

onMounted(async () => {
  await load()
  void Promise.all(nodes.value.map((node) => pingNode(node)))
  timer = window.setInterval(() => {
    now.value = Date.now()
    if (!document.hidden) void load(true)
  }, REFRESH_MS)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<style scoped>
.nodes-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0 1rem;
}
.nodes-head__add {
  margin-bottom: 1.25rem;
}

/* Summary */
.nodes-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1.5rem;
  padding: 0.75rem 1.1rem;
  margin-bottom: 1.25rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.nodes-summary__item {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.nodes-summary__count {
  font-weight: 700;
  font-size: 1.1rem;
}
.nodes-summary__label {
  color: var(--p-text-muted-color);
}
.nodes-summary__refresh {
  margin-inline-start: auto;
}

/* Status dots */
.nodes-dot {
  position: relative;
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--p-surface-400, #94a3b8);
}
.nodes-dot--online {
  background: var(--p-green-500, #22c55e);
}
.nodes-dot--online::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: nodes-ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
}
.nodes-dot--late {
  background: var(--p-amber-500, #f59e0b);
}
.nodes-dot--offline {
  background: var(--p-red-500, #ef4444);
}

/* Grid + cards */
.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr));
  gap: 1rem;
}
.node-card {
  --node-accent: var(--p-surface-400, #94a3b8);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.1rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
  animation: nodes-in 0.4s ease both;
  animation-delay: var(--node-delay, 0ms);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}
.node-card::before {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 0;
  height: 3px;
  background: var(--node-accent);
}
.node-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px -14px color-mix(in srgb, var(--node-accent) 70%, transparent);
}
.node-card--online {
  --node-accent: var(--p-green-500, #22c55e);
}
.node-card--late {
  --node-accent: var(--p-amber-500, #f59e0b);
}
.node-card--offline {
  --node-accent: var(--p-red-500, #ef4444);
}
.node-card--new {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.node-card__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.node-card__icon {
  width: 2.6rem;
  height: 2.6rem;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.15rem;
  color: var(--node-accent);
  background: color-mix(in srgb, var(--node-accent) 14%, transparent);
}
.node-card__name {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  max-width: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-size: 1.05rem;
  font-weight: 600;
  text-align: start;
  cursor: text;
}
.node-card__name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-card__name-edit {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  opacity: 0;
  transition: opacity 0.15s ease;
}
.node-card__name:hover .node-card__name-edit,
.node-card__name:focus-visible .node-card__name-edit {
  opacity: 1;
}
.node-card__rename {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}
.node-card__host {
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.node-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--node-accent);
  background: color-mix(in srgb, var(--node-accent) 12%, transparent);
}
.node-status--never {
  color: var(--p-text-muted-color);
}
.node-card__facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin: 0;
}
.node-card__facts dt {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.15rem;
}
.node-card__facts dd {
  margin: 0;
  font-weight: 500;
  font-size: 0.9rem;
}
.node-check {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}
.node-check--ok {
  color: var(--p-green-600, #16a34a);
}
.node-check--fail {
  color: var(--p-red-500, #ef4444);
}
.node-check--checking {
  color: var(--p-text-muted-color);
}
.node-version {
  padding: 0 0.4rem;
  border-radius: 6px;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.node-version--diff {
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 16%, transparent);
}
.node-card__domains {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.node-domain {
  max-width: 100%;
  padding: 0.12rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.node-domain--more {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-primary-color);
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.node-domain--more:hover {
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.node-domain--more i {
  font-size: 0.7rem;
}
.node-domain-enter-active,
.node-domain-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.node-domain-enter-from,
.node-domain-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
.node-card__more {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 0;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.85rem;
  text-align: start;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}
.node-card__more:hover {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.node-card__more-caret {
  transition: transform 0.25s ease;
}
.node-card__more-caret--open {
  transform: rotate(180deg);
}
/* Height animation without measuring: grid rows 0fr -> 1fr. */
.node-card__info-wrap {
  display: grid;
  grid-template-rows: 0fr;
  margin-top: -0.9rem;
  transition:
    grid-template-rows 0.3s ease,
    margin-top 0.3s ease;
}
.node-card__info-wrap--open {
  grid-template-rows: 1fr;
  margin-top: -0.4rem;
}
.node-card__info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem 0.75rem;
  min-height: 0;
  margin: 0;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.node-card__info-wrap--open .node-card__info {
  opacity: 1;
  padding-top: 0.25rem;
}
.node-card__info-row--wide {
  grid-column: 1 / -1;
}
.node-card__info dt {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.15rem;
}
.node-card__info dt i {
  font-size: 0.72rem;
}
.node-card__info dd {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 500;
}
.node-card__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
}
.node-card__open {
  flex: 1;
}

/* Empty state */
.nodes-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.75rem;
  padding: 2.5rem 1.25rem;
  border-radius: 20px;
  background: var(--p-content-background);
  border: 1px dashed var(--p-content-border-color);
}
.nodes-empty__art {
  position: relative;
  width: 9rem;
  height: 7rem;
  margin-bottom: 0.5rem;
}
.nodes-empty__hub,
.nodes-empty__sat {
  position: absolute;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, var(--p-content-background));
}
.nodes-empty__hub {
  width: 3.5rem;
  height: 3.5rem;
  left: calc(50% - 1.75rem);
  top: calc(50% - 1.75rem);
  font-size: 1.5rem;
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}
.nodes-empty__sat {
  width: 2.1rem;
  height: 2.1rem;
  font-size: 0.9rem;
  animation: nodes-float 3.2s ease-in-out infinite;
}
.nodes-empty__sat--a {
  left: 0;
  top: 0.25rem;
}
.nodes-empty__sat--b {
  right: 0;
  top: 0.75rem;
  animation-delay: 0.6s;
}
.nodes-empty__sat--c {
  left: calc(50% - 1.05rem);
  bottom: -0.5rem;
  animation-delay: 1.2s;
}
.nodes-empty__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}
.nodes-empty__text {
  margin: 0;
  max-width: 32rem;
  color: var(--p-text-muted-color);
}
.nodes-empty__points {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem 1.25rem;
  margin: 0.25rem 0 0.75rem;
  padding: 0;
  list-style: none;
  font-size: 0.9rem;
}
.nodes-empty__points li {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.nodes-empty__points i {
  color: var(--p-primary-color);
}

/* Animations */
@keyframes nodes-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes nodes-ping {
  75%,
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
@keyframes nodes-float {
  50% {
    transform: translateY(-6px);
  }
}
.nodes-card-move {
  transition: transform 0.3s ease;
}
.nodes-card-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.nodes-card-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

@media (max-width: 640px) {
  .nodes-head__add {
    width: 100%;
  }
  .nodes-summary,
  .node-card {
    border-radius: 14px;
  }
}
/* Touch screens have no hover: keep the edit hint visible. */
@media (hover: none) {
  .node-card__name-edit {
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .node-card__info-wrap,
  .node-card__info,
  .node-card__more-caret {
    transition: none;
  }
  .node-card,
  .nodes-dot--online::after,
  .nodes-empty__sat {
    animation: none;
  }
  .node-card:hover {
    transform: none;
  }
}
</style>
