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
      <!-- Search and filters: one row of same-shaped pills -->
      <div class="dm-filters">
        <IconField v-if="state.domains.length > 4" class="dm-filters__search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="search" :placeholder="t('domains.search')" fluid />
        </IconField>
        <button
          v-for="s in stats"
          :key="s.key"
          type="button"
          class="dm-pill dm-stat"
          :class="[`dm-stat--${s.key}`, { 'dm-pill--on': tlsFilter === s.key }]"
          :aria-pressed="tlsFilter === s.key"
          @click="tlsFilter = tlsFilter === s.key ? null : s.key"
        >
          <i :class="s.icon" />
          <b>{{ s.n }}</b>
          <span>{{ t(`domains.stats.${s.key}`) }}</span>
        </button>
        <template v-if="state.domains.length > 4">
          <button
            v-for="k in presentKinds"
            :key="k"
            type="button"
            class="dm-pill dm-kind-chip"
            :class="{ 'dm-pill--on': kindFilter === k }"
            :style="{ '--tone': KIND_META[k].color }"
            :aria-pressed="kindFilter === k"
            @click="kindFilter = kindFilter === k ? null : k"
          >
            <span>{{ KIND_META[k].emoji }}</span>
            <span>{{ t(`domains.kind.${k}.name`) }}</span>
          </button>
        </template>
      </div>

      <ListFilterStatus :shown="rows.length" :total="state.domains.length" :active="filtering" @reset="resetFilters" />
      <p class="dm-howto"><i class="pi pi-sort-alt" />{{ filtering ? t('domains.howtoFiltered') : t('domains.howto') }}</p>

      <TransitionGroup name="dm-row" tag="ol" class="dm-list" :class="{ 'dm-list--moving': rowDrag.moving.value, 'dm-list--settling': rowDrag.settling.value }">
        <li
          v-for="d in rows"
          :key="d.id"
          class="dm-row"
          :data-domain-id="d.id"
          :style="[{ '--kind-color': KIND_META[kindOf(d.mode)].color }, rowDrag.styleOf(d.id)]"
          :class="{
            'dm-row--minor': isFakeProxyMode(d.fake_mode),
            'dm-row--new': d.id === justChanged,
            'dm-row--lifted': d.id === rowDrag.lifted.value,
            'dm-row--held': d.id === rowDrag.held.value,
          }"
        >
          <!-- Head: order, type, the address (copy) and its badges; the actions at the far side -->
          <div class="dm-row__head" :class="{ 'dm-row__head--chosen': hasChosenProxies(d) }">
            <div class="dm-row__order">
              <span
                v-if="!filtering"
                class="dm-row__handle"
                role="button"
                tabindex="0"
                :aria-label="t('domains.drag')"
                aria-keyshortcuts="ArrowUp ArrowDown"
                v-tooltip.top="t('domains.drag')"
                @pointerdown="!busy && rowDrag.start($event, d.id, rows.map((r) => r.id))"
                @keydown.up.prevent="!busy && position(d) > 0 && move(d, -1)"
                @keydown.down.prevent="!busy && position(d) < state.domains.length - 1 && move(d, 1)"
              ><i class="pi pi-bars" /></span>
              <span class="dm-row__n">{{ position(d) + 1 }}</span>
            </div>

            <span class="dm-row__icon" v-tooltip.top="t(`domains.kind.${kindOf(d.mode)}.name`)"><i :class="KIND_META[kindOf(d.mode)].icon" /></span>

            <div class="dm-row__main">
              <div class="dm-row__title">
                <button
                  v-if="d.domain"
                  type="button"
                  class="dm-row__copy"
                  :aria-label="t('domains.copyDomain')"
                  v-tooltip.top="copiedId === d.id ? t('common.copied') : t('domains.copyDomain')"
                  @click="copyAddress(d)"
                ><i :class="copiedId === d.id ? 'pi pi-check' : 'pi pi-copy'" /></button>
                <a v-if="d.panel_link" :href="d.panel_link" class="dm-row__domain" dir="ltr" target="_blank" rel="noopener" v-tooltip.top="t('domains.openPanel')">{{ d.domain }}</a>
                <span v-else class="dm-row__domain" dir="ltr">{{ d.domain || t('domains.noName') }}</span>
                <span v-if="d.alias && d.alias !== d.domain" class="dm-row__alias">{{ d.alias }}</span>
              </div>
              <div class="dm-row__chips">
                <span class="dm-badge dm-badge--kind">{{ t(`domains.kind.${kindOf(d.mode)}.name`) }}</span>
                <span
                  v-if="d.tls.needs_valid"
                  class="dm-badge"
                  :class="`dm-tls--${certState(d)}`"
                  v-tooltip.top="tlsTooltip(d)"
                >
                  <i :class="certIcon(d)" />
                  {{ certLabel(d) }}
                  <template v-if="d.tls.status === 'valid' && expiresIn(d) !== null"> · {{ t('domains.tls.expiresIn', { n: expiresIn(d) }) }}</template>
                </span>
                <!-- No certificate of its own: its TLS mode, each in its own colour (Valid is the certificate badge above) -->
                <span v-else class="dm-badge dm-mode" :class="`dm-mode--${isFakeProxyMode(d.fake_mode) ? 'proxy' : d.fake_mode}`" v-tooltip.top="t('domains.tls.decoyHint')">
                  <i :class="MODE_ICON[d.fake_mode] ?? 'pi pi-eye-slash'" />{{ t(`domains.tlsMode.${d.fake_mode}`) }}
                </span>
                <span v-if="d.ech" class="dm-badge dm-badge--soft"><i class="pi pi-envelope" />ECH</span>
                <span v-if="d.resolve_ip" class="dm-badge dm-badge--soft"><i class="pi pi-search" />{{ t('domains.badge.resolveIp') }}</span>
                <span v-if="d.cdn_ip && d.fake_mode === 'valid'" class="dm-badge dm-badge--soft" v-tooltip.top="d.cdn_ip"><i class="pi pi-map-marker" />{{ t('domains.badge.cdnIp') }}</span>
                <span v-if="d.tls_port" class="dm-badge dm-badge--port" dir="ltr">TLS :{{ d.tls_port }}</span>
                <span v-if="d.http_port" class="dm-badge dm-badge--port" dir="ltr">HTTP :{{ d.http_port }}</span>
                <span v-if="d.mode === 'cdn' && d.servernames" class="dm-badge dm-badge--soft" dir="ltr" v-tooltip.top="t('domains.badge.frontingHint')"><i class="pi pi-id-card" />{{ d.servernames.split(',')[0] }}<template v-if="d.servernames.split(',').length > 1"> +{{ d.servernames.split(',').length - 1 }}</template></span>
                <span v-if="d.server_domain_id" class="dm-badge dm-badge--soft" dir="ltr"><i class="pi pi-arrow-right" />{{ domainName(d.server_domain_id) }}</span>
                <span v-if="d.download_domain_id" class="dm-badge dm-badge--soft" dir="ltr"><i class="pi pi-download" />{{ domainName(d.download_domain_id) }}</span>
              </div>
              <!-- Its proxies and the configs it shows, side by side on one wrapping line (no empty room around them) -->
              <!-- Chosen proxies stay under the badges; "automatic" and "show configs of" go to the middle block -->
              <div v-if="hasChosenProxies(d)" class="dm-row__line dm-row__chosen">
                <span class="dm-row__key"><i class="pi pi-sitemap" />{{ t('domains.field.proxies') }}</span>
                <span v-for="p in proxiesOf(d)" :key="p.id" class="dm-proxy" :class="{ 'dm-proxy--off': !p.enabled }">
                  <span class="dm-proxy__kind">{{ p.kind === 'sni' ? 'SNI' : p.kind === 'ip' ? 'IP' : 'L7' }}</span>{{ p.name }}
                </span>
              </div>
              <div v-if="!isFakeProxyMode(d.fake_mode) && ((d.mode !== 'sub_link_only' && !hasChosenProxies(d)) || showsConfigs(d))" class="dm-row__lines">
                <div v-if="d.mode !== 'sub_link_only' && !hasChosenProxies(d)" class="dm-row__line">
                  <span class="dm-row__key"><i class="pi pi-sitemap" />{{ t('domains.field.proxies') }}</span>
                  <span class="dm-row__auto">{{ t('domains.proxies.autoShort') }}</span>
                </div>
                <div v-if="showsConfigs(d)" class="dm-row__line">
                  <span class="dm-row__key"><i class="pi pi-eye" />{{ t('domains.field.showDomains') }}</span>
                  <template v-if="d.show_domain_ids.length">
                    <span v-for="id in d.show_domain_ids.slice(0, 4)" :key="id" class="dm-proxy" dir="ltr">{{ showName(id) }}</span>
                    <span v-if="d.show_domain_ids.length > 4" class="dm-row__auto">+{{ d.show_domain_ids.length - 4 }}</span>
                  </template>
                  <span v-else class="dm-row__auto">{{ t('domains.field.showAll') }}</span>
                </div>
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
                <Button v-if="d.domain" icon="pi pi-compass" text rounded severity="secondary" :aria-label="t('domains.ips.title')" v-tooltip.top="t('domains.ips.title')" @click="openIps(d)" />
                <Button icon="pi pi-pencil" text rounded :aria-label="t('common.edit')" v-tooltip.top="t('common.edit')" @click="openEdit(d)" />
                <Button icon="pi pi-ellipsis-v" text rounded severity="secondary" :aria-label="t('domains.more')" aria-haspopup="true" @click="openMenu($event, d)" />
              </div>
            </div>
          </div>

          <!-- The last certificate request failed: shown on the row, not only in the badge's tooltip -->
          <div v-if="certFailed(d)" class="dm-row__cert-error" role="alert">
            <i :class="isRateLimited(d) ? 'pi pi-hourglass' : 'pi pi-exclamation-triangle'" />
            <span class="dm-row__cert-error-text">
              <b>{{ t(isRateLimited(d) ? 'domains.tls.rateLimited' : d.tls.status === 'valid' ? 'domains.tls.renewFailed' : 'domains.tls.failed') }}</b>
              <span v-if="certError(d)" dir="ltr" :title="certError(d)">{{ certError(d) }}</span>
            </span>
            <Button :label="t('domains.cert.retry')" icon="pi pi-refresh" size="small" text @click.stop="openCert(d)" />
          </div>

        </li>
      </TransitionGroup>
      <ListNoMatch v-if="!rows.length" @reset="resetFilters" />
    </template>

    <Menu :key="menuKey" ref="rowMenu" :model="rowItems" popup />
    <DomainIpsDialog v-model:visible="ipsVisible" :domain-id="ipsId" />
    <DomainDialog v-model:visible="editVisible" :row="editing" :state="state" :options="options" @saved="onSaved" />
    <DomainsGuideDialog v-model:visible="guideVisible" @got-it="guideSeen" />
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
import ListFilterStatus from '@/shared/components/ListFilterStatus.vue'
import ListNoMatch from '@/shared/components/ListNoMatch.vue'
import { useHashState } from '@/shared/composables/useHashState'
import { useDragSort } from '@/shared/composables/useDragSort'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { daysUntil, longDate } from '@/shared/utils/dates'
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
import { liveWatch, type Subscription } from '@/core/live/live'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import AddDomainWizard from '@/features/domains/components/AddDomainWizard.vue'
import CertProgress from '@/features/domains/components/CertProgress.vue'
import DomainIpsDialog from '@/features/domains/components/DomainIpsDialog.vue'
import DomainDialog from '@/features/domains/components/DomainDialog.vue'
import { loadDomainProblems, rememberDomainWarnings } from '@/shared/composables/useDomainNotices'
import DomainsGuideDialog from '@/features/domains/components/DomainsGuideDialog.vue'
import { KIND_META, KINDS, TLS_ICON, domainsApi, isFakeProxyMode, kindOf, type DomainKind, type DomainProxy, type DomainRow, type DomainTls, type DomainsOptions, type TlsStatus, type DomainsState } from '@/features/domains/api'

const { t, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

/** The TLS mode's badge icon (domains without a certificate of their own) */
const MODE_ICON: Record<string, string> = { reality: 'pi pi-eye-slash', fake: 'pi pi-clone', dns: 'pi pi-database' }
const state = ref<DomainsState | null>(null)
// The notifications follow the list (a certificate obtained or failed, a domain removed)
watch(state, () => void loadDomainProblems())

/** How to reorder, once in this browser: when the list first shows at least two domains (something to reorder). */
const GUIDE_KEY = 'hiddify.domains.guide.seen'
const guideVisible = ref(false)
function guideWasSeen(): boolean {
  try {
    return localStorage.getItem(GUIDE_KEY) === '1'
  } catch {
    return true // no storage: it could not be kept from showing every visit
  }
}
function guideSeen() {
  try {
    localStorage.setItem(GUIDE_KEY, '1')
  } catch {
    /* private mode */
  }
}
const stopGuideWatch = watch(state, (s) => {
  if (!s || s.domains.length < 2) return
  stopGuideWatch()
  if (!guideWasSeen()) window.setTimeout(() => (guideVisible.value = true), 700)
})
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
useHashState({ q: search, kind: kindFilter, tls: tlsFilter })

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

function resetFilters() {
  search.value = ''
  kindFilter.value = null
  tlsFilter.value = null
}

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
/** The last request failed (ACME error kept on the certificate, or the page's job) and none is running now. */
function certFailed(d: DomainRow): boolean {
  if (!d.tls.needs_valid || d.tls.job?.state === 'running') return false
  return d.tls.job?.state === 'failed' || !!d.tls.error
}
/** Every CA refused for its rate limits (the job says so; after it expires, the stored error does). */
function isRateLimited(d: DomainRow): boolean {
  return !!d.tls.job?.rate_limited || certError(d).startsWith('rate limited')
}
function certError(d: DomainRow): string {
  return (d.tls.job?.state === 'failed' && d.tls.job.error) || d.tls.error || ''
}
type CertState = TlsStatus | 'running' | 'failed' | 'renew_failed'
function certState(d: DomainRow): CertState {
  if (d.tls.job?.state === 'running') return 'running'
  if (certFailed(d)) return d.tls.status === 'valid' ? 'renew_failed' : 'failed'
  return d.tls.status
}
function certIcon(d: DomainRow): string {
  const state = certState(d)
  if (state === 'running') return 'pi pi-spin pi-spinner'
  if (state === 'failed') return 'pi pi-times-circle'
  if (state === 'renew_failed') return 'pi pi-exclamation-triangle'
  return TLS_ICON[state]
}
function certLabel(d: DomainRow): string {
  const state = certState(d)
  if (state === 'running') return t('domains.tls.running')
  if (state === 'failed') return t(isRateLimited(d) ? 'domains.tls.rateLimited' : 'domains.tls.failed')
  if (state === 'renew_failed') return t('domains.tls.renewFailed')
  return t(`domains.tls.${state}`)
}
function expiresIn(d: DomainRow): number | null {
  return daysUntil(d.tls.expires_at)
}
function tlsTooltip(d: DomainRow): string {
  const parts = [t(`domains.tls.${d.tls.status}Hint`)]
  if (d.tls.issuer) parts.push(`${t('domains.tls.issuer')}: ${d.tls.issuer}`)
  if (d.tls.expires_at) parts.push(`${t('domains.tls.expires')}: ${longDate(d.tls.expires_at, locale.value)} (${t('domains.tls.expiresIn', { n: expiresIn(d) })})`)
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
  const warnings = (next.warnings ?? []).map((w) => w.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, ''))
  for (const w of warnings) toast.add({ severity: 'warn', summary: t('domains.warning'), detail: w, life: 9000 })
  // Also in the topbar's notifications, for when the toast went by unread
  rememberDomainWarnings(warnings)
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

/**
 * Moving a domain by its handle, live (mouse, finger or pen): it follows the pointer, the others make room, and on
 * release it glides into its place and the new order is saved.
 */
const rowDrag = useDragSort({
  item: (id) => document.querySelector<HTMLElement>(`[data-domain-id="${id}"]`),
  onDrop: (ids, from, to) => {
    if (filtering.value) return false
    const id = ids[from] as number
    const all = (state.value?.domains ?? []).map((r) => r.id).filter((x) => x !== id)
    const target = ids[to] as number
    all.splice(all.indexOf(target) + (to > from ? 1 : 0), 0, id)
    void reorder(all, id)
    return true
  },
})

/** A domain with proxies picked for it (not "automatic"): that list stays under its badges */
function hasChosenProxies(d: DomainRow): boolean {
  return d.mode !== 'sub_link_only' && !isFakeProxyMode(d.fake_mode) && proxiesOf(d).length > 0
}

/** The address itself, from the copy button before it (the tick shows for a moment) */
const copiedId = ref<number | null>(null)
async function copyAddress(d: DomainRow) {
  await copy(d.domain)
  copiedId.value = d.id
  window.setTimeout(() => copiedId.value === d.id && (copiedId.value = null), 1500)
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

// Certificates requested elsewhere finish in the background: the list is pushed again when a certificate job moves on.
// (Not on every domain change: this page's own saves answer with the new list, and the list request itself may write.)
let feed: Subscription | null = null
onMounted(async () => {
  feed = liveWatch<DomainsState>('domains-page/', {
    intervalMs: 5 * 60_000,
    tags: ['cert'],
    onData: (next) => {
      if (!certVisible.value) state.value = next // as load() does (no warnings again: they came with the save)
    },
  })
  await load()
})
onBeforeUnmount(() => feed?.stop())
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
.dm-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 1rem;
}
.dm-filters__search {
  flex: 1 1 14rem;
  max-width: 20rem;
}
.dm-filters__search :deep(input) {
  height: 2.4rem;
  border-radius: 12px;
  font-size: 0.84rem;
}
/* Every filter is the same pill: one height, radius, border and font. */
.dm-pill {
  --tone: var(--p-primary-color);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  height: 2.4rem;
  padding: 0 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.dm-pill:hover {
  border-color: var(--tone);
}
.dm-pill b {
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.dm-stat i {
  color: var(--tone);
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
.dm-pill--on {
  border-color: var(--tone);
  box-shadow: inset 0 0 0 1px var(--tone);
  background: color-mix(in srgb, var(--tone) 11%, var(--p-content-background));
  color: var(--p-text-color);
}
@media (max-width: 560px) {
  .dm-filters__search {
    flex-basis: 100%;
    max-width: none;
  }
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
/* The whole row follows the page's direction (in Persian the handle, number and icon on the right, the actions on the
   left); only the domain name itself stays left-to-right. */
.dm-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.7rem 0.9rem 0.7rem 0.6rem;
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
/* Desktop: name and badges, then the proxies and "show configs of" one above the other in the middle (the card's
   empty room), then the buttons. The phone layout is in the media query below. */
/* Every row as tall as the tallest kind (name, badges and a line of chosen proxies), so the boxes match; the lines stay
   together in the middle (the extra room is not shared out between them) */
.dm-row__head {
  min-height: 4.7rem;
  align-content: center;
  display: grid;
  /* the middle block has a column of its own share (not just its width at the far side): it starts near the middle */
  grid-template-columns: auto auto minmax(0, 1.1fr) minmax(0, 1fr) auto;
  grid-template-areas:
    'order icon title lines side'
    'order icon chips lines side';
  align-items: center;
  gap: 0.3rem 0.85rem;
}
.dm-row__order {
  grid-area: order;
}
.dm-row__icon {
  grid-area: icon;
}
.dm-row__title {
  grid-area: title;
}
.dm-row__chips {
  grid-area: chips;
}
.dm-row__side {
  grid-area: side;
}
.dm-row__head--chosen {
  grid-template-areas:
    'order icon title lines side'
    'order icon chips lines side'
    'order icon chosen lines side';
}
.dm-row__chosen {
  grid-area: chosen;
}
/* Telegram / ShadowTLS / SS FakeTLS front domains follow their own setting: the same box, only quieter. */
.dm-row.dm-row--minor {
  opacity: 0.72;
}
.dm-row.dm-row--minor:hover {
  opacity: 1;
}
.dm-row--new {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
/* A row moved by its handle: it rides above the others, which slide to make room, and glides into its place */
.dm-list--moving {
  user-select: none;
  -webkit-user-select: none;
}
.dm-list--moving .dm-row {
  transition:
    opacity 0.2s ease,
    box-shadow 0.2s ease,
    translate 0.2s ease;
}
.dm-list--moving .dm-row--lifted {
  position: relative;
  z-index: 5;
  opacity: 1;
  background: var(--p-content-background);
  box-shadow: 0 18px 36px -14px rgb(15 23 42 / 45%);
}
.dm-list--moving .dm-row--lifted .dm-row__handle {
  color: var(--p-primary-color);
  cursor: grabbing;
}
.dm-list--moving .dm-row--held,
.dm-list--settling .dm-row {
  transition: none !important;
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
  /* a finger drags it instead of scrolling the page */
  touch-action: none;
}
.dm-row__handle:hover {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.dm-row__handle:active {
  cursor: grabbing;
}
/* Reordering by keyboard (↑ / ↓) since there are no move buttons */
.dm-row__handle:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 1px;
  color: var(--p-primary-color);
}
/* Indigo: a colour no type or badge of the row uses, so the number reads as the order, not as a state */
.dm-row__n {
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: #fff;
  background: var(--p-indigo-500, #6366f1);
  box-shadow: 0 2px 6px -2px color-mix(in srgb, var(--p-indigo-500, #6366f1) 70%, transparent);
}
.dm-row__icon {
  display: grid;
  place-items: center;
  width: 3.1rem;
  height: 3.1rem;
  border-radius: 14px;
  font-size: 1.45rem;
  color: var(--kind-color);
  background: color-mix(in srgb, var(--kind-color) 13%, transparent);
}
/* Its children are placed in the head's grid */
.dm-row__main {
  display: contents;
}
.dm-row__lines {
  grid-area: lines;
  justify-self: start;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
  max-width: 30rem;
}
.dm-row__line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.4rem;
  font-size: 0.86rem;
}
.dm-row__key {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--p-text-muted-color);
}
.dm-row__key i {
  font-size: 0.8rem;
  color: color-mix(in srgb, var(--kind-color) 80%, var(--p-text-muted-color));
}
/* Copy button, name and alias on one line: a long name ends in "…" rather than leaving the button alone above it */
.dm-row__title {
  display: flex;
  align-items: center;
  gap: 0.15rem 0.5rem;
  min-width: 0;
}
.dm-row__copy {
  display: grid;
  place-items: center;
  flex: none;
  width: 1.65rem;
  height: 1.65rem;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}
.dm-row__copy:hover,
.dm-row__copy:focus-visible {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
  outline: none;
}
.dm-row__copy .pi-check {
  color: var(--p-green-500);
}
.dm-row__domain {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1.02rem;
  font-weight: 650;
  color: var(--p-text-color);
  text-decoration: none;
}
a.dm-row__domain:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}
.dm-row__alias {
  min-width: 0;
  flex: 0 1 auto;
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
.dm-row__side {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dm-row__actions {
  display: flex;
  align-items: center;
}
.dm-row__auto {
  font-size: 0.82rem;
  font-style: italic;
  color: var(--p-text-muted-color);
}
.dm-badge {
  --tone: var(--kind-color);
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.12rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 12%, transparent);
  white-space: nowrap;
}
.dm-badge i {
  font-size: 0.76rem;
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
.dm-tls--renew_failed {
  --tone: var(--p-amber-600, #d97706);
}
.dm-tls--expired,
.dm-tls--failed,
.dm-tls--invalid {
  --tone: var(--p-red-500, #ef4444);
}
.dm-tls--running {
  --tone: var(--p-primary-color);
}
.dm-row__cert-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.4rem;
  padding: 0.35rem 0.6rem;
  border-radius: 10px;
  font-size: 0.82rem;
  color: var(--p-red-600, #dc2626);
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-red-500, #ef4444) 30%, transparent);
}
.dm-row__cert-error-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.dm-row__cert-error-text span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--p-text-muted-color);
}
/* TLS modes without a certificate of their own: Reality, Fake, DNS, the built-in fake-TLS servers */
.dm-mode--reality {
  --tone: var(--p-violet-500, #8b5cf6);
}
.dm-mode--fake {
  --tone: var(--p-orange-500, #f97316);
}
.dm-mode--dns {
  --tone: var(--p-slate-500, #64748b);
}
.dm-mode--proxy {
  --tone: var(--p-sky-500, #0ea5e9);
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
  /* Phone: no row of its own for the buttons (it made the card tall and half empty). The name and badges sit beside
     the handle, number and icon; the proxies line and the buttons share the last line. */
  .dm-row {
    padding: 0.6rem 0.65rem 0.55rem 0.5rem;
    border-radius: 14px;
  }
  .dm-row__head {
    /* the phone layout's lines already make every card as tall: no desktop minimum here */
    min-height: 0;
    grid-template-columns: auto auto minmax(0, 1fr) auto;
    grid-template-areas:
      'order icon title title'
      'order icon chips chips'
      'lines lines lines side';
    gap: 0.3rem 0.55rem;
  }
  .dm-row__order {
    grid-area: order;
  }
  .dm-row__icon {
    grid-area: icon;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 12px;
    font-size: 1.15rem;
  }
  .dm-row__main {
    display: contents;
  }
  .dm-row__title {
    grid-area: title;
  }
  .dm-row__chips {
    grid-area: chips;
  }
  .dm-row__lines {
    grid-area: lines;
    flex-direction: row;
    flex-wrap: wrap;
    align-self: center;
    max-width: none;
    gap: 0.15rem 0.9rem;
  }
  .dm-row__line {
    font-size: 0.8rem;
  }
  /* chosen proxies take the last line, beside the buttons, as the other lines do */
  .dm-row__head--chosen {
    grid-template-areas:
      'order icon title title'
      'order icon chips chips'
      'chosen chosen chosen side'
      'lines lines lines side';
  }
  .dm-row__side {
    grid-area: side;
    align-self: end;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  .dm-row__actions :deep(.p-button) {
    width: 2.1rem;
    height: 2.1rem;
  }
  .dm-filters__search {
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
