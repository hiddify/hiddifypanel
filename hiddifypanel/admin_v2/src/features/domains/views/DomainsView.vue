<template>
  <div class="dm-page">
    <div class="dm-head">
      <PageHeader :title="t('domains.title')" :subtitle="t('domains.subtitle')" />
      <Button icon="pi pi-plus" :label="t('domains.add')" class="dm-head__add" @click="wizardVisible = true" />
    </div>

    <ApplyNotice v-model="pendingApply" />

    <div v-if="loading" class="dm-list">
      <Skeleton v-for="i in 3" :key="i" height="6rem" border-radius="16px" />
    </div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <!-- Overview -->
      <div class="dm-stats">
        <button
          v-for="s in stats"
          :key="s.key"
          type="button"
          class="dm-stat"
          :class="[`dm-stat--${s.key}`, { 'dm-stat--on': tlsFilter === s.key }]"
          :aria-pressed="tlsFilter === s.key"
          @click="tlsFilter = tlsFilter === s.key ? null : s.key"
        >
          <i :class="s.icon" />
          <b>{{ s.n }}</b>
          <span>{{ t(`domains.stats.${s.key}`) }}</span>
        </button>
      </div>

      <div v-if="state.domains.length > 4" class="dm-tools">
        <IconField class="dm-tools__search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="search" :placeholder="t('domains.search')" fluid />
        </IconField>
        <div class="dm-tools__kinds">
          <button
            v-for="k in presentKinds"
            :key="k"
            type="button"
            class="dm-kind-chip"
            :class="{ 'dm-kind-chip--on': kindFilter === k }"
            :style="{ '--kind-color': KIND_META[k].color }"
            :aria-pressed="kindFilter === k"
            @click="kindFilter = kindFilter === k ? null : k"
          >
            {{ KIND_META[k].emoji }} {{ t(`domains.kind.${k}.name`) }}
          </button>
        </div>
      </div>

      <p class="dm-howto"><i class="pi pi-sort-alt" />{{ filtering ? t('domains.howtoFiltered') : t('domains.howto') }}</p>

      <TransitionGroup name="dm-row" tag="ol" class="dm-list" :class="{ 'dm-list--dragging': dragId !== null }">
        <li
          v-for="d in rows"
          :key="d.id"
          class="dm-row"
          :style="{ '--kind-color': KIND_META[kindOf(d.mode)].color }"
          :class="{
            'dm-row--minor': isFakeProxyMode(d.fake_mode),
            'dm-row--new': d.id === justChanged,
            'dm-row--drag': d.id === dragId,
            'dm-row--over': d.id === overId && d.id !== dragId,
          }"
          @dragover.prevent="onDragOver(d)"
          @drop.prevent="onDrop(d)"
        >
          <div class="dm-row__order">
            <span
              v-if="!filtering"
              class="dm-row__handle"
              draggable="true"
              :aria-label="t('domains.drag')"
              v-tooltip.top="t('domains.drag')"
              @dragstart="onDragStart($event, d)"
              @dragend="onDragEnd"
            ><i class="pi pi-bars" /></span>
            <span class="dm-row__n">{{ position(d) + 1 }}</span>
          </div>

          <span class="dm-row__emoji" v-tooltip.top="t(`domains.kind.${kindOf(d.mode)}.name`)">{{ KIND_META[kindOf(d.mode)].emoji }}</span>

          <div class="dm-row__body">
            <div class="dm-row__title">
              <a v-if="d.panel_link" :href="d.panel_link" class="dm-row__domain" dir="ltr" target="_blank" rel="noopener" v-tooltip.top="t('domains.openPanel')">{{ d.domain }}</a>
              <span v-else class="dm-row__domain" dir="ltr">{{ d.domain || t('domains.noName') }}</span>
              <span v-if="d.alias && d.alias !== d.domain" class="dm-row__alias">{{ d.alias }}</span>
            </div>

            <div class="dm-row__chips">
              <span class="dm-badge dm-badge--kind">{{ t(`domains.kind.${kindOf(d.mode)}.name`) }}<template v-if="d.fake_mode !== 'valid'"> · {{ t(`domains.tlsMode.${d.fake_mode}`) }}</template></span>
              <span
                v-if="d.tls.needs_valid"
                class="dm-badge"
                :class="`dm-tls--${certState(d)}`"
                v-tooltip.top="tlsTooltip(d)"
              >
                <i :class="certState(d) === 'running' ? 'pi pi-spin pi-spinner' : TLS_ICON[d.tls.status]" />
                {{ certState(d) === 'running' ? t('domains.tls.running') : t(`domains.tls.${d.tls.status}`) }}
                <template v-if="d.tls.status === 'valid' && expiresIn(d) !== null && expiresIn(d)! <= 14"> · {{ t('domains.tls.expiresIn', { n: expiresIn(d) }) }}</template>
              </span>
              <span v-else class="dm-badge dm-tls--decoy" v-tooltip.top="t('domains.tls.decoyHint')"><i class="pi pi-eye-slash" />{{ t('domains.tls.decoy') }}</span>
              <span v-if="d.tls_port" class="dm-badge dm-badge--port" dir="ltr">TLS :{{ d.tls_port }}</span>
              <span v-if="d.http_port" class="dm-badge dm-badge--port" dir="ltr">HTTP :{{ d.http_port }}</span>
              <span v-if="d.mode === 'cdn' && d.servernames" class="dm-badge dm-badge--soft" dir="ltr" v-tooltip.top="t('domains.badge.frontingHint')">🎭 {{ d.servernames.split(',')[0] }}<template v-if="d.servernames.split(',').length > 1"> +{{ d.servernames.split(',').length - 1 }}</template></span>
              <span v-if="d.ech" class="dm-badge dm-badge--soft">🔐 ECH</span>
              <span v-if="d.resolve_ip" class="dm-badge dm-badge--soft">🔢 {{ t('domains.badge.resolveIp') }}</span>
              <span v-if="d.cdn_ip && d.fake_mode === 'valid'" class="dm-badge dm-badge--soft" v-tooltip.top="d.cdn_ip">🔂 {{ t('domains.badge.cdnIp') }}</span>
              <span v-if="d.server_domain_id" class="dm-badge dm-badge--soft" dir="ltr"><i class="pi pi-arrow-right" />{{ domainName(d.server_domain_id) }}</span>
              <span v-if="d.download_domain_id" class="dm-badge dm-badge--soft" dir="ltr">📈 {{ domainName(d.download_domain_id) }}</span>
            </div>

            <div v-if="d.mode !== 'sub_link_only' && !isFakeProxyMode(d.fake_mode)" class="dm-row__line">
              <span class="dm-row__key"><i class="pi pi-sitemap" />{{ t('domains.field.proxies') }}</span>
              <template v-if="proxiesOf(d).length">
                <span v-for="p in proxiesOf(d)" :key="p.id" class="dm-proxy" :class="{ 'dm-proxy--off': !p.enabled }">
                  <span class="dm-proxy__kind">{{ p.kind === 'sni' ? 'SNI' : p.kind === 'ip' ? 'IP' : 'L7' }}</span>{{ p.name }}
                </span>
              </template>
              <span v-else class="dm-row__auto">{{ t('domains.proxies.autoShort') }}</span>
            </div>
            <div v-if="showsConfigs(d) && !isFakeProxyMode(d.fake_mode)" class="dm-row__line">
              <span class="dm-row__key"><i class="pi pi-eye" />{{ t('domains.field.showDomains') }}</span>
              <template v-if="d.show_domain_ids.length">
                <span v-for="id in d.show_domain_ids.slice(0, 4)" :key="id" class="dm-proxy" dir="ltr">{{ showName(id) }}</span>
                <span v-if="d.show_domain_ids.length > 4" class="dm-row__auto">+{{ d.show_domain_ids.length - 4 }}</span>
              </template>
              <span v-else class="dm-row__auto">{{ t('domains.field.showAll') }}</span>
            </div>
          </div>

          <div class="dm-row__side">
            <Button
              v-if="canGetCert(d)"
              :label="t('domains.getCert')"
              icon="pi pi-verified"
              size="small"
              :severity="d.tls.status === 'valid' ? 'secondary' : 'success'"
              outlined
              class="dm-row__cert"
              :disabled="certState(d) === 'running'"
              @click="openCert(d)"
            />
            <div class="dm-row__actions">
              <Button v-if="d.domain" icon="pi pi-compass" text rounded size="small" severity="secondary" :aria-label="t('domains.ips.title')" v-tooltip.top="t('domains.ips.title')" @click="openIps(d)" />
              <Button icon="pi pi-arrow-up" text rounded size="small" severity="secondary" :disabled="busy || filtering || position(d) === 0" :aria-label="t('domains.moveUp')" v-tooltip.top="t('domains.moveUp')" @click="move(d, -1)" />
              <Button icon="pi pi-arrow-down" text rounded size="small" severity="secondary" :disabled="busy || filtering || position(d) === state.domains.length - 1" :aria-label="t('domains.moveDown')" v-tooltip.top="t('domains.moveDown')" @click="move(d, 1)" />
              <Button icon="pi pi-pencil" text rounded size="small" :aria-label="t('common.edit')" v-tooltip.top="t('common.edit')" @click="openEdit(d)" />
              <Button icon="pi pi-ellipsis-v" text rounded size="small" severity="secondary" :aria-label="t('domains.more')" aria-haspopup="true" @click="openMenu($event, d)" />
            </div>
          </div>
        </li>
      </TransitionGroup>
      <p v-if="!rows.length" class="dm-empty"><i class="pi pi-filter-slash" />{{ t('domains.noMatch') }}</p>
    </template>

    <Menu :key="menuKey" ref="rowMenu" :model="rowItems" popup />
    <DomainIpsDialog v-model:visible="ipsVisible" :domain-id="ipsId" />
    <DomainDialog v-model:visible="editVisible" :row="editing" :state="state" :options="options" @saved="onSaved" />
    <AddDomainWizard v-model:visible="wizardVisible" :state="state" @added="onAdded" @edit="openEdit" />

    <Dialog v-model:visible="certVisible" modal :draggable="false" :header="t('domains.getCert')" :style="{ width: 'min(32rem, calc(100vw - 1.5rem))' }" @after-hide="onCertClosed">
      <CertProgress v-if="certRow" :key="certKey" :domain-id="certRow.id" :domain="certRow.domain" :start="certStart" @finished="onCertFinished" />
      <template #footer>
        <Button :label="certDone ? t('domains.wizard.finish') : t('domains.wizard.continueBackground')" icon="pi pi-check" @click="certVisible = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import AddDomainWizard from '@/features/domains/components/AddDomainWizard.vue'
import CertProgress from '@/features/domains/components/CertProgress.vue'
import DomainIpsDialog from '@/features/domains/components/DomainIpsDialog.vue'
import DomainDialog from '@/features/domains/components/DomainDialog.vue'
import { KIND_META, KINDS, TLS_ICON, domainsApi, isFakeProxyMode, kindOf, type DomainKind, type DomainProxy, type DomainRow, type DomainTls, type DomainsOptions, type DomainsState } from '@/features/domains/api'

const { t } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const state = ref<DomainsState | null>(null)
/** Loaded after the list so the page shows right away. */
const options = ref<DomainsOptions | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const pendingApply = ref<RestartMode>('nothing')
const busy = ref(false)
const justChanged = ref<number | null>(null)

const search = ref('')
const kindFilter = ref<DomainKind | null>(null)
type TlsFilter = 'all' | 'valid' | 'attention' | 'decoy'
const tlsFilter = ref<TlsFilter | null>(null)

const editVisible = ref(false)
const editing = ref<DomainRow | null>(null)
const wizardVisible = ref(false)
const rowMenu = ref<InstanceType<typeof Menu> | null>(null)
const menuRow = ref<DomainRow | null>(null)
// Recreating the popup after each change drops its stale scroll handler/target.
const menuKey = ref(0)

const ipsVisible = ref(false)
const ipsId = ref<number | null>(null)
function openIps(d: DomainRow) {
  ipsId.value = d.id
  ipsVisible.value = true
}

const certVisible = ref(false)
const certRow = ref<DomainRow | null>(null)
const certKey = ref(0)
const certDone = ref(false)
/** Ask for a certificate when the dialog opens (false: one was just asked for by saving). */
const certStart = ref(true)

const dragId = ref<number | null>(null)
const overId = ref<number | null>(null)

const byId = computed(() => new Map((state.value?.domains ?? []).map((d) => [d.id, d])))
const proxyById = computed(() => new Map((state.value?.meta.proxies ?? []).map((p) => [p.id, p])))

function needsAttention(d: DomainRow): boolean {
  return d.tls.needs_valid && d.tls.status !== 'valid' && !d.domain.includes('*')
}

const stats = computed(() => {
  const all = state.value?.domains ?? []
  return [
    { key: 'all' as TlsFilter, icon: 'pi pi-globe', n: all.length },
    { key: 'valid' as TlsFilter, icon: 'pi pi-verified', n: all.filter((d) => d.tls.needs_valid && d.tls.status === 'valid').length },
    { key: 'attention' as TlsFilter, icon: 'pi pi-exclamation-triangle', n: all.filter(needsAttention).length },
    { key: 'decoy' as TlsFilter, icon: 'pi pi-eye-slash', n: all.filter((d) => !d.tls.needs_valid).length },
  ].filter((s) => s.key === 'all' || s.n > 0)
})

const presentKinds = computed(() => [...KINDS, 'worker' as DomainKind].filter((k) => (state.value?.domains ?? []).some((d) => kindOf(d.mode) === k)))
const filtering = computed(() => !!search.value.trim() || kindFilter.value !== null || (tlsFilter.value !== null && tlsFilter.value !== 'all'))

const rows = computed(() => {
  const q = search.value.trim().toLowerCase()
  return (state.value?.domains ?? []).filter((d) => {
    if (q && !`${d.domain} ${d.alias}`.toLowerCase().includes(q)) return false
    if (kindFilter.value && kindOf(d.mode) !== kindFilter.value) return false
    if (tlsFilter.value === 'valid' && !(d.tls.needs_valid && d.tls.status === 'valid')) return false
    if (tlsFilter.value === 'attention' && !needsAttention(d)) return false
    if (tlsFilter.value === 'decoy' && d.tls.needs_valid) return false
    return true
  })
})

function position(d: DomainRow): number {
  return (state.value?.domains ?? []).findIndex((x) => x.id === d.id)
}
function domainName(id: number | null): string {
  return (id && byId.value.get(id)?.domain) || '—'
}
/** A shown domain, also a node's (as `Node[name] domain`). */
function showName(id: number): string {
  const o = options.value?.show_options.find((x) => x.id === id)
  if (!o) return domainName(id)
  return o.node ? `Node[${o.node}] ${o.domain}` : o.domain
}
function proxiesOf(d: DomainRow): DomainProxy[] {
  return d.custom_proxy_ids.map((id) => proxyById.value.get(id)).filter(Boolean) as DomainProxy[]
}
/** Same rule as the editor: sub-link domains, or real-certificate domains while there is no sub-link domain. */
function showsConfigs(d: DomainRow): boolean {
  return d.mode === 'sub_link_only' || (!state.value?.meta.has_sublink && d.fake_mode === 'valid')
}
function canGetCert(d: DomainRow): boolean {
  return d.tls.needs_valid && !!d.domain && !d.domain.includes('*') && d.tls.status !== 'valid'
}
function certState(d: DomainRow): string {
  if (d.tls.job?.state === 'running') return 'running'
  return d.tls.status
}
function expiresIn(d: DomainRow): number | null {
  if (!d.tls.expires_at) return null
  return Math.max(0, Math.round((Date.parse(d.tls.expires_at) - Date.now()) / 86_400_000))
}
function tlsTooltip(d: DomainRow): string {
  const parts = [t(`domains.tls.${d.tls.status}Hint`)]
  if (d.tls.issuer) parts.push(`${t('domains.tls.issuer')}: ${d.tls.issuer}`)
  if (d.tls.expires_at) parts.push(`${t('domains.tls.expires')}: ${new Date(d.tls.expires_at).toLocaleDateString()}`)
  if (d.tls.error) parts.push(d.tls.error)
  return parts.join('\n')
}

const rowItems = computed<MenuItem[]>(() => {
  const d = menuRow.value
  if (!d) return []
  return [
    { label: t('common.edit'), icon: 'pi pi-pencil', command: () => openEdit(d) },
    { label: t('domains.openPanel'), icon: 'pi pi-external-link', visible: !!d.panel_link, url: d.panel_link ?? undefined, target: '_blank' },
    { label: t('domains.ips.title'), icon: 'pi pi-compass', visible: !!d.domain, command: () => openIps(d) },
    { label: t('domains.copyDomain'), icon: 'pi pi-copy', visible: !!d.domain, command: () => copy(d.domain) },
    { label: d.tls.status === 'valid' ? t('domains.renewCert') : t('domains.getCert'), icon: 'pi pi-verified', visible: d.tls.needs_valid && !!d.domain && !d.domain.includes('*'), command: () => openCert(d) },
    { separator: true },
    { label: t('common.delete'), icon: 'pi pi-trash', class: 'dm-menu--danger', disabled: (state.value?.domains.length ?? 0) <= 1, command: () => confirmDelete(d) },
  ]
})

function apply(next: DomainsState) {
  state.value = next
  menuKey.value++
  void loadOptions()
  if (next.restart_mode) pendingApply.value = strongerRestartMode(pendingApply.value, next.restart_mode)
  for (const w of next.warnings ?? []) toast.add({ severity: 'warn', summary: t('domains.warning'), detail: w.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, ''), life: 9000 })
}

function flash(id: number | null | undefined) {
  if (!id) return
  justChanged.value = id
  window.setTimeout(() => (justChanged.value = null), 2200)
}

async function loadOptions() {
  try {
    options.value = await domainsApi.options()
  } catch {
    // the dialog falls back to every proxy, and shown domains to this panel's names
  }
}

async function load(quiet = false) {
  if (!quiet) loading.value = true
  loadError.value = null
  try {
    state.value = await domainsApi.list()
    void loadOptions()
  } catch (err) {
    if (!quiet) loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function run(action: () => Promise<DomainsState>, flashId?: number, done?: string) {
  busy.value = true
  try {
    apply(await action())
    flash(flashId)
    if (done) toast.add({ severity: 'success', summary: done, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'warn', summary: t('domains.notChanged'), detail: apiErrorMessage(err), life: 7000 })
  } finally {
    busy.value = false
  }
}

function reorder(ids: number[], flashId?: number) {
  const before = state.value
  if (before) {
    const map = new Map(before.domains.map((d) => [d.id, d]))
    state.value = { ...before, domains: ids.map((id) => map.get(id)!).filter(Boolean) }
  }
  return run(async () => {
    try {
      return await domainsApi.reorder(ids)
    } catch (err) {
      if (before) state.value = before
      throw err
    }
  }, flashId)
}

function move(d: DomainRow, delta: number) {
  const ids = (state.value?.domains ?? []).map((r) => r.id)
  const from = ids.indexOf(d.id)
  const to = from + delta
  if (to < 0 || to >= ids.length) return
  ids.splice(from, 1)
  ids.splice(to, 0, d.id)
  void reorder(ids, d.id)
}

function onDragStart(e: DragEvent, d: DomainRow) {
  dragId.value = d.id
  e.dataTransfer?.setData('text/plain', String(d.id))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onDragOver(d: DomainRow) {
  if (dragId.value !== null) overId.value = d.id
}
function onDragEnd() {
  dragId.value = null
  overId.value = null
}
function onDrop(target: DomainRow) {
  const id = dragId.value
  onDragEnd()
  if (id === null || id === target.id || filtering.value) return
  const all = (state.value?.domains ?? []).map((r) => r.id)
  const movingDown = all.indexOf(id) < all.indexOf(target.id)
  const ids = all.filter((x) => x !== id)
  ids.splice(ids.indexOf(target.id) + (movingDown ? 1 : 0), 0, id)
  void reorder(ids, id)
}

function openMenu(e: Event, d: DomainRow) {
  menuRow.value = d
  const menu = rowMenu.value
  const target = e.currentTarget as HTMLElement | null
  // Always re-show instead of toggling so a stuck open state can't swallow the tap.
  menu?.hide()
  void nextTick(() => menu?.show(e, target ?? undefined))
}

function openEdit(d: DomainRow) {
  editing.value = state.value?.domains.find((x) => x.id === d.id) ?? d
  editVisible.value = true
}

function onSaved(next: DomainsState, row: DomainRow) {
  apply(next)
  flash(row.id)
  toast.add({ severity: 'success', summary: t('domains.saved', { name: row.domain || row.alias }), life: 3000 })
  if (next.certificate_requested) openCert(row, false)
}

function onAdded(next: DomainsState, row: DomainRow) {
  apply({ ...next, warnings: [] })
  flash(row.id)
}

function openCert(d: DomainRow, start = true) {
  certStart.value = start
  certRow.value = d
  certDone.value = false
  certKey.value++
  certVisible.value = true
}
function onCertFinished(_tls: DomainTls | null, ok: boolean) {
  certDone.value = true
  if (ok) toast.add({ severity: 'success', summary: t('domains.cert.ok'), detail: certRow.value?.domain, life: 4000 })
  void load(true)
}
function onCertClosed() {
  certRow.value = null
  void load(true)
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    /* clipboard blocked */
  }
}

function confirmDelete(d: DomainRow) {
  dangerConfirm({
    header: t('domains.deleteTitle', { name: d.domain || d.alias }),
    message: t('domains.deleteMessage'),
    acceptLabel: t('common.delete'),
    accept: () => run(() => domainsApi.remove(d.id), undefined, t('domains.deleted', { name: d.domain || d.alias })),
  })
}

// Certificates requested elsewhere finish in the background: refresh now and then while one is running.
let refresher: number | undefined
onMounted(async () => {
  await load()
  refresher = window.setInterval(() => {
    if (!certVisible.value && state.value?.domains.some((d) => d.tls.job?.state === 'running')) void load(true)
  }, 8000)
})
onBeforeUnmount(() => window.clearInterval(refresher))
</script>

<style scoped>
.dm-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0 1rem;
}
.dm-head__add {
  margin-bottom: 1.25rem;
}

/* Overview tiles (also TLS filters) */
.dm-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.dm-stat {
  --tone: var(--p-primary-color);
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.85rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.dm-stat i {
  color: var(--tone);
}
.dm-stat b {
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}
.dm-stat span {
  color: var(--p-text-muted-color);
}
.dm-stat--valid {
  --tone: var(--p-green-500, #22c55e);
}
.dm-stat--attention {
  --tone: var(--p-amber-500, #f59e0b);
}
.dm-stat--decoy {
  --tone: var(--p-violet-500, #8b5cf6);
}
.dm-stat--on {
  border-color: var(--tone);
  background: color-mix(in srgb, var(--tone) 10%, var(--p-content-background));
}

.dm-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
}
.dm-tools__search {
  flex: 1 1 14rem;
  max-width: 22rem;
}
.dm-tools__kinds {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.dm-kind-chip {
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}
.dm-kind-chip--on {
  border-color: var(--kind-color);
  background: color-mix(in srgb, var(--kind-color) 12%, var(--p-content-background));
}

.dm-howto {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 0.86rem;
  color: var(--p-text-muted-color);
}
.dm-howto i {
  margin-top: 0.15rem;
  color: var(--p-primary-color);
}

/* Ordered list */
.dm-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.dm-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.85rem;
  padding: 0.85rem 1rem 0.85rem 0.6rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 4px solid var(--kind-color);
  animation: dm-in 0.35s ease both;
  transition:
    opacity 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.15s ease;
}
.dm-row:hover {
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.05);
}
/* Telegram / ShadowTLS / SS FakeTLS front domains follow their own setting: smaller and quieter than real domains. */
.dm-row.dm-row--minor {
  gap: 0.5rem 0.6rem;
  padding: 0.35rem 0.75rem 0.35rem 0.4rem;
  border-radius: 10px;
  border-inline-start-width: 3px;
  background: transparent;
  opacity: 0.72;
}
.dm-row.dm-row--minor:hover {
  opacity: 1;
  box-shadow: none;
}
.dm-row--minor .dm-row__emoji {
  width: 1.9rem;
  height: 1.9rem;
  font-size: 0.95rem;
}
.dm-row--minor .dm-row__domain {
  font-size: 0.9rem;
  font-weight: 500;
}
.dm-row--minor .dm-row__chips {
  margin-top: 0.1rem;
}
.dm-row--new {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.dm-row--drag {
  opacity: 0.45;
}
.dm-row--over {
  transform: translateY(2px);
  box-shadow: 0 -3px 0 0 var(--p-primary-color);
}
.dm-row__order {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}
.dm-row__handle {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 2rem;
  border-radius: 8px;
  color: var(--p-text-muted-color);
  cursor: grab;
}
.dm-row__handle:hover {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.dm-row__handle:active {
  cursor: grabbing;
}
.dm-row__n {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.74rem;
  font-weight: 700;
  color: #fff;
  background: var(--kind-color);
}
.dm-row__emoji {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  background: color-mix(in srgb, var(--kind-color) 14%, transparent);
}
.dm-row__body {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.dm-row__title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.2rem 0.6rem;
  min-width: 0;
}
.dm-row__domain {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--p-text-color);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
a.dm-row__domain:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}
.dm-row__alias {
  font-size: 0.84rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dm-row__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.dm-row__line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
}
.dm-row__key {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-inline-end: 0.15rem;
  color: var(--p-text-muted-color);
}
.dm-row__key i {
  font-size: 0.75rem;
}
.dm-row__auto {
  color: var(--p-text-muted-color);
  font-style: italic;
}
.dm-row__side {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dm-row__actions {
  display: flex;
  align-items: center;
}

.dm-badge {
  --tone: var(--kind-color);
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 12%, transparent);
  white-space: nowrap;
}
.dm-badge i {
  font-size: 0.7rem;
}
.dm-badge--soft,
.dm-badge--port {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.dm-badge--port {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.dm-tls--valid {
  --tone: var(--p-green-600, #16a34a);
}
.dm-tls--self_signed,
.dm-tls--missing {
  --tone: var(--p-amber-600, #d97706);
}
.dm-tls--expired,
.dm-tls--invalid {
  --tone: var(--p-red-500, #ef4444);
}
.dm-tls--running {
  --tone: var(--p-primary-color);
}
.dm-tls--decoy {
  --tone: var(--p-violet-500, #8b5cf6);
}
.dm-proxy {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  max-width: 14rem;
  padding: 0.05rem 0.5rem 0.05rem 0.15rem;
  border-radius: 8px;
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dm-proxy:not(:has(.dm-proxy__kind)) {
  padding-inline-start: 0.5rem;
}
.dm-proxy--off {
  opacity: 0.55;
}
.dm-proxy__kind {
  padding: 0 0.3rem;
  border-radius: 6px;
  font-size: 0.64rem;
  font-weight: 700;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.dm-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem 0;
  color: var(--p-text-muted-color);
}

@keyframes dm-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.dm-row-move {
  transition: transform 0.3s ease;
}
.dm-row-leave-active {
  transition: opacity 0.2s ease;
}
.dm-row-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .dm-head__add {
    width: 100%;
  }
  .dm-row {
    grid-template-columns: auto auto minmax(0, 1fr);
    gap: 0.6rem 0.7rem;
    padding: 0.75rem 0.75rem 0.6rem 0.4rem;
    border-radius: 14px;
  }
  .dm-row__handle {
    display: none; /* touch: use the arrows */
  }
  .dm-row__side {
    grid-column: 1 / -1;
    justify-content: space-between;
    padding-top: 0.5rem;
    border-top: 1px solid var(--p-content-border-color);
  }
  .dm-row__side:not(:has(.dm-row__cert)) {
    justify-content: flex-end;
  }
  .dm-tools__search {
    max-width: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .dm-row {
    animation: none;
  }
  .dm-row-move {
    transition: none;
  }
}
</style>

<style>
.dm-menu--danger .p-menu-item-icon,
.dm-menu--danger .p-menu-item-label {
  color: var(--p-red-500, #ef4444);
}
</style>
