<template>
  <PageHeader :title="t('proxy.listTitle')" />
  <section class="qf" :aria-label="t('proxy.quick.label')">
    <button
      type="button"
      class="qf-pill qf-pill--modified"
      :class="{ 'qf-pill--on': filterModified }"
      :aria-pressed="filterModified"
      v-tooltip.bottom="t('proxy.quick.modifiedHint')"
      @click="filterModified = !filterModified"
    >
      <i class="pi pi-pencil" />
      <b>{{ modifiedCount }}</b>
      <span>{{ t('proxy.quick.modified') }}</span>
    </button>

    <MultiSelect
      v-for="g in quickGroups"
      :key="g.key"
      :model-value="quick[g.key] ?? []"
      :options="groupOptions(g)"
      option-label="label"
      option-value="value"
      :show-toggle-all="false"
      :max-selected-labels="0"
      :placeholder="g.title"
      :aria-label="g.title"
      class="qf-select"
      :class="{ 'qf-select--on': quick[g.key]?.length }"
      @update:model-value="(v: string[]) => (quick = { ...quick, [g.key]: v })"
    >
      <template v-if="quick[g.key]?.length" #value="{ value }">
        <span class="qf-value">
          <i :class="g.icon" />
          <span v-if="value.length === 1">{{ g.options.find((o) => o.value === value[0])?.label }}</span>
          <template v-else><span>{{ g.title }}</span><b>{{ value.length }}</b></template>
        </span>
      </template>
      <template #option="{ option }">
        <span class="qf-option">
          <span class="qf-option__label">{{ option.label }}</span>
          <small>{{ option.count }}</small>
        </span>
      </template>
    </MultiSelect>

    <TreeSelect
      v-model="domainModeSelection"
      :options="domainModeTree"
      selection-mode="checkbox"
      display="comma"
      filter
      filter-mode="lenient"
      :placeholder="t('proxy.domainModes')"
      :aria-label="t('proxy.domainModes')"
      class="qf-select"
      :class="{ 'qf-select--on': selectedDomainModes.length }"
    />

    <Button v-if="quickActive" icon="pi pi-times" :label="t('proxy.quick.clear')" text size="small" severity="secondary" @click="clearQuick" />
    <span class="qf__count">{{ t('proxy.quick.showing', { n: filteredProxies.length, total: proxies.length }) }}</span>
  </section>
  <Panel>
    <DataTable
      :value="filteredProxies"
      :loading="loading"
      striped-rows
      paginator
      :rows="10"
      :rows-per-page-options="[10, 25, 50]"
      data-key="id"
    >
      <template #header>
        <div class="flex justify-between items-center flex-wrap gap-3">
          <IconField class="min-w-56 flex-1 max-w-xl">
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="filterSearch"
              :placeholder="t('proxy.searchAll')"
              class="w-full"
            />
          </IconField>
          <div class="flex flex-wrap gap-2">
            <Button icon="pi pi-refresh" severity="secondary" :aria-label="t('common.search')" @click="load" />
            <Button
              icon="pi pi-file-export"
              :label="t('proxy.generateBundle')"
              severity="secondary"
              @click="bundleDialogVisible = true"
            />
            <Button
              icon="pi pi-replay"
              :label="t('proxy.resetAll')"
              severity="secondary"
              outlined
              :loading="resetting"
              @click="confirmResetAll"
            />
            <Button icon="pi pi-plus" :label="t('proxy.new')" as="a" :href="newProxyHref" @click.exact.prevent="openNew" />
          </div>
        </div>
      </template>

      <Column field="enable" sortable class="w-44 shrink-0">
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('common.enabled') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterEnabled !== null ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => enabledPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <div class="list-actions-cell">
            <ToggleSwitch
              :key="`${data.id}-${enableSwitchEpoch}`"
              :model-value="isEffectivelyEnabled(data)"
              @update:model-value="(v: boolean) => toggleEnable(data, v)"
            />
            <Button
              as="a"
              :href="editProxyHref(data.id)"
              icon="pi pi-pencil"
              text
              rounded
              @click.exact.prevent="openEdit(data.id)"
            />
            <Button icon="pi pi-copy" text rounded @click="duplicate(data.id)" />
            <Button
              v-if="!data.is_builtin"
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              @click="confirmDelete(data)"
            />
            <Tag v-if="showsCommonProxy(data)" icon="pi pi-asterisk" v-tooltip="t('proxy.commonProxyBadge')" severity="info" />
            <SysBadge v-if="data.is_builtin" :customized="Boolean(data.server_override || data.client_override)" icon-only class="inline-flex" />
          </div>
        </template>
      </Column>
      <Column field="name" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.name') }}</span>
            <Button
              icon="pi pi-search"
              text
              rounded
              size="small"
              :severity="filterName ? 'primary' : 'secondary'"
              :aria-label="t('common.search')"
              @click="(e: Event) => namePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <a
            class="proxy-name-link"
            :href="editProxyHref(data.id)"
            @click.exact.prevent="openEdit(data.id)"
          >{{ data.name }}</a>
        </template>
      </Column>
      <Column field="proto" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.protocol') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterProto ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => protoPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag v-if="data.proto && !isNoInbound(data)" :value="protoLabel(data.proto)" :style="protoTagStyle(data.proto)" class="proto-tag" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="mode" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.mode') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterMode ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => modePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          {{ modeLabel(data.mode ?? data.protocol) }}
        </template>
      </Column>
      <Column field="categories">
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.categories') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterCategories.length ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => categoriesPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <div v-if="(data.categories || []).length" class="chip-summary-cell">
            <template v-if="isCategoriesExpanded(data.id)">
              <Tag
                v-for="category in data.categories || []"
                :key="category"
                :value="category"
                class="me-1 mb-1"
                severity="secondary"
              />
              <Button
                link
                class="p-0 chip-summary-toggle"
                :label="t('common.collapse', 'less')"
                @click="toggleCategories(data.id)"
              />
            </template>
            <template v-else>
              <Tag
                v-for="category in visibleCategories(data.categories || [])"
                :key="category"
                :value="category"
                class="me-1 mb-1"
                severity="secondary"
              />
              <Button
                v-if="(data.categories || []).length > 2"
                link
                class="p-0 chip-summary-toggle"
                label="…"
                @click="toggleCategories(data.id)"
              />
            </template>
          </div>
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="server_core" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.serverCore') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterCore ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => corePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag v-if="data.server_core" :value="data.server_core" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="tls_layer" sortable>
        <template #header>
          <span>{{ t('proxy.tlsLayer') }}</span>
        </template>
        <template #body="{ data }">
          <span>{{ tlsLayerDisplay(data) }}</span>
        </template>
      </Column>
      <Column field="domain_modes">
        <template #header>
          <span>{{ t('proxy.domainModes') }}</span>
        </template>
        <template #body="{ data }">
          <div v-if="(data.domain_modes || []).length" class="domain-modes-cell">
            <template v-if="isDomainModesExpanded(data.id)">
              <Tag
                v-for="mode in data.domain_modes || []"
                :key="mode"
                :value="t(`proxy.domainModeLabels.${mode}`, mode)"
                class="me-1 mb-1"
                severity="secondary"
              />
              <Button
                link
                class="p-0 domain-modes-toggle"
                :label="t('common.collapse', 'less')"
                @click="toggleDomainModes(data.id)"
              />
            </template>
            <template v-else>
              <span class="domain-modes-summary">{{ domainModesSummary(data.domain_modes || []) }}</span>
              <Button
                v-if="domainModesNeedsExpand(data.domain_modes || [])"
                link
                class="p-0 domain-modes-toggle"
                label="…"
                @click="toggleDomainModes(data.id)"
              />
            </template>
          </div>
          <span v-else>—</span>
        </template>
      </Column>
    </DataTable>
  </Panel>

  <!-- One click on a filter icon: the list is already open (or the text box is focused) -->
  <Popover ref="categoriesPopover" @show="focusFirstInput(categoriesPopover)">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('proxy.categories') }}</label>
      <Listbox v-model="filterCategories" :options="categoryOptions" multiple filter :filter-placeholder="t('common.search')" list-style="max-height: 16rem" class="w-full" />
      <Button v-if="filterCategories.length" :label="t('tags.clear')" icon="pi pi-times" text size="small" severity="secondary" @click="filterCategories = []" />
    </div>
  </Popover>
  <Popover ref="namePopover" @show="focusFirstInput(namePopover)">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('proxy.name') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterName" :placeholder="t('common.search')" class="w-full" @keydown.enter="namePopover.hide()" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="protoPopover" @show="focusFirstInput(protoPopover)">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('proxy.protocol') }}</label>
      <Listbox v-model="filterProto" :options="protoOptions" option-label="label" option-value="value" filter :filter-placeholder="t('common.search')" list-style="max-height: 16rem" class="w-full" @change="protoPopover.hide()">
        <template #option="{ option }">
          <span class="proto-option"><span class="proto-dot" :style="{ background: protoColor(option.value) }" />{{ option.label }}</span>
        </template>
      </Listbox>
    </div>
  </Popover>
  <Popover ref="modePopover" @show="focusFirstInput(modePopover)">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('proxy.mode') }}</label>
      <Listbox v-model="filterMode" :options="modeOptions" option-label="label" option-value="value" filter :filter-placeholder="t('common.search')" list-style="max-height: 16rem" class="w-full" @change="modePopover.hide()" />
    </div>
  </Popover>
  <Popover ref="corePopover" @show="focusFirstInput(corePopover)">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('proxy.serverCore') }}</label>
      <Listbox v-model="filterCore" :options="coreOptions" class="w-full" @change="corePopover.hide()" />
    </div>
  </Popover>
  <Popover ref="enabledPopover">
    <div class="filter-pop">
      <label class="filter-pop__title">{{ t('common.enabled') }}</label>
      <Listbox v-model="filterEnabled" :options="enabledOptions" option-label="label" option-value="value" class="w-full" @change="enabledPopover.hide()" />
    </div>
  </Popover>

  <GenerateBundleDialog v-model:visible="bundleDialogVisible" :meta="meta" />
</template>

<script setup lang="ts">
import { apiErrorMessage } from '@/core/api/client'
defineOptions({ name: 'CustomProxyListView' })

import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'
import Listbox from 'primevue/listbox'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Popover from 'primevue/popover'
import MultiSelect from 'primevue/multiselect'
import TreeSelect from 'primevue/treeselect'
import type { TreeNode } from 'primevue/treenode'
import PageHeader from '@/shared/components/PageHeader.vue'
import { focusFirstInput } from '@/shared/utils/popover-focus'
import { protoColor, protoTagStyle } from '@/shared/utils/proto-color'
import SysBadge from '@/shared/components/SysBadge.vue'
import GenerateBundleDialog from '@/features/custom-proxy/components/GenerateBundleDialog.vue'
import { customProxiesApi, type CustomProxy, type CustomProxyMeta } from '@/core/api/generated'
import { isEffectivelyEnabled, blockedParentEnables, isBlockedByParent, parentEnableConflict, useParentEnablePrompt } from '@/features/custom-proxy/parent-enable'

const { t } = useI18n()
const router = useRouter()
const dangerConfirm = useDangerConfirm()
const toast = useToast()
const { promptParentEnable } = useParentEnablePrompt()
const enableSwitchEpoch = ref(0)

const newProxyHref = computed(() => router.resolve({ name: 'custom-proxy-new' }).href)

function editProxyHref(id: number | undefined) {
  if (id == null) return '#'
  return router.resolve({ name: 'custom-proxy-edit', params: { id: String(id) } }).href
}

function openNew() {
  void router.push({ name: 'custom-proxy-new' })
}

function openEdit(id: number | undefined) {
  if (id == null) return
  void router.push({ name: 'custom-proxy-edit', params: { id: String(id) } })
}

const expandedDomainModeIds = ref<Set<number>>(new Set())
const expandedCategoryIds = ref<Set<number>>(new Set())

function domainModeFamilies(modes: string[]): string[] {
  const families: string[] = []
  const seen = new Set<string>()
  for (const mode of modes) {
    const family = String(mode).split('-')[0] || String(mode)
    if (!seen.has(family)) {
      seen.add(family)
      families.push(family)
    }
  }
  return families
}

function domainModesSummary(modes: string[]): string {
  return domainModeFamilies(modes).join(', ')
}

function domainModesNeedsExpand(modes: string[]): boolean {
  if (modes.length <= 1) return false
  return modes.some((mode) => String(mode).includes('-')) || modes.length > domainModeFamilies(modes).length
}

function isDomainModesExpanded(id: number | undefined): boolean {
  return id != null && expandedDomainModeIds.value.has(id)
}

function toggleDomainModes(id: number | undefined) {
  if (id == null) return
  const next = new Set(expandedDomainModeIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedDomainModeIds.value = next
}

function visibleCategories(categories: string[]): string[] {
  return categories.slice(0, 2)
}

function isCategoriesExpanded(id: number | undefined): boolean {
  return id != null && expandedCategoryIds.value.has(id)
}

function toggleCategories(id: number | undefined) {
  if (id == null) return
  const next = new Set(expandedCategoryIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedCategoryIds.value = next
}

const proxies = ref<CustomProxy[]>([])
const meta = ref<CustomProxyMeta | null>(null)
const bundleDialogVisible = ref(false)
const loading = ref(false)
const modeOptions = ref<{ label: string; value: string }[]>([])
const protoOptions = ref<{ label: string; value: string }[]>([])
const coreOptions = ref<string[]>([])

const filterCategories = ref<string[]>([])
const categoryOptions = ref<string[]>([])

const filterSearch = ref('')
const filterName = ref('')
const filterProto = ref<string | null>(null)
const filterMode = ref<string | null>(null)
const filterCore = ref<string | null>(null)
const filterEnabled = ref<boolean | null>(null)

/* Quick filters: OR inside a group, AND between groups. */
interface QuickOption {
  value: string
  label: string
  test: (row: CustomProxy) => boolean
}
interface QuickGroup {
  key: string
  title: string
  icon: string
  options: QuickOption[]
}

const filterModified = ref(false)
const quick = ref<Record<string, string[]>>({})
const domainModeSelection = ref<Record<string, { checked?: boolean; partialChecked?: boolean }> | null>(null)
const resetting = ref(false)

function rowProto(row: CustomProxy) {
  return row.proto ?? (row as { protocol?: string }).protocol
}
function rowMode(row: CustomProxy) {
  return row.mode ?? (row as { protocol?: string }).protocol
}

/** A built-in proxy whose catalog defaults the admin changed. */
function isModified(row: CustomProxy): boolean {
  return Boolean(row.is_builtin) && (Boolean(row.server_override) || Boolean(row.client_override) || Object.values(row.builtin_overrides ?? {}).some(Boolean))
}

const otherLabel = computed(() => t('proxy.quick.other'))

function listedOptions(known: Array<[string, string, string[]]>, rowValue: (row: CustomProxy) => string | undefined): QuickOption[] {
  const knownValues = new Set(known.flatMap(([, , values]) => values))
  return [
    ...known.map(([value, label, values]) => ({ value, label, test: (row: CustomProxy) => values.includes(rowValue(row) ?? '') })),
    { value: 'other', label: otherLabel.value, test: (row: CustomProxy) => !knownValues.has(rowValue(row) ?? '') },
  ]
}

const quickGroups = computed<QuickGroup[]>(() => [
  {
    key: 'proto',
    icon: 'pi pi-share-alt',
    title: t('proxy.protocol'),
    options: listedOptions(
      [
        ['vless', 'VLESS', ['vless']],
        ['vmess', 'VMess', ['vmess']],
        ['trojan', 'Trojan', ['trojan']],
      ],
      (row) => (isNoInbound(row) ? '' : rowProto(row)),
    ),
  },
  {
    key: 'transport',
    icon: 'pi pi-arrows-h',
    title: t('proxy.transport'),
    options: listedOptions(
      [
        ['xhttp', 'XHTTP', ['xhttp']],
        ['ws', 'WebSocket', ['ws']],
        ['httpupgrade', 'HTTPUpgrade', ['httpupgrade']],
        ['tcp', 'RAW', ['tcp']],
        ['http', 'RawHTTP', ['http']],
        ['grpc', 'gRPC', ['grpc']],
      ],
      (row) => row.transport ?? undefined,
    ),
  },
  {
    key: 'mode',
    icon: 'pi pi-server',
    title: t('proxy.mode'),
    options: listedOptions(
      [
        ['l7', 'L7 gateway', ['domains_l7_gateway']],
        ['sni', 'SNI gateway', ['domains_sni_gateway']],
        ['dns', 'DNS', ['domains_dns_gateway']],
        ['ip', 'IP based', ['ip']],
      ],
      (row) => rowMode(row),
    ),
  },
  {
    key: 'tls',
    icon: 'pi pi-lock',
    title: 'TLS',
    options: [
      { value: 'http', label: 'HTTP', test: (row) => [row.tls_layer, row.download_tls_layer].some((l) => l === 'http') },
      { value: 'tls', label: 'TLS', test: (row) => [row.tls_layer, row.download_tls_layer].some((l) => ['tls', 'tls_h1', 'tls_h2', 'quic_tcp_tls'].includes(l ?? '')) },
      { value: 'quic', label: 'QUIC', test: (row) => [row.tls_layer, row.download_tls_layer].some((l) => ['quic_tls', 'quic_tcp_tls'].includes(l ?? '')) },
    ],
  },
])

function groupOptions(group: QuickGroup) {
  return group.options.map((o) => ({ value: o.value, label: o.label, count: proxies.value.filter((row) => matchesQuick(row, group.key) && o.test(row)).length }))
}

/** Domain modes as a tree: direct → valid, fake…; relay → …; CDN on its own. */
const domainModeTree = computed<TreeNode[]>(() => {
  const modes = new Set<string>(meta.value?.domain_modes ?? [])
  for (const p of proxies.value) for (const m of p.domain_modes ?? []) modes.add(m)
  const families = new Map<string, string[]>()
  for (const m of [...modes].sort()) {
    const family = m.split('-')[0] || m
    families.set(family, [...(families.get(family) ?? []), m])
  }
  return [...families.entries()].map(([family, members]) => {
    const label = (m: string) => t(`proxy.domainModeLabels.${m}`, m)
    if (members.length === 1 && members[0] === family) return { key: family, label: label(family) }
    return { key: `group:${family}`, label: label(family), children: members.map((m) => ({ key: m, label: label(m) })) }
  })
})

const selectedDomainModes = computed(() => {
  const leaves = new Set<string>()
  const walk = (nodes: TreeNode[]) => nodes.forEach((n) => (n.children ? walk(n.children) : leaves.add(String(n.key))))
  walk(domainModeTree.value)
  return Object.entries(domainModeSelection.value ?? {})
    .filter(([key, state]) => state?.checked && leaves.has(key))
    .map(([key]) => key)
})

const modifiedCount = computed(() => proxies.value.filter((row) => matchesQuick(row, 'modified') && isModified(row)).length)
const quickActive = computed(
  () => filterModified.value || selectedDomainModes.value.length > 0 || Object.values(quick.value).some((v) => v.length),
)

function clearQuick() {
  filterModified.value = false
  quick.value = {}
  domainModeSelection.value = null
}

/** `skip`: a group left out, so its options can be counted against all the other filters. */
function matchesQuick(row: CustomProxy, skip?: string): boolean {
  if (skip !== 'modified' && filterModified.value && !isModified(row)) return false
  for (const group of quickGroups.value) {
    if (group.key === skip) continue
    const picked = quick.value[group.key] ?? []
    if (picked.length && !group.options.some((o) => picked.includes(o.value) && o.test(row))) return false
  }
  const modes = selectedDomainModes.value
  if (skip !== 'domain' && modes.length && !(row.domain_modes ?? []).some((m) => modes.includes(m))) return false
  return true
}

function confirmResetAll() {
  dangerConfirm({
    message: t('proxy.resetAllConfirm'),
    header: t('proxy.resetAll'),
    acceptLabel: t('proxy.resetAll'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      resetting.value = true
      try {
        const { reset } = await customProxiesApi.resetAll()
        toast.add({ severity: 'success', summary: t('proxy.resetAllDone', { n: reset }), life: 4000 })
        await load()
      } catch (err) {
        toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
      } finally {
        resetting.value = false
      }
    },
  })
}

const categoriesPopover = ref()
const namePopover = ref()
const protoPopover = ref()
const modePopover = ref()
const corePopover = ref()
const enabledPopover = ref()

const enabledOptions = [
  { label: t('common.enabled'), value: true },
  { label: t('common.disabled'), value: false },
]

const COMMON_PROXY_CORES = new Set(['hiddify-core', 'xray'])

function isNoInbound(row: CustomProxy) {
  return row.mode === 'no_inbound'
}

function showsCommonProxy(row: CustomProxy) {
  return Boolean(row.is_common_proxy) && (isNoInbound(row) || COMMON_PROXY_CORES.has(row.server_core ?? ''))
}

function protoLabel(proto: string | undefined) {
  if (!proto) return '—'
  if (proto === 'shadowsocks') return 'Shadowsocks'
  return proto.toUpperCase()
}

function modeLabel(mode: string | undefined) {
  if (!mode) return '—'
  return t(`proxy.modeLabels.${mode}`, mode)
}

const TLS_LAYER_SHORT: Record<string, string> = {
  http: '-',
  tls_h1: 'TLS H1',
  tls_h2: 'TLS H2',
  tls: 'TLS H2 H1',
  quic_tls: 'QUIC',
  quic_tcp_tls: 'QUIC+TLS',
}

function tlsLayerShort(layer: string | null | undefined): string {
  if (!layer) return ''
  return TLS_LAYER_SHORT[layer] || t(`proxy.tlsLayerLabels.${layer}`, layer)
}

function tlsLayerDisplay(row: CustomProxy): string {
  const up = row.tls_layer
  const down = row.download_tls_layer
  if (!up && !down) return '—'
  if (down && up && down !== up) {
    return `📤${tlsLayerShort(up)} 📥${tlsLayerShort(down)}`
  }
  return tlsLayerShort(up || down)
}

function proxySearchHaystack(row: CustomProxy): string {
  const mode = row.mode ?? (row as { protocol?: string }).protocol
  const proto = row.proto ?? (row as { protocol?: string }).protocol
  const parts = [
    row.name,
    row.slug,
    isNoInbound(row) ? '' : proto,
    isNoInbound(row) ? '' : protoLabel(proto),
    mode,
    modeLabel(mode),
    ...(row.categories ?? []),
    row.server_core,
    row.tls_layer,
    row.download_tls_layer,
    tlsLayerDisplay(row),
    ...(row.domain_modes ?? []),
    ...(row.domain_modes ?? []).map((domainMode) => t(`proxy.domainModeLabels.${domainMode}`, domainMode)),
    isEffectivelyEnabled(row) ? t('common.enabled') : t('common.disabled'),
    showsCommonProxy(row) ? t('proxy.commonProxyBadge') : '',
    row.is_builtin ? 'SYS' : '',
  ]
  return parts.filter((part): part is string => Boolean(part)).join(' ').toLowerCase()
}

const filteredProxies = computed(() =>
  proxies.value.filter((p) => {
    const mode = p.mode ?? (p as { protocol?: string }).protocol
    const proto = p.proto ?? (p as { protocol?: string }).protocol
    const searchQ = filterSearch.value.trim().toLowerCase()
    if (!matchesQuick(p)) return false
    if (searchQ && !proxySearchHaystack(p).includes(searchQ)) return false
    const nameQ = filterName.value.trim().toLowerCase()
    if (nameQ && !(p.name || '').toLowerCase().includes(nameQ) && !(p.slug || '').toLowerCase().includes(nameQ)) {
      return false
    }
    if (filterProto.value && (isNoInbound(p) || proto !== filterProto.value)) return false
    if (filterMode.value && mode !== filterMode.value) return false
    if (filterCore.value && p.server_core !== filterCore.value) return false
    if (filterCategories.value.length && !filterCategories.value.some((category) => (p.categories || []).includes(category))) return false
    if (filterEnabled.value !== null && isEffectivelyEnabled(p) !== filterEnabled.value) return false
    return true
  }),
)

async function load() {
  loading.value = true
  try {
    const [list, metaRes] = await Promise.all([customProxiesApi.list(), customProxiesApi.meta()])
    proxies.value = list
    meta.value = metaRes
    modeOptions.value = (metaRes.modes ?? []).map((m) => ({
      label: t(`proxy.modeLabels.${m}`, m),
      value: m,
    }))
    protoOptions.value = (metaRes.protos ?? []).map((p) => ({
      label: p === 'shadowsocks' ? 'Shadowsocks' : p.toUpperCase(),
      value: p,
    }))
    const cores = new Set<string>()
    const categories = new Set<string>(metaRes.suggested_categories ?? [])
    for (const p of list) {
      if (p.server_core) cores.add(p.server_core)
      for (const category of p.categories ?? []) categories.add(category)
    }
    for (const c of metaRes.server_cores ?? []) cores.add(c)
    coreOptions.value = [...cores].sort()
    categoryOptions.value = [...categories].sort()
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  } finally {
    loading.value = false
  }
}

function rejectBlockedEnable(row: CustomProxy) {
  enableSwitchEpoch.value += 1
  promptParentEnable(blockedParentEnables(row), meta.value?.parent_enable_settings_url)
}

async function toggleEnable(row: CustomProxy, enable: boolean) {
  if (!row.id) return
  if (enable && isBlockedByParent(row)) {
    rejectBlockedEnable(row)
    return
  }
  try {
    const updated = await customProxiesApi.enable(row.id, enable)
    if (enable && isBlockedByParent(updated)) {
      rejectBlockedEnable({ ...row, ...updated })
      return
    }
    Object.assign(row, updated)
  } catch (err: unknown) {
    const conflict = parentEnableConflict(err)
    if (conflict) {
      enableSwitchEpoch.value += 1
      promptParentEnable(conflict.blocked_by, conflict.settings_url)
      return
    }
    enableSwitchEpoch.value += 1
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  }
}

async function duplicate(id: number) {
  let copy
  try {
    copy = await customProxiesApi.duplicate(id)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
    return
  }
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  await load()
  await router.push({ name: 'custom-proxy-edit', params: { id: String(copy.id) } })
}

function confirmDelete(row: CustomProxy) {
  dangerConfirm({
    message: t('common.confirmDelete'),
    header: t('common.delete'),
    acceptLabel: t('common.delete'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      if (!row.id) return
      await customProxiesApi.delete(row.id)
      toast.add({ severity: 'success', summary: t('common.deleted'), life: 3000 })
      await load()
    },
  })
}

onMounted(load)
onActivated(() => {
  // Refresh rows after edit/save while keeping filters/search from KeepAlive.
  void load()
})
</script>

<style scoped>
.qf {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}
.qf__count {
  margin-inline-start: auto;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
/* Every filter is the same pill: one height, radius, border and font. */
.qf-pill,
.qf-select {
  height: 2.4rem;
  min-width: 0;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  font: inherit;
  font-size: 0.84rem;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}
.qf-select {
  width: 10.5rem;
  max-width: 100%;
}
.qf-select--on,
.qf-pill--on {
  border-color: var(--p-primary-color);
  box-shadow: inset 0 0 0 1px var(--p-primary-color);
}
.qf-pill {
  --tone: var(--p-amber-500, #f59e0b);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0 0.75rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.qf-pill:hover {
  border-color: var(--tone);
}
.qf-pill i {
  color: var(--tone);
}
.qf-pill b {
  color: var(--p-text-color);
}
.qf-pill--on {
  --tone: var(--p-amber-500, #f59e0b);
  border-color: var(--tone);
  box-shadow: inset 0 0 0 1px var(--tone);
  background: color-mix(in srgb, var(--tone) 11%, var(--p-content-background));
  color: var(--p-text-color);
}
.qf-value {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.qf-value i {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.qf-option {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}
.qf-option__label {
  flex: 1;
}
.qf-option small {
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
@media (max-width: 560px) {
  .qf-select {
    flex: 1 1 calc(50% - 0.45rem);
    width: auto;
  }
  .qf__count {
    flex: 1 0 100%;
    margin: 0;
  }
}
.filter-pop {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 14rem;
}
.filter-pop__title {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.proto-option {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
}
.proto-dot {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 999px;
}
.proto-tag {
  font-weight: 600;
}
.proxy-name-link,
.list-name-link {
  color: var(--p-primary-color);
  text-decoration: none;
  font-weight: 500;
}
.proxy-name-link:hover,
.list-name-link:hover {
  text-decoration: underline;
}
.list-actions-cell {
  display: inline-flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.15rem;
}
.domain-modes-cell,
.chip-summary-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}
.domain-modes-summary {
  font-size: 0.9rem;
}
.domain-modes-toggle,
.chip-summary-toggle {
  font-size: 0.85rem;
  min-width: auto;
}
</style>
