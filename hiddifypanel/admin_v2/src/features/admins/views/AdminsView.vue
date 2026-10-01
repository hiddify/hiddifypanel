<template>
  <div class="admins-page">
    <div class="admins-head">
      <PageHeader :title="t('admins.title')" :subtitle="t('admins.subtitle')" />
      <Button v-if="tree?.can_create" icon="pi pi-user-plus" :label="t('admins.add')" class="admins-head__add" @click="openCreate" />
    </div>

    <!-- Summary + search -->
    <section v-if="tree" class="admins-bar">
      <div class="admins-bar__stats">
        <span class="admins-bar__stat"><i class="pi pi-sitemap" /><b>{{ formatCount(tree.admins.length) }}</b>{{ t('admins.summary.admins', tree.admins.length) }}</span>
        <span class="admins-bar__stat"><i class="pi pi-users" /><b>{{ formatCount(rootStats.total) }}</b>{{ t('admins.summary.users', rootStats.total) }}</span>
        <span class="admins-bar__stat"><span class="admins-dot" /><b>{{ formatCount(rootStats.online) }}</b>{{ t('admins.summary.online') }}</span>
      </div>
      <IconField class="admins-bar__search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="query" :placeholder="t('admins.search')" class="w-full" :aria-label="t('admins.search')" />
        <InputIcon v-if="query" class="pi pi-times admins-bar__clear" role="button" :aria-label="t('admins.clearSearch')" @click="query = ''" />
      </IconField>
      <div class="admins-bar__filters">
        <Select
          v-model="modeFilter"
          :options="modeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('admins.filter.anyMode')"
          show-clear
          class="admins-bar__filter"
          :aria-label="t('admins.filter.mode')"
        >
          <template #value="{ value, placeholder }">
            <span class="admins-bar__filter-value"><i class="pi pi-shield" />{{ value ? t(`admins.mode.${value}`) : placeholder }}</span>
          </template>
        </Select>
        <Select
          v-model="subFilter"
          :options="subOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('admins.filter.anySub')"
          show-clear
          class="admins-bar__filter"
          :aria-label="t('admins.filter.sub')"
        >
          <template #value="{ value, placeholder }">
            <span class="admins-bar__filter-value"><i class="pi pi-sitemap" />{{ value ? subOptions.find((o) => o.value === value)?.label : placeholder }}</span>
          </template>
        </Select>
      </div>
      <Button icon="pi pi-refresh" text rounded severity="secondary" :loading="refreshing" :aria-label="t('admins.refresh')" v-tooltip.left="t('admins.refresh')" @click="refresh" />
    </section>

    <div v-if="loading" class="admins-card">
      <Skeleton v-for="i in 4" :key="i" height="3.5rem" class="mb-2" border-radius="12px" />
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <div v-else-if="tree" class="admins-card">
      <TreeTable
        :value="nodes"
        v-model:expanded-keys="expandedKeys"
        data-key="key"
        class="admins-table"
      >
        <template #empty>
          <div class="admins-empty-search">
            <i class="pi pi-filter-slash" />{{ t('admins.noMatch') }}
            <Button :label="t('admins.filter.clear')" size="small" text @click="clearFilters" />
          </div>
        </template>

        <Column field="name" :header="t('admins.col.name')" header-class="admins-col--name" body-class="admins-col--name">
          <template #body="{ node }">
            <div class="admins-who" :class="{ 'admins-who--nested': depthOf(node) > 0 }" :style="{ '--depth': depthOf(node) }">
              <div class="admins-who__top">
                <!-- The avatar doubles as the expand/collapse toggle of an admin with sub-admins -->
                <component
                  :is="node.children?.length ? 'button' : 'span'"
                  :type="node.children?.length ? 'button' : undefined"
                  class="admins-avatar"
                  :class="[`admins-avatar--${row(node).mode}`, { 'admins-avatar--toggle': node.children?.length }]"
                  :style="{ '--avatar-hue': hue(row(node).uuid) }"
                  :aria-expanded="node.children?.length ? isExpanded(node) : undefined"
                  :aria-label="node.children?.length ? t(isExpanded(node) ? 'admins.collapse' : 'admins.expand', { name: row(node).name }) : undefined"
                  @click="node.children?.length && toggle(node)"
                >
                  <i v-if="row(node).mode === 'super_admin'" class="pi pi-crown" />
                  <template v-else>{{ initials(row(node).name) }}</template>
                  <span v-if="node.children?.length" class="admins-avatar__caret" :class="{ 'admins-avatar__caret--open': isExpanded(node) }">
                    <i class="pi pi-chevron-down" />
                  </span>
                </component>
                <div class="admins-who__body">
                  <div class="admins-who__name">
                    <span class="admins-who__text" :title="row(node).name"><MarkText :text="row(node).name" :query="query" /></span>
                    <span v-if="row(node).is_me" class="admins-chip admins-chip--me">{{ t('admins.you') }}</span>
                  </div>
                  <div class="admins-who__tags">
                    <span class="admins-mode" :class="`admins-mode--${row(node).mode}`">
                      <i class="pi" :class="row(node).mode === 'super_admin' ? 'pi-crown' : row(node).mode === 'admin' ? 'pi-shield' : 'pi-user'" />{{ t(`admins.mode.${row(node).mode}`) }}
                    </span>
                    <span
                      v-if="row(node).mode !== 'super_admin' && row(node).can_add_admin"
                      class="admins-chip admins-chip--sub"
                      v-tooltip.top="t('admins.canAddHint')"
                    ><i class="pi pi-sitemap" />{{ t('admins.canAddShort') }}</span>
                    <button
                      v-if="node.children?.length"
                      type="button"
                      class="admins-chip admins-chip--toggle"
                      :aria-expanded="isExpanded(node)"
                      @click="toggle(node)"
                    >{{ t('admins.subCount', row(node).sub_admins) }}<i class="pi" :class="isExpanded(node) ? 'pi-angle-up' : 'pi-angle-down'" /></button>
                    <span v-else-if="row(node).sub_admins" class="admins-chip">{{ t('admins.subCount', row(node).sub_admins) }}</span>
                    <button type="button" class="admins-linkbtn" @click="openLink(row(node))">
                      <i class="pi pi-qrcode" /><span>{{ t('admins.showLink') }}</span>
                    </button>
                  </div>
                </div>
                <!-- Actions sit at the top end of the admin -->
                <!-- Your own row: only your users' additional configs can be changed here -->
                <div v-if="row(node).is_me" class="admins-actions">
                  <Button
                    icon="pi pi-paperclip"
                    text
                    rounded
                    size="small"
                    :aria-label="t('admins.myConfigs')"
                    v-tooltip.top="t('admins.myConfigsHint')"
                    @click="openMyConfigs(row(node))"
                  />
                  <span class="admins-you-lock" v-tooltip.top="t('admins.meLocked')"><i class="pi pi-lock" /></span>
                </div>
                <div v-else class="admins-actions">
                  <Button
                    icon="pi pi-pencil"
                    text
                    rounded
                    size="small"
                    :disabled="!row(node).can_edit"
                    :aria-label="t('common.edit')"
                    v-tooltip.top="t('common.edit')"
                    @click="openEdit(row(node))"
                  />
                  <Button
                    icon="pi pi-ellipsis-v"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    :aria-label="t('admins.more')"
                    aria-haspopup="true"
                    @click="openMenu($event, row(node))"
                  />
                </div>
              </div>
              <!-- The users column moves here on small screens, using the full width -->
              <UsageMeters class="admins-who__meters" :stats="row(node).stats" :limits="row(node).limits" />
            </div>
          </template>
        </Column>

        <Column :header="t('admins.col.users')" header-class="admins-col--md" body-class="admins-col--md admins-col--users">
          <template #body="{ node }">
            <UsageMeters :stats="row(node).stats" :limits="row(node).limits" />
          </template>
        </Column>

        <Column :header="t('admins.col.note')" header-class="admins-col--lg" body-class="admins-col--lg admins-col--note">
          <template #body="{ node }">
            <span v-if="row(node).comment" class="admins-note" :title="row(node).comment">{{ row(node).comment }}</span>
            <span v-else class="text-muted-color">—</span>
          </template>
        </Column>
      </TreeTable>

      <!-- Nobody below the signed-in admin yet -->
      <section v-if="tree.admins.length <= 1 && !query" class="admins-empty">
        <div class="admins-empty__art" aria-hidden="true">
          <span class="admins-empty__root"><i class="pi pi-user" /></span>
          <span class="admins-empty__line" />
          <span class="admins-empty__leaf admins-empty__leaf--a"><i class="pi pi-user-plus" /></span>
          <span class="admins-empty__leaf admins-empty__leaf--b"><i class="pi pi-user-plus" /></span>
        </div>
        <h3 class="admins-empty__title">{{ t('admins.empty.title') }}</h3>
        <p class="admins-empty__text">{{ tree.can_create ? t('admins.empty.text') : t('admins.empty.textNoPermission') }}</p>
        <Button v-if="tree.can_create" icon="pi pi-user-plus" :label="t('admins.empty.cta')" @click="openCreate" />
      </section>
    </div>

    <Menu ref="menu" :model="menuItems" popup />

    <MyConfigsDialog v-model:visible="myConfigsVisible" :admin="myRow" @saved="onMyConfigsSaved" />
    <AdminFormDialog v-model:visible="formVisible" :admin="editingAdmin" :tree="tree" @created="onCreated" @saved="onSaved" @reset-password="confirmReset" />
    <AdminLinkDialog v-model:visible="linkVisible" :admin="linkAdmin" :domains="tree?.link_domains ?? []" @reset-password="confirmReset" />
    <AdminCredentialsDialog v-model:visible="credentialsVisible" :name="credentialsName" :credentials="credentials" :kind="credentialsKind" />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import Select from 'primevue/select'
import type { MenuItem } from 'primevue/menuitem'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import TreeTable from 'primevue/treetable'
import type { TreeNode } from 'primevue/treenode'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { formatCount } from '@/shared/utils/format-metrics'
import AdminCredentialsDialog from '@/features/admins/components/AdminCredentialsDialog.vue'
import AdminFormDialog from '@/features/admins/components/AdminFormDialog.vue'
import MyConfigsDialog from '@/features/admins/components/MyConfigsDialog.vue'
import AdminLinkDialog from '@/features/admins/components/AdminLinkDialog.vue'
import UsageMeters from '@/features/admins/components/UsageMeters.vue'
import { adminsApi, type AdminCredentials, type AdminMode, type AdminRow, type AdminsTree } from '@/features/admins/api'

/** Highlights the search match inside a name or UUID. */
const MarkText = defineComponent({
  props: { text: { type: String, required: true }, query: { type: String, default: '' } },
  setup(props) {
    return () => {
      const q = props.query.trim().toLowerCase()
      const at = q ? props.text.toLowerCase().indexOf(q) : -1
      if (at < 0) return props.text
      return [props.text.slice(0, at), h('mark', { class: 'admins-mark' }, props.text.slice(at, at + q.length)), props.text.slice(at + q.length)]
    }
  },
})

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()
const dangerConfirm = useDangerConfirm()

const tree = ref<AdminsTree | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref<string | null>(null)
const query = ref('')
const expandedKeys = ref<Record<string, boolean>>({})
const modeFilter = ref<AdminMode | null>(null)
const subFilter = ref<'yes' | 'no' | null>(null)
const linkAdmin = ref<AdminRow | null>(null)
const linkVisible = ref(false)
const justChanged = ref<string | null>(null)

const formVisible = ref(false)
const editingAdmin = ref<AdminRow | null>(null)
const credentialsVisible = ref(false)
const credentials = ref<AdminCredentials | null>(null)
const credentialsName = ref('')
const credentialsKind = ref<'created' | 'reset'>('created')

const menu = ref<InstanceType<typeof Menu> | null>(null)
const menuAdmin = ref<AdminRow | null>(null)

const rootStats = computed(() => tree.value?.admins.find((a) => a.is_me)?.stats ?? { total: 0, active: 0, online: 0 })

function row(node: TreeNode): AdminRow {
  return node.data as AdminRow
}

/** TreeTable puts a node's `styleClass` on its row. */
function rowClass(admin: AdminRow): string {
  return [admin.is_me ? 'admins-row--me' : '', admin.uuid === justChanged.value ? 'admins-row--new' : ''].join(' ').trim()
}

const MODE_ORDER: AdminMode[] = ['super_admin', 'admin', 'agent']
/** Modes that exist in the tree (super admin and agent always). */
const modeOptions = computed(() => {
  const present = new Set<AdminMode>(['super_admin', 'agent', ...(tree.value?.admins ?? []).map((a) => a.mode)])
  return MODE_ORDER.filter((mode) => present.has(mode)).map((mode) => ({ value: mode, label: t(`admins.mode.${mode}`) }))
})
const subOptions = computed(() => [
  { value: 'yes' as const, label: t('admins.filter.canAdd') },
  { value: 'no' as const, label: t('admins.filter.cannotAdd') },
])
const filtering = computed(() => Boolean(query.value.trim() || modeFilter.value || subFilter.value))

function canAddSubs(admin: AdminRow): boolean {
  return admin.mode === 'super_admin' || admin.can_add_admin
}

function matches(admin: AdminRow): boolean {
  const q = query.value.trim().toLowerCase()
  if (q && !admin.name.toLowerCase().includes(q) && !admin.uuid.toLowerCase().includes(q)) return false
  if (modeFilter.value && admin.mode !== modeFilter.value) return false
  if (subFilter.value && canAddSubs(admin) !== (subFilter.value === 'yes')) return false
  return true
}

function clearFilters() {
  query.value = ''
  modeFilter.value = null
  subFilter.value = null
}

/** Tree depth of each admin (0 = the signed-in admin). */
const depths = computed(() => {
  const rows = tree.value?.admins ?? []
  const byUuid = new Map(rows.map((a) => [a.uuid, a]))
  const out = new Map<string, number>()
  for (const admin of rows) {
    let depth = 0
    let cur = admin
    while (cur.parent_uuid && byUuid.has(cur.parent_uuid) && depth < 50) {
      cur = byUuid.get(cur.parent_uuid)!
      depth += 1
    }
    out.set(admin.uuid, depth)
  }
  return out
})

function depthOf(node: TreeNode): number {
  return depths.value.get(String(node.key)) ?? 0
}

function isExpanded(node: TreeNode): boolean {
  return Boolean(expandedKeys.value[String(node.key)])
}

function toggle(node: TreeNode) {
  const key = String(node.key)
  const next = { ...expandedKeys.value }
  if (next[key]) delete next[key]
  else next[key] = true
  expandedKeys.value = next
}

/** The admin tree; while filtering, matches and the path to them (lenient filter). */
const nodes = computed<TreeNode[]>(() => {
  const rows = tree.value?.admins ?? []
  const build = (parent: string | null): TreeNode[] =>
    rows
      .filter((admin) => admin.parent_uuid === parent)
      .sort((a, b) => Number(b.mode === 'super_admin') - Number(a.mode === 'super_admin') || a.name.localeCompare(b.name))
      .map((admin) => ({ key: admin.uuid, data: admin, styleClass: rowClass(admin), children: build(admin.uuid) }))
      .filter((node) => !filtering.value || matches(node.data) || node.children.length > 0)
  return build(null)
})

function expandAll() {
  expandedKeys.value = Object.fromEntries((tree.value?.admins ?? []).map((a) => [a.uuid, true]))
}

// Filtering opens every branch so matches are visible.
watch(filtering, (on) => {
  if (on) expandAll()
})

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0]![0]! + parts[1]![0]! : (parts[0] ?? '?').slice(0, 2)
  return letters.toUpperCase()
}

/** A stable color per admin. */
function hue(uuid: string): number {
  let sum = 0
  for (const ch of uuid) sum = (sum * 31 + ch.charCodeAt(0)) % 360
  return sum
}

async function load(silent = false) {
  if (!silent) loading.value = true
  loadError.value = null
  try {
    const first = !tree.value
    tree.value = await adminsApi.tree()
    if (first) expandAll()
  } catch (err) {
    if (!silent) loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function refresh() {
  refreshing.value = true
  await load(true)
  refreshing.value = false
}

function flash(uuid: string) {
  justChanged.value = uuid
  window.setTimeout(() => (justChanged.value = null), 2500)
}

function openCreate() {
  editingAdmin.value = null
  formVisible.value = true
}

const myConfigsVisible = ref(false)
const myRow = ref<AdminRow | null>(null)
function openMyConfigs(admin: AdminRow) {
  myRow.value = admin
  myConfigsVisible.value = true
}
function onMyConfigsSaved(rows: AdminRow['additional_configs']) {
  if (myRow.value) myRow.value.additional_configs = rows
  toast.add({ severity: 'success', summary: t('account.configsSaved'), life: 3000 })
}

function openEdit(admin: AdminRow) {
  if (!admin.can_edit) return
  editingAdmin.value = admin
  formVisible.value = true
}

function openLink(admin: AdminRow) {
  linkAdmin.value = admin
  linkVisible.value = true
}

async function copyLink(admin: AdminRow) {
  await navigator.clipboard.writeText(admin.admin_link)
  toast.add({ severity: 'success', summary: t('common.copied'), life: 2000 })
}

function openMenu(event: Event, admin: AdminRow) {
  menuAdmin.value = admin
  menu.value?.toggle(event)
}

const menuItems = computed<MenuItem[]>(() => {
  const admin = menuAdmin.value
  if (!admin) return []
  return [
    { label: t('common.edit'), icon: 'pi pi-pencil', disabled: !admin.can_edit, command: () => openEdit(admin) },
    { label: t('admins.resetPassword'), icon: 'pi pi-key', disabled: !admin.can_edit, command: () => confirmReset(admin) },
    { label: t('admins.showLink'), icon: 'pi pi-qrcode', command: () => openLink(admin) },
    { label: t('admins.copyLink'), icon: 'pi pi-copy', command: () => copyLink(admin) },
    { separator: true },
    { label: t('common.delete'), icon: 'pi pi-trash', class: 'admins-menu--danger', disabled: !admin.can_delete, command: () => confirmDelete(admin) },
  ]
})

async function onCreated(name: string, creds: AdminCredentials) {
  credentialsName.value = name
  credentials.value = creds
  credentialsKind.value = 'created'
  credentialsVisible.value = true
  await load(true)
  const created = tree.value?.admins.find((a) => a.admin_link === creds.admin_link)
  if (created) {
    if (created.parent_uuid) expandedKeys.value = { ...expandedKeys.value, [created.parent_uuid]: true }
    flash(created.uuid)
  }
}

async function onSaved(name: string) {
  toast.add({ severity: 'success', summary: t('admins.saved', { name }), life: 3000 })
  const uuid = editingAdmin.value?.uuid
  await load(true)
  if (uuid) flash(uuid)
}

function confirmReset(admin: AdminRow) {
  confirm.require({
    header: t('admins.resetTitle', { name: admin.name }),
    message: t('admins.resetMessage'),
    icon: 'pi pi-key',
    defaultFocus: 'reject',
    rejectProps: { label: t('common.cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('admins.resetPassword'), severity: 'warn' },
    accept: async () => {
      try {
        const creds = await adminsApi.resetPassword(admin.uuid)
        formVisible.value = false
        linkVisible.value = false
        credentialsName.value = admin.name
        credentials.value = creds
        credentialsKind.value = 'reset'
        credentialsVisible.value = true
        void load(true)
      } catch (err) {
        toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

function confirmDelete(admin: AdminRow) {
  dangerConfirm({
    header: t('admins.deleteTitle', { name: admin.name }),
    message: admin.sub_admins ? t('admins.deleteMessageWithSubs', { count: admin.sub_admins }, admin.sub_admins) : t('admins.deleteMessage'),
    acceptLabel: t('common.delete'),
    accept: async () => {
      try {
        await adminsApi.remove(admin.uuid)
        toast.add({ severity: 'success', summary: t('admins.deleted', { name: admin.name }), life: 3000 })
        await load(true)
      } catch (err) {
        toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

onMounted(() => load())
</script>

<style scoped>
.admins-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0 1rem;
}
.admins-head__add {
  margin-bottom: 1.25rem;
}

/* Summary + search bar */
.admins-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.25rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.admins-bar__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
}
.admins-bar__stat {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--p-text-muted-color);
}
.admins-bar__stat b {
  font-size: 1.05rem;
  color: var(--p-text-color);
}
.admins-bar__stat i {
  color: var(--p-primary-color);
}
.admins-bar__search {
  flex: 1 1 16rem;
  margin-inline-start: auto;
  max-width: 24rem;
}
.admins-bar__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.admins-bar__filter {
  min-width: 10.5rem;
}
.admins-bar__filter-value {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.admins-bar__filter-value i {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.admins-bar__clear {
  cursor: pointer;
}
.admins-dot {
  position: relative;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--p-green-500, #22c55e);
}
.admins-dot::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: admins-ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
}

/* Table card */
.admins-card {
  padding: 0.5rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}
.admins-table :deep(.p-treetable-tbody > tr) {
  transition: background-color 0.2s ease;
  animation: admins-in 0.35s ease both;
}
.admins-table :deep(.p-treetable-tbody > tr > td) {
  padding-block: 0.7rem;
  vertical-align: middle;
}
.admins-table :deep(.p-treetable-thead > tr > th) {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
  background: transparent;
}
.admins-table :deep(tr.admins-row--me) {
  background: color-mix(in srgb, var(--p-primary-color) 5%, transparent);
}
.admins-table :deep(tr.admins-row--new) {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 12%, transparent);
}
.admins-table :deep(.admins-col--name) {
  min-width: 14rem;
}
/* No built-in expander column: the avatar toggles, and the indent below is ours (slimmer). */
.admins-table :deep(.admins-col--name .p-treetable-body-cell-content) {
  align-items: flex-start;
}
.admins-table :deep(.admins-col--users) {
  width: 30rem;
}
.admins-table :deep(.admins-col--note) {
  max-width: 14rem;
}

.admins-actions {
  display: flex;
  gap: 0.1rem;
}
.admins-you-lock {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
  font-size: 0.8rem;
}

/* Name cell */
.admins-who {
  --indent: 1.35rem;
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  min-width: 0;
  padding-inline-start: calc(var(--depth, 0) * var(--indent));
}
/* Guide: an elbow from the parent's column into this admin's avatar. */
.admins-who--nested::before {
  content: '';
  position: absolute;
  top: -0.7rem;
  height: calc(0.7rem + 1.15rem);
  inset-inline-start: calc((var(--depth) - 1) * var(--indent) + 0.55rem);
  width: calc(var(--indent) - 0.55rem);
  border-inline-start: 2px solid var(--p-content-border-color);
  border-bottom: 2px solid var(--p-content-border-color);
  border-end-start-radius: 8px;
}
.admins-who__top {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  min-width: 0;
}
.admins-who__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.admins-actions,
.admins-you-lock {
  flex-shrink: 0;
  margin-inline-start: auto;
  margin-top: -0.2rem;
}
.admins-who__tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
}
.admins-who__meters {
  display: none;
}
.admins-linkbtn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 35%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--p-primary-color) 7%, transparent);
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.admins-linkbtn:hover {
  background: color-mix(in srgb, var(--p-primary-color) 16%, transparent);
}
.admins-linkbtn i {
  font-size: 0.75rem;
}
.admins-avatar {
  flex-shrink: 0;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 0.8rem;
  font-weight: 700;
  color: hsl(var(--avatar-hue) 60% 42%);
  background: hsl(var(--avatar-hue) 70% 50% / 0.14);
}
button.admins-avatar {
  position: relative;
  border: 0;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}
button.admins-avatar--super_admin {
  font-size: 1rem;
}
button.admins-avatar:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 18%, transparent);
}
button.admins-avatar:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.admins-avatar__caret {
  position: absolute;
  inset-inline-end: -0.3rem;
  bottom: -0.3rem;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
  box-shadow: 0 0 0 2px var(--p-content-background);
  transition: transform 0.2s ease;
}
.admins-avatar__caret i {
  font-size: 0.55rem;
}
.admins-avatar__caret--open {
  transform: rotate(180deg);
}
.admins-chip--toggle {
  border: 0;
  font: inherit;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
}
.admins-chip--toggle:hover {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.admins-chip--toggle i {
  font-size: 0.65rem;
}
.admins-avatar--super_admin {
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 16%, transparent);
  font-size: 1rem;
}
:global(.app-dark) .admins-avatar:not(.admins-avatar--super_admin) {
  color: hsl(var(--avatar-hue) 70% 70%);
}
.admins-who__name {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  font-weight: 600;
}
.admins-who__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:deep(.admins-mark) {
  padding: 0 0.1rem;
  border-radius: 3px;
  color: inherit;
  background: color-mix(in srgb, var(--p-amber-400, #fbbf24) 45%, transparent);
}

.admins-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.admins-chip--sub {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 12%, transparent);
}
.admins-chip--me {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.admins-mode {
  --mode-color: var(--p-sky-500, #0ea5e9);
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--mode-color);
  background: color-mix(in srgb, var(--mode-color) 12%, transparent);
}
.admins-mode i {
  font-size: 0.72rem;
}
.admins-mode--super_admin {
  --mode-color: var(--p-amber-600, #d97706);
}
.admins-mode--admin {
  --mode-color: var(--p-violet-500, #8b5cf6);
}

.admins-note {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.admins-empty-search {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem;
  color: var(--p-text-muted-color);
}

/* Empty state (no sub-admins yet) */
.admins-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.6rem;
  margin: 0.5rem;
  padding: 2rem 1rem;
  border-radius: 14px;
  border: 1px dashed var(--p-content-border-color);
}
.admins-empty__art {
  position: relative;
  width: 8rem;
  height: 6rem;
  margin-bottom: 0.25rem;
}
.admins-empty__root,
.admins-empty__leaf {
  position: absolute;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, var(--p-content-background));
}
.admins-empty__root {
  width: 2.8rem;
  height: 2.8rem;
  left: calc(50% - 1.4rem);
  top: 0;
  font-size: 1.2rem;
}
.admins-empty__line {
  position: absolute;
  left: 20%;
  right: 20%;
  top: 3.4rem;
  height: 1rem;
  border: 2px dashed color-mix(in srgb, var(--p-primary-color) 35%, transparent);
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
}
.admins-empty__leaf {
  width: 2.1rem;
  height: 2.1rem;
  bottom: 0;
  font-size: 0.85rem;
  animation: admins-float 3.2s ease-in-out infinite;
}
.admins-empty__leaf--a {
  left: calc(20% - 1.05rem);
}
.admins-empty__leaf--b {
  right: calc(20% - 1.05rem);
  animation-delay: 0.8s;
}
.admins-empty__title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}
.admins-empty__text {
  margin: 0 0 0.5rem;
  max-width: 30rem;
  color: var(--p-text-muted-color);
}

@keyframes admins-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes admins-ping {
  75%,
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
@keyframes admins-float {
  50% {
    transform: translateY(-5px);
  }
}

/* Wide columns step out as the screen narrows; their content moves into the name cell. */
@media (max-width: 1200px) {
  .admins-table :deep(.admins-col--lg) {
    display: none;
  }
}
@media (max-width: 860px) {
  .admins-table :deep(.admins-col--md) {
    display: none;
  }
  .admins-who__meters {
    display: grid;
    padding: 0.6rem 0.75rem;
    border-radius: 12px;
    background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
  }
  .admins-table :deep(.admins-col--name) {
    min-width: 0;
  }
}
@media (max-width: 640px) {
  .admins-head__add {
    width: 100%;
  }
  .admins-bar__search {
    max-width: none;
    flex-basis: 100%;
    order: 3;
  }
  .admins-bar__filters {
    order: 4;
    flex-basis: 100%;
  }
  .admins-bar__filter {
    flex: 1 1 0;
    min-width: 0;
  }
  .admins-card {
    padding: 0.15rem;
    border-radius: 14px;
  }
  .admins-table :deep(.admins-col--name) {
    padding-inline: 0.6rem;
  }
  .admins-who {
    --indent: 0.9rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .admins-table :deep(.p-treetable-tbody > tr),
  .admins-dot::after,
  .admins-empty__leaf {
    animation: none;
  }
}
</style>

<style>
.admins-menu--danger .p-menu-item-icon,
.admins-menu--danger .p-menu-item-label {
  color: var(--p-red-500, #ef4444);
}
</style>
