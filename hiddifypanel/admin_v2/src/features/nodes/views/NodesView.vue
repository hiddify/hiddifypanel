<template>
  <div ref="pageEl" class="nodes-page">
    <div class="nodes-head">
      <PageHeader v-if="!embedded" :title="t('nodes.title')" :subtitle="t('nodes.subtitle')" />
      <Button v-if="nodes.length" icon="pi pi-plus" :label="t('nodes.addNode')" class="nodes-head__add" @click="addVisible = true" />
    </div>

    <!-- Summary -->
    <section v-if="nodes.length" class="nodes-summary">
      <div v-for="item in summary" :key="item.status" class="nodes-summary__item" :class="`nodes-summary__item--${item.status}`">
        <span class="nodes-dot" :class="`nodes-dot--${item.status}`" />
        <span class="nodes-summary__count">{{ item.count }}</span>
        <span class="nodes-summary__label">{{ t(`nodes.status.${item.status}`) }}</span>
      </div>
      <div class="nodes-summary__totals">
        <div class="nodes-summary__item">
          <i class="pi pi-arrow-right-arrow-left nodes-summary__icon" />
          <span class="nodes-summary__count">{{ formatBytes(totals.traffic) }}</span>
          <span class="nodes-summary__label">{{ t('nodes.info.todayTraffic') }}</span>
        </div>
        <div class="nodes-summary__item">
          <i class="pi pi-users nodes-summary__icon" />
          <span class="nodes-summary__count">{{ formatCount(totals.online) }}</span>
          <span class="nodes-summary__label">{{ t('nodes.info.todayOnline') }}</span>
        </div>
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
        :class="[`node-card--${node.status}`, { 'node-card--new': node.id === justAdded, 'node-card--live': liveOpen.has(node.id) }]"
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
              <span v-if="flag(node.country)" class="node-card__flag" :title="countryName(node.country)" :aria-label="countryName(node.country)">{{ flag(node.country) }}</span>
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
              <!-- Not reachable: why and what to do on hover (mouse) or a click; the button next to it checks again -->
              <span v-else-if="pings[node.id]?.state === 'fail'" class="node-check node-check--fail">
                <button
                  type="button"
                  class="node-check__why"
                  aria-haspopup="dialog"
                  :aria-label="`${t('nodes.unreachable')}: ${t('nodes.contact.hint')}`"
                  @pointerenter="(e: PointerEvent) => e.pointerType === 'mouse' && showWhy(e, node.id)"
                  @pointerleave="(e: PointerEvent) => e.pointerType === 'mouse' && hideWhySoon()"
                  @click="(e: MouseEvent) => toggleWhy(e, node.id)"
                >
                  <i class="pi pi-times-circle" />{{ t('nodes.unreachable') }}<i class="pi pi-info-circle node-check__info" aria-hidden="true" />
                </button>
                <Button icon="pi pi-refresh" text rounded size="small" class="node-check__again" :aria-label="t('nodes.checkAgain')" v-tooltip.top="t('nodes.checkAgain')" @click="pingNode(node)" />
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

        <!-- A few nodes have the room: their details are always shown, not behind "More information". -->
        <button v-if="!few" type="button" class="node-card__more" :aria-expanded="expandedInfo.has(node.id)" @click="toggleInfo(node.id)">
          <i class="pi pi-info-circle" />
          <span class="flex-1">{{ t('nodes.moreInfo') }}</span>
          <i class="pi pi-angle-down node-card__more-caret" :class="{ 'node-card__more-caret--open': expandedInfo.has(node.id) }" />
        </button>
        <div class="node-card__info-wrap" :class="{ 'node-card__info-wrap--open': few || expandedInfo.has(node.id), 'node-card__info-wrap--inline': few }">
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
          <Button icon="pi pi-wave-pulse" :label="t('nodes.pingDialog.button')" severity="secondary" outlined class="node-card__ping" :aria-pressed="pinging.has(node.id)" :class="{ 'node-card__ping--on': pinging.has(node.id) }" @click="togglePing(node.id)" />
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
            icon="pi pi-chart-line"
            severity="secondary"
            outlined
            :aria-label="t('nodes.syncInfo')"
            v-tooltip.top="t('nodes.syncInfo')"
            @click="syncInfoNode = node"
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

        <!-- This node's live charts (network, CPU, RAM), polled only while open -->
        <button type="button" class="node-card__live-toggle" :aria-expanded="liveOpen.has(node.id)" @click="toggleLive(node.id)">
          <i class="pi pi-chart-line" />
          <span class="flex-1">{{ liveOpen.has(node.id) ? t('nodes.live.showLess') : t('nodes.live.showMore') }}</span>
          <i class="pi pi-angle-down node-card__more-caret" :class="{ 'node-card__more-caret--open': liveOpen.has(node.id) }" />
        </button>
        <!-- Slides open and closed; kept once opened so it can slide closed (the feed stops when no card is open) -->
        <div class="node-card__live-wrap" :class="{ 'node-card__live-wrap--open': liveOpen.has(node.id) }">
          <div class="node-card__live" :class="{ 'node-card__live--settled': liveSettled.has(node.id) }">
            <NodeLiveCharts v-if="liveSeen.has(node.id)" :samples="liveHistory.nodeSamples.value[node.id] ?? []" :error="liveErrors[node.id]" @retry="retryLive(node)" />
          </div>
        </div>
        <!-- Ping: over this card, under its name (each card its own: several nodes at once) -->
        <NodePingPanel v-if="pinging.has(node.id)" :node="node" class="node-card__ping-panel" @close="togglePing(node.id)" />
      </article>
      <!-- With a few nodes the row has empty room: offer the next one there. -->
      <button v-if="few" key="add" type="button" class="nodes-add-tile" :style="tileHeight ? { height: `${tileHeight}px` } : undefined" @click="addVisible = true">
        <span class="nodes-add-tile__icon"><i class="pi pi-plus" /></span>
        <span class="nodes-add-tile__title">{{ t('nodes.addNode') }}</span>
        <span class="nodes-add-tile__text">{{ t('nodes.addTileText') }}</span>
      </button>
    </TransitionGroup>

    <AddNodeDialog v-model:visible="addVisible" @added="onAdded" />
    <Popover ref="whyPop" class="node-why-pop" @show="whyOpen = true" @hide="whyOpen = false">
      <div @pointerenter="(e: PointerEvent) => e.pointerType === 'mouse' && showWhy(e, whyNodeId!)" @pointerleave="(e: PointerEvent) => e.pointerType === 'mouse' && hideWhySoon()">
        <NodeContactError v-if="whyNodeId !== null && pings[whyNodeId]" :code="pings[whyNodeId]?.code" :detail="pings[whyNodeId]?.error">
          <template #actions>
            <Button :label="t('nodes.checkAgain')" icon="pi pi-refresh" size="small" outlined @click="checkAgainFromSheet" />
          </template>
        </NodeContactError>
      </div>
    </Popover>
    <Dialog
      :visible="syncInfoNode !== null"
      modal
      maximizable
      dismissable-mask
      :header="syncInfoNode ? t('nodes.syncInfoTitle', { name: syncInfoNode.name }) : ''"
      :style="{ width: '64rem' }"
      :breakpoints="{ '1199px': '90vw', '575px': '100vw' }"
      @update:visible="(v: boolean) => !v && (syncInfoNode = null)"
    >
      <NodeSyncPanel v-if="syncInfoNode" :key="syncInfoNode.id" :loader="syncReportLoader(syncInfoNode.id)" embedded />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { liveWatch, type Subscription } from '@/core/live/live'
import { formatBytes, formatCount } from '@/shared/utils/format-metrics'
import AddNodeDialog from '@/features/nodes/components/AddNodeDialog.vue'
import NodeLiveCharts from '@/features/nodes/components/NodeLiveCharts.vue'
import { useMetricHistory } from '@/features/dashboard/composables/useMetricHistory'
import { SYSTEM_REFRESH_MS } from '@/features/dashboard/composables/useDashboard'
import type { DashboardSnapshot } from '@/core/api/generated'
import NodePingPanel from '@/features/nodes/components/NodePingPanel.vue'
import Dialog from 'primevue/dialog'
import Popover from 'primevue/popover'
import NodeContactError from '@/features/nodes/components/NodeContactError.vue'
import { nodeProblems } from '@/shared/composables/useNodeNotices'
import NodeSyncPanel from '@/features/node-home/components/NodeSyncPanel.vue'
import { NodeContactFailure, type NodeSyncLoader } from '@/features/node-home/composables/useNodeSyncStatus'
import { nodesApi, type NodeStatus, type PanelNode } from '@/features/nodes/api'

interface PingState {
  state: 'checking' | 'ok' | 'fail'
  version?: string
  /** Why it failed (hutils.node.contact_error) and the technical text */
  code?: string
  error?: string
}

const REFRESH_MS = 60_000
const DOMAIN_PREVIEW = 3
/** Up to this many nodes, each card shows all its details and an "add node" tile fills the row. */
const FEW_NODES = 3

/** `embedded`: shown inside another page (quick setup), without the page header. */
defineProps<{ embedded?: boolean }>()

const { t, te, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const nodes = ref<PanelNode[]>([])
const panelVersion = ref('')
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref<string | null>(null)
const addVisible = ref(false)
/** The nodes being pinged (their panel is open on their card). */
const pinging = ref<Set<number>>(new Set())
function togglePing(id: number) {
  const next = new Set(pinging.value)
  if (!next.delete(id)) next.add(id)
  pinging.value = next
}
/** The node whose sync report is open. */
const syncInfoNode = ref<PanelNode | null>(null)

/** The node's report through this panel; a node that cannot be asked shows the reason as the panel's error. */
function syncReportLoader(id: number): NodeSyncLoader {
  return async () => {
    const res = await nodesApi.syncReport(id)
    if (!res.report) throw res.error_code ? new NodeContactFailure(res.error_code, res.error) : new Error(res.error || t('nodes.syncInfoUnavailable'))
    return res.report
  }
}
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

const few = computed(() => nodes.value.length <= FEW_NODES)

/** Today's traffic and online users of all nodes together. */
const totals = computed(() =>
  nodes.value.reduce((sum, node) => ({ traffic: sum.traffic + node.details.today_usage, online: sum.online + node.details.today_online }), { traffic: 0, online: 0 }),
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

/** The flag emoji of a country code (two regional indicator letters); '' when there is none. */
function flag(code: string | undefined): string {
  const c = (code ?? '').toUpperCase()
  if (!/^[A-Z]{2}$/.test(c)) return ''
  return String.fromCodePoint(...[...c].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65))
}
function countryName(code: string): string {
  try {
    return new Intl.DisplayNames([locale.value], { type: 'region' }).of(code.toUpperCase()) ?? code
  } catch {
    return code
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
    pings[node.id] = res.online ? { state: 'ok', version: res.version } : { state: 'fail', code: res.error_code, error: res.error }
    // the top bar's notifications follow what was just found
    const others = nodeProblems.value.filter((p) => p.id !== node.id)
    nodeProblems.value = res.online ? others : [...others, { id: node.id, name: node.name, code: res.error_code || 'unknown', detail: res.error }]
  } catch (err) {
    pings[node.id] = { state: 'fail', code: 'unknown', error: apiErrorMessage(err) }
  }
}

// "Not reachable": one sheet for the page, for the node the mouse is over (or that was clicked)
const whyPop = ref<InstanceType<typeof Popover> | null>(null)
const whyNodeId = ref<number | null>(null)
const whyOpen = ref(false)
let whyHideTimer: number | undefined
function showWhy(e: Event, id: number) {
  window.clearTimeout(whyHideTimer)
  if (whyOpen.value && whyNodeId.value === id) return
  if (whyOpen.value) whyPop.value?.hide()
  whyNodeId.value = id
  // the sheet changes node after the old one closed, so it opens next to this one (currentTarget is gone by then)
  const target = e.currentTarget as HTMLElement
  void nextTick(() => whyPop.value?.show(e, target))
}
function hideWhySoon() {
  window.clearTimeout(whyHideTimer)
  whyHideTimer = window.setTimeout(() => whyPop.value?.hide(), 220)
}
function toggleWhy(e: MouseEvent, id: number) {
  // With a mouse the hover already opened it: a click keeps it open. A tap opens and closes it.
  if ((e as PointerEvent).pointerType !== 'mouse' && whyOpen.value && whyNodeId.value === id) whyPop.value?.hide()
  else showWhy(e, id)
}
/** "Check again" under the live charts: the connection check, and the charts asked again now */
function retryLive(node: PanelNode) {
  void pingNode(node)
  liveFeed?.restart()
}
function checkAgainFromSheet() {
  const node = nodes.value.find((n) => n.id === whyNodeId.value)
  whyPop.value?.hide()
  if (node) void pingNode(node)
}

/**
 * The "Add node" tile is as tall as a node card that is not showing its charts: each card has its own height (one
 * card's charts must not stretch its row), so the tile follows the closed cards, measured.
 */
const pageEl = ref<HTMLElement | null>(null)
const tileHeight = ref<number | null>(null)
const cardSizes = new ResizeObserver(() => measureTile())
/** A card's height without its charts (open, opening or closed): with every card open there is no closed one to take. */
function closedHeight(card: HTMLElement): number {
  const wrap = card.querySelector<HTMLElement>('.node-card__live-wrap')
  if (!wrap) return card.offsetHeight
  const gap = parseFloat(getComputedStyle(card).rowGap) || 0
  const top = parseFloat(getComputedStyle(wrap).marginTop) || 0
  return card.offsetHeight - (wrap.getBoundingClientRect().height + gap + top)
}
function measureTile() {
  const cards = [...(pageEl.value?.querySelectorAll<HTMLElement>('.node-card') ?? [])]
  const tallest = Math.max(0, ...cards.map(closedHeight))
  tileHeight.value = tallest > 0 ? Math.round(tallest) : null
}
function watchCards() {
  for (const card of pageEl.value?.querySelectorAll<HTMLElement>('.node-card') ?? []) cardSizes.observe(card)
  measureTile()
}
onUpdated(watchCards)
onBeforeUnmount(() => cardSizes.disconnect())

/**
 * "Show more": the open cards' live charts. One feed for all of them (the dashboard's system snapshot lists every
 * node), every 5 s while at least one is open; 60 samples kept, so the charts show the last 5 minutes.
 */
const liveOpen = ref<Set<number>>(new Set())
/** Cards whose charts were opened once (they stay mounted, to slide closed) */
const liveSeen = ref<Set<number>>(new Set())
/** Fully open: the section stops clipping, so a chart's tooltip can go over its neighbours (clipped while sliding) */
const liveSettled = ref<Set<number>>(new Set())
const liveHistory = useMetricHistory(60)
const liveErrors = reactive<Record<number, { code: string; detail: string } | null>>({})
let liveFeed: Subscription | null = null

function toggleLive(id: number) {
  const next = new Set(liveOpen.value)
  if (!next.delete(id)) next.add(id)
  liveOpen.value = next
  if (next.has(id)) liveSeen.value = new Set(liveSeen.value).add(id)
  const settled = new Set(liveSettled.value)
  settled.delete(id)
  liveSettled.value = settled
  if (next.has(id)) window.setTimeout(() => liveOpen.value.has(id) && (liveSettled.value = new Set(liveSettled.value).add(id)), 380)
  if (next.size && !liveFeed) {
    liveFeed = liveWatch<DashboardSnapshot>('dashboard/', {
      query: () => ({ days: 1, include: 'system', processes: 0 }),
      intervalMs: SYSTEM_REFRESH_MS,
      onData: (snapshot) => {
        const stats = snapshot.node_stats ?? []
        liveHistory.pushNodes(stats)
        for (const node of stats) liveErrors[node.id] = node.ok ? null : { code: node.error_code || 'unknown', detail: node.error || '' }
      },
      onError: () => {},
    })
  } else if (!next.size) {
    stopLive()
  }
}

function stopLive() {
  liveFeed?.stop()
  liveFeed = null
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
    // The node could not be asked: say why and what to do (the "Not reachable" sheet has the rest)
    const why = (err as { response?: { data?: { error_code?: string; error?: string } } })?.response?.data
    if (why?.error_code) {
      pings[node.id] = { state: 'fail', code: why.error_code, error: why.error ?? '' }
      const code = te(`nodes.contact.${why.error_code}.title`) ? why.error_code : 'unknown'
      toast.add({ severity: 'error', summary: t('nodes.syncFailed', { name: node.name }), detail: `${t(`nodes.contact.${code}.title`)}. ${t(`nodes.contact.${code}.fix`)}`, life: 10000 })
    } else toast.add({ severity: 'error', summary: t('nodes.syncFailed', { name: node.name }), detail: apiErrorMessage(err), life: 6000 })
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

let feed: Subscription | null = null

onMounted(async () => {
  // "Last seen" and usage: pushed when a node reports (its row changes), and at least every REFRESH_MS.
  feed = liveWatch<{ nodes: PanelNode[]; panel_version: string }>('nodes/', {
    intervalMs: REFRESH_MS,
    tags: ['child'],
    onData: (res) => {
      nodes.value = res.nodes
      panelVersion.value = res.panel_version
      now.value = Date.now()
    },
  })
  timer = window.setInterval(() => (now.value = Date.now()), 30_000) // relative times move on between updates
  await load()
  void Promise.all(nodes.value.map((node) => pingNode(node)))
})

onBeforeUnmount(() => {
  feed?.stop()
  stopLive()
  window.clearInterval(timer)
})
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
.nodes-summary__icon {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.nodes-summary__totals {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  padding-inline-start: 1.5rem;
  border-inline-start: 1px solid var(--p-content-border-color);
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
  /* Each card its own height: one card's open charts must not stretch the others in its row */
  align-items: start;
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
.node-card__flag {
  flex: none;
  font-size: 1.15em;
  line-height: 1;
  /* colour emoji fonts first: the flag, not its two letters, where the system has one */
  font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
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
.node-check__why {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: help;
  text-decoration: underline dotted color-mix(in srgb, currentColor 55%, transparent);
  text-underline-offset: 3px;
}
.node-check__info {
  font-size: 0.75rem;
  opacity: 0.7;
}
.node-check__again {
  width: 1.75rem !important;
  height: 1.75rem !important;
  margin-inline-start: -0.15rem;
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
.node-card__more,
.node-card__live-toggle {
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
.node-card__live-toggle:hover,
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
/* The live charts slide down (as "More information"), the gap above them only while open */
.node-card__live-wrap {
  display: grid;
  grid-template-rows: 0fr;
  margin-top: -0.9rem;
  transition:
    grid-template-rows 0.35s ease,
    margin-top 0.35s ease;
}
.node-card__live-wrap--open {
  grid-template-rows: 1fr;
  margin-top: 0;
}
.node-card__live {
  min-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.node-card__live-wrap--open .node-card__live {
  opacity: 1;
}
.node-card__live--settled {
  overflow: visible;
}
@media (prefers-reduced-motion: reduce) {
  .node-card__live-wrap,
  .node-card__live {
    transition: none;
  }
}
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
/* Always open (a few nodes): a quiet panel of its own instead of the toggle's drop-down. */
.node-card__info-wrap--inline {
  margin-top: 0;
  transition: none;
}
.node-card__info-wrap--inline .node-card__info {
  padding: 0.75rem 0.85rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
  transition: none;
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
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: auto;
}
.node-card__open {
  flex: 1;
}
/* Labels on one line ("ورود به نود" broke into three beside "Ping"): the row wraps instead */
.node-card__open,
.node-card__ping {
  flex-shrink: 0;
  min-width: max-content;
  white-space: nowrap;
}
/* The ping panel lies over the card below its head (icon, flag, name stay visible), at its own height: a card made
   tall by its open charts does not stretch it */
.node-card__ping-panel {
  position: absolute;
  z-index: 3;
  inset: 4.6rem 0.6rem auto;
  max-height: calc(100% - 5.2rem);
}
.node-card__ping--on {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
/* Delete last, at the row's end (alone on a second row when the card is narrow) */
.node-card__actions > :last-child {
  margin-inline-start: auto;
}

/* "Add node" tile (a few nodes) */
.nodes-add-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 13rem;
  padding: 1.5rem 1.25rem;
  border-radius: 16px;
  border: 1.5px dashed var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  text-align: center;
  cursor: pointer;
  animation: nodes-in 0.4s ease both;
  transition:
    color 0.18s ease,
    border-color 0.18s ease,
    background-color 0.18s ease;
}
.nodes-add-tile:hover,
.nodes-add-tile:focus-visible {
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
}
.nodes-add-tile:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.nodes-add-tile__icon {
  width: 3rem;
  height: 3rem;
  display: grid;
  place-items: center;
  border-radius: 14px;
  font-size: 1.2rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  transition: transform 0.18s ease;
}
.nodes-add-tile:hover .nodes-add-tile__icon {
  transform: scale(1.08);
}
.nodes-add-tile__title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-text-color);
}
.nodes-add-tile__text {
  max-width: 16rem;
  font-size: 0.85rem;
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
  /* Totals take their own line under the status counts. */
  .nodes-summary__totals {
    order: 1;
    width: 100%;
    padding: 0.6rem 0 0;
    border-inline-start: 0;
    border-top: 1px solid var(--p-content-border-color);
  }
  .nodes-add-tile {
    min-height: 9rem;
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
  .nodes-add-tile,
  .nodes-dot--online::after,
  .nodes-empty__sat {
    animation: none;
  }
  .nodes-add-tile:hover .nodes-add-tile__icon {
    transform: none;
  }
  .node-card:hover {
    transform: none;
  }
}
</style>

<style>
/* "Not reachable" sheet (teleported to the body, so not scoped) */
.node-why-pop {
  max-width: min(26rem, calc(100vw - 2rem));
}
.node-why-pop .p-popover-content {
  padding: 0.35rem;
}
</style>
