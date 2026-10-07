<template>
  <div class="users-page">
    <div class="users-head">
      <PageHeader :title="t('users.title')" :subtitle="t('users.subtitle')" />
      <Button
        icon="pi pi-user-plus"
        :label="t('users.add')"
        class="users-head__add"
        :disabled="state ? !state.can_add : true"
        v-tooltip.bottom="state && !state.can_add ? t('users.limitReached') : ''"
        @click="openAdd"
      />
    </div>

    <!-- Filters with counts: states and what needs attention -->
    <section v-if="state" class="users-filters" :aria-label="t('users.filtersLabel')">
      <template v-for="f in filters" :key="f.key">
      <button
        type="button"
        class="users-filter"
        :class="[`users-filter--${f.key}`, { 'users-filter--on': filter === f.key }]"
        :aria-pressed="filter === f.key"
        v-tooltip.bottom="t(`users.filter.${f.key}Hint`)"
        @click="filter = filter === f.key ? 'all' : f.key"
      >
        <i :class="f.icon" />
        <b>{{ formatCount(f.count) }}</b>
        <span>{{ t(`users.filter.${f.key}`) }}</span>
      </button>
      <!-- Right after "All" -->
      <TagFilter v-if="f.key === 'all'" v-model="pickedTags" :items="allRows" class="users-tagfilter" />
      </template>
    </section>

    <!-- Toolbar -->
    <section v-if="state" class="users-bar">
      <div class="users-bar__find">
        <IconField class="users-bar__search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="query" :placeholder="t('users.search')" class="w-full" :aria-label="t('users.search')" />
          <InputIcon v-if="query" class="pi pi-times users-bar__clear" role="button" :aria-label="t('users.clearSearch')" @click="query = ''" />
        </IconField>
        <Button icon="pi pi-refresh" text rounded severity="secondary" class="users-bar__refresh" :loading="refreshing" :aria-label="t('users.refresh')" v-tooltip.bottom="t('users.refresh')" @click="refresh" />
      </div>
      <div class="users-bar__options">
        <label class="users-check"><Checkbox v-model="groupByOwner" binary /><span>{{ t('users.groupByOwner') }}</span></label>
        <label class="users-check"><ToggleSwitch v-model="inlineEdit" /><span>{{ t('users.inlineEdit') }}</span></label>
        <Select v-model="pageSize" :options="pageOptions" option-label="label" option-value="value" size="small" class="users-bar__page" :aria-label="t('users.perPage')">
          <template #value="{ value }"><i class="pi pi-list" /> {{ pageOptions.find((o) => o.value === value)?.label }}</template>
        </Select>
      </div>
    </section>

    <!-- Bulk actions -->
    <Transition name="users-fade">
      <section v-if="selected.length" class="users-bulk">
        <span class="users-bulk__count"><i class="pi pi-check-square" />{{ t('users.selected', { n: selected.length }, selected.length) }}</span>
        <div class="users-bulk__actions">
          <Button size="small" icon="pi pi-check-circle" :label="t('users.bulk.enable')" severity="secondary" outlined @click="bulk('enable')" />
          <Button size="small" icon="pi pi-ban" :label="t('users.bulk.disable')" severity="secondary" outlined @click="bulk('disable')" />
          <Button size="small" icon="pi pi-refresh" :label="t('users.bulk.reset_usage')" severity="secondary" outlined @click="bulk('reset_usage')" />
          <Button size="small" icon="pi pi-replay" :label="t('users.bulk.reset_days')" severity="secondary" outlined @click="bulk('reset_days')" />
          <Button size="small" icon="pi pi-plus-circle" :label="t('users.bulk.add_limits')" severity="secondary" outlined @click="openAddLimits" />
          <Button size="small" icon="pi pi-tag" :label="t('tags.bulk')" severity="secondary" outlined aria-haspopup="dialog" @click="bulkTagPop?.toggle($event)" />
          <Button size="small" icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined @click="bulk('delete')" />
          <Button size="small" icon="pi pi-times" text severity="secondary" :aria-label="t('users.clearSelection')" @click="selected = []" />
        </div>
      </section>
    </Transition>

    <Message v-if="inlineEdit && !narrow" severity="info" :closable="false" size="small" class="mb-3" icon="pi pi-pencil">{{ t('users.inlineHint') }}</Message>

    <div v-if="loading" class="users-card">
      <Skeleton v-for="i in 6" :key="i" height="3.2rem" class="mb-2" border-radius="10px" />
    </div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <!-- Desktop / tablet: table -->
    <div v-else-if="state && !narrow" class="users-card">
      <DataTable
        v-model:selection="selected"
        v-model:first="first"
        :value="rows"
        data-key="uuid"
        :paginator="paged && rows.length > pageSize"
        :rows="paged ? pageSize : Math.max(rows.length, 1)"
        paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        :current-page-report-template="pageReport"
        :sort-field="groupByOwner ? 'owner_key' : sortField"
        :sort-order="groupByOwner ? 1 : sortOrder"
        :row-group-mode="groupByOwner ? 'subheader' : undefined"
        :group-rows-by="groupByOwner ? 'owner_key' : undefined"
        :edit-mode="inlineEdit ? 'cell' : undefined"
        removable-sort
        size="small"
        class="users-table"
        :row-class="rowClass"
        @sort="onSort"
        @cell-edit-complete="onCellEdit"
      >
        <template #empty>
          <div class="users-empty">
            <i class="pi pi-users" />
            <span>{{ state.users.length ? t('users.noMatch') : t('users.none') }}</span>
            <Button v-if="!state.users.length && state.can_add" icon="pi pi-user-plus" :label="t('users.add')" size="small" @click="openAdd" />
          </div>
        </template>
        <template #groupheader="{ data }">
          <div class="users-group">
            <i class="pi pi-sitemap" />
            <b>{{ ownerPath(data.owner_uuid, data.owner_name) }}</b>
            <span class="text-muted-color">{{ t('users.groupCount', { n: groupSize(data.owner_key) }, groupSize(data.owner_key)) }}</span>
          </div>
        </template>

        <Column selection-mode="multiple" header-style="width: 2.5rem" />
        <Column header-style="width: 4.5rem" body-class="u-actions-cell">
          <template #body="{ data }">
            <div class="u-actions">
              <Button icon="pi pi-pencil" text rounded size="small" :aria-label="t('common.edit')" v-tooltip.top="t('common.edit')" @click="openEdit(data)" />
              <Button icon="pi pi-ellipsis-v" text rounded size="small" severity="secondary" :aria-label="t('users.more')" aria-haspopup="true" @click="openMenu($event, data)" />
            </div>
          </template>
        </Column>

        <Column field="status_rank" sortable header-style="width: 3.5rem" body-class="u-status-cell">
          <template #header><span class="sr-only">{{ t('users.col.status') }}</span></template>
          <template #body="{ data }">
            <ToggleSwitch v-if="inlineEdit" :model-value="data.enable" :aria-label="t('users.form.enabled')" @update:model-value="(v: boolean) => patch(data, { enable: v })" />
            <span v-else class="u-state" :class="`u-state--${data.status}`" :aria-label="t(`users.status.${data.status}`)" v-tooltip.top="`${t(`users.status.${data.status}`)}: ${t(`users.statusHint.${data.status}`)}`">
              <i :class="STATUS_ICON[data.status as UserStatus]" />
            </span>
          </template>
        </Column>

        <Column field="id" :header="t('users.col.id')" sortable header-style="width: 4.5rem">
          <template #body="{ data }">
            <span class="u-id">{{ data.id }}</span>
          </template>
        </Column>

        <Column field="name" :header="t('users.col.name')" sortable>
          <template #body="{ data }">
            <div class="u-who">
              <div class="u-who__line">
                <!-- The link first: every row's QR button lines up -->
                <Button icon="pi pi-qrcode" text rounded size="small" class="u-who__link" :aria-label="t('users.showLink')" v-tooltip.top="t('users.showLink')" @click.stop="openLink(data)" />
                <TagDots kind="user" :uuid="data.uuid" :ids="data.tags" @changed="(ids: number[]) => setTags(data.uuid, ids)" />
                <button type="button" class="u-who__name" :title="data.name" @click="openEdit(data)"><MarkText :text="data.name" :query="query" /></button>
              </div>
              <small v-if="data.comment" class="u-who__note" :title="data.comment"><MarkText :text="data.comment" :query="query" /></small>
              <small v-if="query && data.uuid.includes(query.trim().toLowerCase())" class="u-who__uuid" dir="ltr"><MarkText :text="data.uuid" :query="query" /></small>
            </div>
          </template>
          <template #editor="{ data, field }">
            <div class="flex flex-col gap-1">
              <InputText v-model="data[field]" class="w-full" size="small" autofocus />
              <InputText v-model="data.comment" class="w-full" size="small" :placeholder="t('users.form.note')" />
            </div>
          </template>
        </Column>

        <Column field="usage_ratio" :header="t('users.col.usage')" sortable header-style="width: 12rem">
          <template #body="{ data }">
            <div class="u-usage" @mouseenter="showNodes($event, data)" @mouseleave="hideNodesSoon()">
              <MeterBar :used="data.current_usage_GB" :max="unlimitedGb(data.usage_limit_GB) ? null : data.usage_limit_GB" :text="usageText(data)" size="sm" :segments="usageSegments(data)" />
              <span v-if="data.mode !== 'no_reset'" class="u-reset" v-tooltip.top="t(`users.modeHint.${data.mode}`)">
                <i class="pi pi-sync" />{{ t(`users.resetTag.${data.mode}`) }}<template v-if="data.days_to_reset !== null"> · {{ relativeDays(data.days_to_reset, locale) }}</template>
              </span>
            </div>
          </template>
          <template #editor="{ data }">
            <div class="u-edit-usage">
              <InputNumber v-model="data.usage_limit_GB" :min="0" :max="UNLIMITED_GB" :max-fraction-digits="3" suffix=" GB" size="small" fluid autofocus />
              <Select v-model="data.mode" :options="modeOptions" option-label="label" option-value="value" size="small" class="u-edit-mode" />
              <Button icon="pi pi-refresh" text rounded size="small" severity="warn" :disabled="!data.current_usage_GB" :aria-label="t('users.form.resetUsage')" v-tooltip.top="t('users.form.resetUsage')" @click.stop="quick(data, 'reset_usage')" />
            </div>
          </template>
        </Column>

        <Column field="remaining_days" sortable header-style="width: 10rem">
          <template #header>
            <span class="u-expire-head">
              {{ t('users.col.expire') }}
              <button type="button" class="u-date-toggle" :class="{ 'u-date-toggle--on': showDates }" :aria-pressed="showDates" v-tooltip.top="showDates ? t('users.showRelative') : t('users.showDates')" @click.stop="showDates = !showDates">
                <i class="pi pi-calendar" />
              </button>
            </span>
          </template>
          <template #body="{ data }">
            <span class="u-expire" :class="`u-tone--${expireToneOf(data)}`" v-tooltip.top="expireTitle(data)">
              <i v-if="!data.start_date" class="pi pi-hourglass" />
              {{ expireText(data) }}
            </span>
          </template>
          <template #editor="{ data }">
            <InputNumber v-model="data.package_days" :min="0" :max="UNLIMITED_DAYS" :suffix="` ${t('users.form.daysUnit')}`" size="small" fluid autofocus />
          </template>
        </Column>

        <Column field="last_online_ts" :header="t('users.col.lastOnline')" sortable header-style="width: 9rem">
          <template #body="{ data }">
            <span class="u-online" :class="[`u-tone--${seen(data).tone}`, { 'u-online--hover': data.nodes.length }]" :title="data.last_online && !seen(data).online ? new Date(data.last_online).toLocaleString(locale) : undefined" @mouseenter="showNodes($event, data)" @mouseleave="hideNodesSoon()">
              <span v-if="seen(data).online" class="u-dot" />{{ seen(data).text }}
            </span>
          </template>
        </Column>

      </DataTable>
    </div>

    <!-- Phones: compact cards -->
    <div v-else-if="state" class="u-cards">
      <!-- Select every user the current filter / search shows (all pages), as the table's header checkbox does on a wider screen -->
      <label v-if="rows.length" class="u-selectall">
        <Checkbox :model-value="allPicked" :indeterminate="somePicked && !allPicked" binary :aria-label="t('users.selectAll', { n: rows.length }, rows.length)" @update:model-value="(v: boolean) => toggleAll(v)" />
        <span>{{ t('users.selectAll', { n: rows.length }, rows.length) }}</span>
      </label>
      <template v-for="group in cardGroups" :key="group.key">
        <div v-if="groupByOwner" class="users-group users-group--card"><i class="pi pi-sitemap" /><b>{{ group.owner || '—' }}</b><span class="text-muted-color">{{ group.users.length }}</span></div>
        <article v-for="u in group.users" :key="u.uuid" class="u-card" :class="[`u-card--${u.status}`, { 'u-card--picked': isSelected(u) }]">
          <header class="u-card__head">
            <Checkbox :model-value="isSelected(u)" binary class="u-card__check" :aria-label="t('users.select')" @update:model-value="(v: boolean) => toggleSelect(u, v)" />
            <!-- Status-tinted QR button: the link, first, on every card -->
            <button type="button" class="u-card__qr" :aria-label="t('users.showLink')" @click="openLink(u)">
              <i class="pi pi-qrcode" />
              <span class="u-card__badge" :aria-label="t(`users.status.${u.status}`)"><i :class="STATUS_ICON[u.status]" /></span>
            </button>
            <TagDots kind="user" :uuid="u.uuid" :ids="u.tags" @changed="(ids: number[]) => setTags(u.uuid, ids)" />
            <button type="button" class="u-card__title" @click="openEdit(u)">
              <span class="u-card__name">{{ u.name }}</span>
              <span class="u-card__sub">{{ u.comment || t(`users.status.${u.status}`) }}</span>
            </button>
            <Button icon="pi pi-pencil" text rounded size="small" :aria-label="t('common.edit')" @click="openEdit(u)" />
            <Button icon="pi pi-ellipsis-v" text rounded size="small" severity="secondary" :aria-label="t('users.more')" @click="openMenu($event, u)" />
          </header>
          <div class="u-card__body">
            <MeterBar :used="u.current_usage_GB" :max="unlimitedGb(u.usage_limit_GB) ? null : u.usage_limit_GB" :text="usageText(u)" size="sm" :segments="usageSegments(u)" />
            <div class="u-card__pills">
              <button type="button" class="u-pill" :class="`u-tone--${expireToneOf(u)}`" :aria-label="t('users.col.expire')" @click="showDates = !showDates">
                <i :class="u.start_date ? 'pi pi-calendar' : 'pi pi-hourglass'" />{{ expireText(u) }}
              </button>
              <span class="u-pill" :class="`u-tone--${seen(u).tone}`"><span v-if="seen(u).online" class="u-dot" /><i v-else class="pi pi-wifi" />{{ seen(u).text }}</span>
              <span v-if="u.mode !== 'no_reset'" class="u-pill u-pill--reset"><i class="pi pi-sync" />{{ t(`users.resetTag.${u.mode}`) }}</span>
            </div>
          </div>
        </article>
      </template>
      <div v-if="!rows.length" class="users-empty"><i class="pi pi-users" /><span>{{ state.users.length ? t('users.noMatch') : t('users.none') }}</span></div>
      <Paginator v-if="paged && rows.length > pageSize" v-model:first="first" :rows="pageSize" :total-records="rows.length" template="PrevPageLink CurrentPageReport NextPageLink" :current-page-report-template="pageReport" />
    </div>

    <Menu ref="rowMenu" :model="menuItems" popup />

    <!-- Hover breakdown of the last status / usage cell: one row per node -->
    <Popover ref="nodesPop" append-to="body" @mouseenter="cancelHideNodes" @mouseleave="hideNodesSoon">
      <div v-if="nodesBreakdown.length" class="un">
        <div class="un__title"><i class="pi pi-sitemap" />{{ t('users.nodes.title') }}</div>
        <div v-for="n in nodesBreakdown" :key="n.key" class="un__row">
          <span class="un__dot" :style="{ background: n.color }" />
          <span class="un__name" :title="n.name">{{ n.name }}</span>
          <span class="un__seen" :class="`u-tone--${n.seen.tone}`"><span v-if="n.seen.online" class="u-dot" />{{ n.seen.text }}</span>
          <span class="un__usage" dir="ltr">{{ n.usage }}</span>
        </div>
      </div>
    </Popover>

    <!-- Add limits: data and days on top of what the selected users have -->
    <Dialog v-model:visible="limitsVisible" modal :draggable="false" :header="t('users.addLimits.title', { n: selected.length }, selected.length)" :style="{ width: '24rem' }" :breakpoints="{ '575px': 'calc(100vw - 2rem)' }">
      <p class="al-hint">{{ t('users.addLimits.hint') }}</p>
      <form class="al-form" @submit.prevent="applyLimits">
        <div class="al-field">
          <label for="al-gb" class="font-medium">{{ t('users.addLimits.gb') }}</label>
          <InputNumber v-model="limitsGb" input-id="al-gb" :min="0" :max="UNLIMITED_GB" :max-fraction-digits="3" suffix=" GB" fluid autofocus />
        </div>
        <div class="al-field">
          <label for="al-days" class="font-medium">{{ t('users.addLimits.days') }}</label>
          <InputNumber v-model="limitsDays" input-id="al-days" :min="0" :max="3650" :suffix="` ${t('users.form.daysUnit')}`" fluid />
        </div>
        <small class="al-note">{{ t('users.addLimits.note') }}</small>
      </form>
      <template #footer>
        <Button :label="t('common.cancel')" severity="secondary" text @click="limitsVisible = false" />
        <Button icon="pi pi-plus-circle" :label="t('users.addLimits.apply')" :loading="limitsBusy" :disabled="!limitsGb && !limitsDays" @click="applyLimits" />
      </template>
    </Dialog>
    <Popover ref="bulkTagPop" append-to="body">
      <TagPicker :selected="bulkTagState.all" :partial="bulkTagState.some" :title="t('tags.bulk')" :hint="t('tags.bulkHint')" @toggle="bulkTag" @create="(id: number) => bulkTag(id, true)" />
    </Popover>

    <UserFormDialog v-model:visible="formVisible" :user="editingUser" :state="state" @saved="onSaved" />
    <LinkShareDialog
      v-if="linkUser && state"
      v-model:visible="linkVisible"
      :title="t('users.linkTitle', { name: linkUser.name })"
      :name="linkUser.name"
      :domains="state.link_domains"
      :path="userLinkPath(linkUser)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import DataTable, { type DataTableCellEditCompleteEvent, type DataTableSortEvent } from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import Message from 'primevue/message'
import Paginator from 'primevue/paginator'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import ToggleSwitch from 'primevue/toggleswitch'
import PageHeader from '@/shared/components/PageHeader.vue'
import LinkShareDialog from '@/shared/components/LinkShareDialog.vue'
import MeterBar from '@/shared/components/MeterBar.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { formatCount } from '@/shared/utils/format-metrics'
import { matchesTags, useTags } from '@/features/tags/useTags'
import { tagsApi } from '@/features/tags/api'
import TagDots from '@/features/tags/components/TagDots.vue'
import TagFilter from '@/features/tags/components/TagFilter.vue'
import TagPicker from '@/features/tags/components/TagPicker.vue'
import UserFormDialog from '@/features/users/components/UserFormDialog.vue'
import { STATUS_ICON, UNLIMITED_DAYS, UNLIMITED_GB, USER_MODES, userLinkPath, usersApi, type BulkAction, type UserDetail, type UserPayload, type UserRow, type UserStatus, type UsersState } from '@/features/users/api'
import { expireTone, gb, lastSeen, nodeColor, ONE_GIG, relativeDays, shortDate, type Tone } from '@/features/users/format'

/** Highlights the search match. */
const MarkText = defineComponent({
  props: { text: { type: String, required: true }, query: { type: String, default: '' } },
  setup(props) {
    return () => {
      const q = props.query.trim().toLowerCase()
      const at = q ? props.text.toLowerCase().indexOf(q) : -1
      if (at < 0) return props.text
      return [props.text.slice(0, at), h('mark', { class: 'u-mark' }, props.text.slice(at, at + q.length)), props.text.slice(at + q.length)]
    }
  },
})

type Row = UserRow & { status_rank: number; usage_ratio: number; last_online_ts: number; owner_key: string }
type FilterKey = 'all' | UserStatus | 'expiring' | 'data_low' | 'not_started' | 'unseen_week'

const STATUS_ORDER: UserStatus[] = ['active', 'no_data', 'expired', 'disabled']
/** "Soon": a week left, or 80% of the data used. */
const SOON_DAYS = 7
const SOON_USAGE = 0.8
const WEEK_MS = 7 * 86400_000
const PREFS_KEY = 'hiddify.users.prefs'

const { t, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const state = ref<UsersState | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref<string | null>(null)
const query = ref('')
const filter = ref<FilterKey>('all')
const pickedTags = ref<number[]>([])
const selected = ref<Row[]>([])
const sortField = ref<string | undefined>(undefined)
const sortOrder = ref<1 | -1 | 0 | undefined>(undefined)
const first = ref(0)
const now = ref(Date.now())
let timer: number | undefined

// Remembered per browser: grouping, dates, page size (0 = all).
function readPrefs(): Record<string, unknown> {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY) || '{}')
  } catch {
    return {}
  }
}
const prefs = readPrefs()
const groupByOwner = ref(Boolean(prefs.groupByOwner))
const showDates = ref(Boolean(prefs.showDates))
const pageSize = ref<number>([10, 100, 0].includes(Number(prefs.pageSize)) ? Number(prefs.pageSize) : 10)
const inlineEdit = ref(false)
watch([groupByOwner, showDates, pageSize], () => {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify({ groupByOwner: groupByOwner.value, showDates: showDates.value, pageSize: pageSize.value }))
  } catch {
    /* private mode: not remembered */
  }
})
const paged = computed(() => pageSize.value > 0)
/** PrimeVue fills {first} {last} {totalRecords}: hand them through vue-i18n untouched. */
const pageReport = computed(() => t('users.pageReport', { first: '{first}', last: '{last}', totalRecords: '{totalRecords}' }))
const pageOptions = computed(() => [
  { value: 10, label: '10' },
  { value: 100, label: '100' },
  { value: 0, label: t('users.all') },
])

// Narrow screens get cards.
const narrowQuery = window.matchMedia('(max-width: 768px)')
const narrow = ref(narrowQuery.matches)
const onNarrow = (e: MediaQueryListEvent) => (narrow.value = e.matches)

const formVisible = ref(false)
const editingUser = ref<UserRow | null>(null)
const linkVisible = ref(false)
const linkUser = ref<UserRow | null>(null)
const rowMenu = ref<InstanceType<typeof Menu> | null>(null)
const menuUser = ref<UserRow | null>(null)

const modeOptions = computed(() => USER_MODES.map((m) => ({ value: m, label: t(`users.mode.${m}`) })))

function unlimitedGb(v: number): boolean {
  return v >= UNLIMITED_GB
}

/**
 * Groups are admins, not names (several admins may share a name): keyed by tree position, so the
 * signed-in admin comes first and each sub-admin follows its parent.
 */
const ownerOrder = computed(() => {
  const admins = state.value?.admins ?? []
  const order = new Map<string, { index: number; path: string }>()
  const visit = (parent: string | null, path: string[]) => {
    for (const a of admins.filter((x) => x.parent_uuid === parent)) {
      const here = [...path, a.name]
      order.set(a.uuid, { index: order.size, path: here.join(' › ') })
      visit(a.uuid, here)
    }
  }
  visit(null, [])
  return order
})
function ownerKey(uuid: string | null): string {
  return `${String(ownerOrder.value.get(uuid ?? '')?.index ?? 9999).padStart(4, '0')}:${uuid ?? ''}`
}
function ownerPath(uuid: string | null, fallback: string): string {
  return ownerOrder.value.get(uuid ?? '')?.path ?? fallback
}

const allRows = computed<Row[]>(() =>
  (state.value?.users ?? []).map((u) => ({
    ...u,
    owner_key: ownerKey(u.owner_uuid),
    status_rank: STATUS_ORDER.indexOf(u.status),
    usage_ratio: u.usage_limit_GB > 0 ? u.current_usage_GB / u.usage_limit_GB : u.current_usage_GB > 0 ? Infinity : 0,
    last_online_ts: u.last_online ? new Date(u.last_online).getTime() : 0,
  })),
)

const MATCH: Record<FilterKey, (u: Row) => boolean> = {
  all: () => true,
  active: (u) => u.status === 'active',
  no_data: (u) => u.status === 'no_data',
  expired: (u) => u.status === 'expired',
  disabled: (u) => u.status === 'disabled',
  // Needs attention: still active, but about to stop.
  expiring: (u) => u.status === 'active' && !!u.start_date && u.remaining_days <= SOON_DAYS,
  data_low: (u) => u.status === 'active' && !unlimitedGb(u.usage_limit_GB) && u.usage_ratio >= SOON_USAGE,
  not_started: (u) => u.enable && !u.start_date,
  // Connected before, but not in the last 7 days (never connected: see "Not started").
  unseen_week: (u) => u.last_online_ts > 0 && now.value - u.last_online_ts > WEEK_MS,
}
const FILTER_ICON: Record<FilterKey, string> = {
  all: 'pi pi-users',
  ...STATUS_ICON,
  expiring: 'pi pi-clock',
  data_low: 'pi pi-chart-pie',
  not_started: 'pi pi-hourglass',
  unseen_week: 'pi pi-eye-slash',
}
const ALWAYS_SHOWN: FilterKey[] = ['all', 'active', 'expiring', 'data_low']
const filters = computed(() =>
  (['all', 'active', 'expiring', 'data_low', 'unseen_week', 'not_started', 'no_data', 'expired', 'disabled'] as FilterKey[])
    .map((key) => ({ key, icon: FILTER_ICON[key], count: allRows.value.filter(MATCH[key]).length }))
    // The everyday ones always show (even at 0); the rest only when they have users.
    .filter((f) => ALWAYS_SHOWN.includes(f.key) || f.count > 0 || filter.value === f.key),
)

const rows = computed<Row[]>(() => {
  const q = query.value.trim().toLowerCase()
  const match = MATCH[filter.value]
  return allRows.value.filter((u) => match(u) && matchesTags(u.tags, pickedTags.value) && (!q || u.name.toLowerCase().includes(q) || u.uuid.includes(q) || String(u.id).includes(q) || u.comment.toLowerCase().includes(q)))
})
// New filter / search / page size: back to the first page.
watch([filter, query, pageSize, pickedTags], () => (first.value = 0))

// Tags: a user's own dots, and the "Tag" button of the bulk bar.
const { load: loadTags } = useTags()
function setTags(uuid: string, ids: number[]) {
  if (!state.value) return
  state.value.users = state.value.users.map((u) => (u.uuid === uuid ? { ...u, tags: ids } : u))
}
const bulkTagPop = ref<InstanceType<typeof Popover> | null>(null)
const bulkTagState = computed(() => {
  const picked = new Set(selected.value.map((s) => s.uuid))
  const users = allRows.value.filter((u) => picked.has(u.uuid))
  const seen = new Map<number, number>()
  for (const u of users) for (const id of u.tags) seen.set(id, (seen.get(id) ?? 0) + 1)
  const all = [...seen].filter(([, n]) => n === users.length).map(([id]) => id)
  return { all, some: [...seen.keys()].filter((id) => !all.includes(id)) }
})
async function bulkTag(id: number, on: boolean) {
  const uuids = selected.value.map((s) => s.uuid)
  if (!uuids.length) return
  try {
    await tagsApi.bulk('user', uuids, on ? [id] : [], on ? [] : [id])
  } catch (err) {
    toast.add({ severity: 'error', summary: t('tags.saveFailed'), detail: apiErrorMessage(err), life: 5000 })
    return
  }
  await Promise.all([load(true), loadTags(true)])
}

/** Phones: the current page, grouped when asked. */
const pageRows = computed(() => {
  const list = groupByOwner.value ? [...rows.value].sort((a, b) => a.owner_key.localeCompare(b.owner_key)) : rows.value
  return paged.value ? list.slice(first.value, first.value + pageSize.value) : list
})
const cardGroups = computed(() => {
  if (!groupByOwner.value) return [{ key: '', owner: '', users: pageRows.value }]
  const map = new Map<string, Row[]>()
  for (const u of pageRows.value) map.set(u.owner_key, [...(map.get(u.owner_key) ?? []), u])
  return [...map].map(([key, users]) => ({ key, owner: ownerPath(users[0]!.owner_uuid, users[0]!.owner_name), users }))
})

function groupSize(key: string): number {
  return rows.value.filter((u) => u.owner_key === key).length
}

function usageText(u: UserRow): string {
  const used = gb(u.current_usage_GB, locale.value)
  return unlimitedGb(u.usage_limit_GB) ? `${used} / ∞ GB` : `${used} / ${gb(u.usage_limit_GB, locale.value)} GB`
}
function expireToneOf(u: UserRow): Tone {
  return u.package_days >= UNLIMITED_DAYS ? 'ok' : expireTone(u.remaining_days)
}
function expireText(u: UserRow): string {
  if (u.package_days >= UNLIMITED_DAYS) return '∞'
  if (showDates.value) return u.expire_date ? shortDate(u.expire_date, locale.value) : t('users.afterFirstShort', { n: u.package_days })
  return relativeDays(u.remaining_days, locale.value)
}
function expireTitle(u: UserRow): string {
  if (u.package_days >= UNLIMITED_DAYS) return t('users.noTimeLimit')
  const base = t('users.daysLeft', { n: u.remaining_days }, u.remaining_days)
  return u.start_date ? `${base} · ${t('users.form.expiresOn', { date: shortDate(u.expire_date, locale.value) })}` : `${base} · ${t('users.form.notStartedHint')}`
}
function seen(u: UserRow) {
  return lastSeen(u.last_online, now.value, locale.value, { online: t('users.online'), never: t('users.never') })
}

/** Hover breakdown: one popover for the table, anchored at the hovered cell. */
const nodesPop = ref()
const nodesRow = ref<Row | null>(null)
let nodesHideTimer: number | undefined

function cancelHideNodes() {
  if (nodesHideTimer) window.clearTimeout(nodesHideTimer)
  nodesHideTimer = undefined
}
function hideNodesSoon() {
  cancelHideNodes()
  nodesHideTimer = window.setTimeout(() => {
    nodesRow.value = null
    nodesPop.value?.hide()
  }, 220)
}
function showNodes(event: MouseEvent, u: Row) {
  if (!u.nodes.length) return
  cancelHideNodes()
  nodesRow.value = u
  nodesPop.value?.show(event)
}

/** Per-node usage slices for the bar; with fewer than two slices the classic gradient stays. */
function usageSegments(u: UserRow): { value: number; color: string }[] {
  const slices = u.nodes.filter((n) => n.usage > 0).map((n) => ({ value: n.usage / ONE_GIG, color: nodeColor(n.child_id) }))
  const rest = u.current_usage_GB - slices.reduce((sum, s) => sum + s.value, 0)
  if (rest > 0.001) slices.push({ value: rest, color: 'var(--p-text-muted-color)' })
  return slices.length > 1 ? slices : []
}

const nodesBreakdown = computed(() => {
  const u = nodesRow.value
  if (!u) return []
  const rows = u.nodes.map((n) => ({
    key: `n${n.child_id}`,
    name: n.name,
    color: nodeColor(n.child_id),
    seen: lastSeen(n.last_online, now.value, locale.value, { online: t('users.online'), never: t('users.never') }),
    usage: `${gb(n.usage / ONE_GIG, locale.value)} GB`,
  }))
  const rest = u.current_usage_GB - u.nodes.reduce((sum, n) => sum + n.usage / ONE_GIG, 0)
  if (rest > 0.001) {
    rows.push({ key: 'rest', name: t('users.nodes.other'), color: 'var(--p-text-muted-color)', seen: { text: '—', tone: 'muted' as Tone, online: false }, usage: `${gb(rest, locale.value)} GB` })
  }
  return rows
})

function rowClass(u: Row) {
  return u.status === 'active' ? '' : `u-row--${u.status}`
}
function onSort(e: DataTableSortEvent) {
  sortField.value = (e.sortField as string) || undefined
  sortOrder.value = e.sortOrder ?? undefined
}

function isSelected(u: Row): boolean {
  return selected.value.some((s) => s.uuid === u.uuid)
}

/** Every user the filter / search shows (not only this page). */
const allPicked = computed(() => rows.value.length > 0 && rows.value.every((u) => isSelected(u)))
const somePicked = computed(() => rows.value.some((u) => isSelected(u)))

function toggleAll(on: boolean) {
  const shown = new Set(rows.value.map((u) => u.uuid))
  const others = selected.value.filter((s) => !shown.has(s.uuid))
  selected.value = on ? [...others, ...rows.value] : others
}

function toggleSelect(u: Row, on: boolean) {
  selected.value = on ? [...selected.value, u] : selected.value.filter((s) => s.uuid !== u.uuid)
}

async function load(silent = false) {
  if (!silent) loading.value = true
  loadError.value = null
  try {
    state.value = await usersApi.list()
    const keep = new Set(state.value.users.map((u) => u.uuid))
    selected.value = selected.value.filter((s) => keep.has(s.uuid))
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
  refreshing.value = false
}

/** Replace one row with the server's version after a change. */
function replaceRow(user: UserDetail) {
  if (!state.value) return
  const row: UserRow = { ...user, additional_configs: user.additional_configs.length }
  const i = state.value.users.findIndex((u) => u.uuid === user.uuid)
  if (i >= 0) state.value.users[i] = row
  else state.value.users.unshift(row)
}

async function patch(u: UserRow, payload: UserPayload, done?: string) {
  try {
    replaceRow(await usersApi.update(u.uuid, payload))
    if (done) toast.add({ severity: 'success', summary: done, life: 2500 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
    await load(true)
  }
}

/** Inline edits: each editor may change more than its own field (name + note, limit + reset period). */
const INLINE_FIELDS = ['name', 'comment', 'usage_limit_GB', 'mode', 'package_days'] as const
function onCellEdit(e: DataTableCellEditCompleteEvent) {
  const { data, newData } = e as DataTableCellEditCompleteEvent & { newData: Row }
  const payload: Record<string, unknown> = {}
  for (const key of INLINE_FIELDS) {
    const value = (newData as Record<string, unknown>)[key]
    if (value !== (data as Record<string, unknown>)[key]) payload[key] = value
  }
  if (!Object.keys(payload).length || ('name' in payload && !String(payload.name ?? '').trim())) return
  void patch(data as Row, payload as UserPayload)
}

function quick(u: UserRow, action: 'reset_usage' | 'reset_days') {
  void patch(u, { [action]: true }, t(`users.done.${action}`, { name: u.name }))
}

function openAdd() {
  editingUser.value = null
  formVisible.value = true
}
function openEdit(u: UserRow) {
  editingUser.value = u
  formVisible.value = true
}
function openLink(u: UserRow) {
  linkUser.value = u
  linkVisible.value = true
}
function onSaved(user: UserDetail, created: boolean) {
  replaceRow(user)
  toast.add({ severity: 'success', summary: created ? t('users.added', { name: user.name }) : t('users.saved', { name: user.name }), life: 3000 })
  if (created) {
    linkUser.value = { ...user, additional_configs: user.additional_configs.length }
    linkVisible.value = true
  }
}

function openMenu(e: Event, u: UserRow) {
  menuUser.value = u
  rowMenu.value?.toggle(e)
}
const menuItems = computed<MenuItem[]>(() => {
  const u = menuUser.value
  if (!u) return []
  return [
    { label: t('common.edit'), icon: 'pi pi-pencil', command: () => openEdit(u) },
    { label: t('users.showLink'), icon: 'pi pi-qrcode', command: () => openLink(u) },
    { separator: true },
    { label: u.enable ? t('users.bulk.disable') : t('users.bulk.enable'), icon: u.enable ? 'pi pi-ban' : 'pi pi-check-circle', command: () => patch(u, { enable: !u.enable }) },
    { label: t('users.form.resetUsage'), icon: 'pi pi-refresh', disabled: !u.current_usage_GB, command: () => quick(u, 'reset_usage') },
    { label: t('users.form.resetDays'), icon: 'pi pi-replay', disabled: !u.start_date, command: () => quick(u, 'reset_days') },
    { separator: true },
    { label: t('common.delete'), icon: 'pi pi-trash', class: 'u-menu--danger', command: () => confirmDelete(u) },
  ]
})

function confirmDelete(u: UserRow) {
  dangerConfirm({
    header: t('users.deleteTitle', { name: u.name }),
    message: t('users.deleteMessage'),
    acceptLabel: t('common.delete'),
    accept: async () => {
      try {
        await usersApi.remove(u.uuid)
        if (state.value) state.value.users = state.value.users.filter((x) => x.uuid !== u.uuid)
        toast.add({ severity: 'success', summary: t('users.deleted', { name: u.name }), life: 3000 })
      } catch (err) {
        toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

// "Add limits": data and days added to every selected user (10 GB and 7 days to start with).
const limitsVisible = ref(false)
const limitsGb = ref<number | null>(10)
const limitsDays = ref<number | null>(7)
const limitsBusy = ref(false)
function openAddLimits() {
  limitsGb.value = 10
  limitsDays.value = 7
  limitsVisible.value = true
}
async function applyLimits() {
  if ((!limitsGb.value && !limitsDays.value) || limitsBusy.value) return
  limitsBusy.value = true
  try {
    const count = await usersApi.bulk('add_limits', selected.value.map((u) => u.uuid), limitsDays.value ?? 0, limitsGb.value ?? 0)
    toast.add({ severity: 'success', summary: t('users.bulkDone.add_limits', { n: count }, count), life: 3000 })
    limitsVisible.value = false
    await load(true)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    limitsBusy.value = false
  }
}

function bulk(action: BulkAction) {
  const uuids = selected.value.map((u) => u.uuid)
  const n = uuids.length
  const run = async (days?: number) => {
    try {
      const count = await usersApi.bulk(action, uuids, days)
      toast.add({ severity: 'success', summary: t(`users.bulkDone.${action}`, { n: count }, count), life: 3000 })
      if (action === 'delete') selected.value = []
      await load(true)
    } catch (err) {
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
    }
  }
  if (action === 'add_days') return void run(7)
  if (action === 'delete' || action === 'reset_usage' || action === 'reset_days' || action === 'disable') {
    dangerConfirm({
      header: t(`users.bulkConfirm.${action}`, { n }, n),
      message: t(`users.bulkConfirmText.${action}`),
      acceptLabel: t(`users.bulk.${action}`),
      accept: () => run(),
    })
    return
  }
  void run()
}

onMounted(async () => {
  narrowQuery.addEventListener('change', onNarrow)
  await load()
  timer = window.setInterval(() => {
    now.value = Date.now()
    if (!document.hidden && !formVisible.value && !inlineEdit.value) void load(true)
  }, 60_000)
})
onBeforeUnmount(() => {
  narrowQuery.removeEventListener('change', onNarrow)
  window.clearInterval(timer)
})
</script>

<style scoped>
.users-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0 1rem;
}
.users-head__add {
  margin-bottom: 1.25rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

/* Filter chips */
.users-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}
.users-tagfilter {
  flex: none;
  min-width: 8.5rem;
  border-radius: 12px;
}
.users-filter {
  --tone: var(--p-primary-color);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    transform 0.15s ease;
}
.users-filter:hover {
  transform: translateY(-1px);
  border-color: var(--tone);
}
.users-filter i {
  color: var(--tone);
}
.users-filter b {
  color: var(--p-text-color);
}
.users-filter--on {
  border-color: var(--tone);
  background: color-mix(in srgb, var(--tone) 11%, var(--p-content-background));
  color: var(--p-text-color);
  box-shadow: inset 0 0 0 1px var(--tone);
}
.users-filter--active {
  --tone: var(--p-green-500, #22c55e);
}
.users-filter--expiring,
.users-filter--data_low {
  --tone: var(--p-amber-500, #f59e0b);
}
.users-filter--unseen_week {
  --tone: var(--p-violet-500, #8b5cf6);
}
.users-filter--not_started {
  --tone: var(--p-sky-500, #0ea5e9);
}
.users-filter--no_data {
  --tone: var(--p-orange-500, #f97316);
}
.users-filter--expired {
  --tone: var(--p-red-500, #ef4444);
}
.users-filter--disabled {
  --tone: var(--p-surface-500, #64748b);
}

/* Toolbar */
.users-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem 1rem;
  padding: 0.55rem 0.75rem;
  margin-bottom: 0.85rem;
  border-radius: 14px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.users-bar__find {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1 1 18rem;
  max-width: 29rem;
  min-width: 0;
}
.users-bar__search {
  flex: 1;
  min-width: 0;
}
.users-bar__refresh {
  flex-shrink: 0;
}
.users-bar__clear {
  cursor: pointer;
}
.users-bar__options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 1rem;
  margin-inline-start: auto;
}
.users-bar__page {
  min-width: 6rem;
}
.users-check {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.86rem;
  cursor: pointer;
  user-select: none;
}

/* Bulk actions */
.users-bulk {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
  padding: 0.6rem 0.9rem;
  margin-bottom: 0.85rem;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 40%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 7%, var(--p-content-background));
}
.users-bulk__count {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 600;
  color: var(--p-primary-color);
}
.users-bulk__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.users-card {
  padding: 0.35rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}
.users-table :deep(.p-datatable-thead > tr > th) {
  font-size: 0.76rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}
.users-table :deep(.p-datatable-tbody > tr > td) {
  padding-block: 0.5rem;
  vertical-align: middle;
}
.users-table :deep(tr.u-row--disabled > td:not(:first-child)) {
  opacity: 0.6;
}
.users-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
}
.users-group i {
  color: var(--p-primary-color);
}
.users-group--card {
  margin: 0.5rem 0.2rem 0.1rem;
}
.users-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  padding: 2rem 1rem;
  color: var(--p-text-muted-color);
}
.users-empty > i {
  font-size: 1.6rem;
  color: var(--p-primary-color);
}

/* Id cell: small, quiet, aligned digits */
.u-id {
  display: inline-block;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--p-text-muted-color);
}

/* Status: icon only */
.u-state {
  --tone: var(--p-green-500, #22c55e);
  display: inline-grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  flex-shrink: 0;
  border-radius: 50%;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 14%, transparent);
}
.u-state i {
  font-size: 0.85rem;
}
.u-state--no_data {
  --tone: var(--p-orange-500, #f97316);
}
.u-state--expired {
  --tone: var(--p-red-500, #ef4444);
}
.u-state--disabled {
  --tone: var(--p-surface-500, #64748b);
}

/* Name cell: name + link button, note below */
.al-hint,
.al-note {
  color: var(--p-text-muted-color);
}
.al-hint {
  margin: 0 0 1rem;
  font-size: 0.85rem;
}
.al-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.al-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.u-who {
  /* The note sits beside the name when there is room, and wraps under it when there is not */
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  column-gap: 0.6rem;
  row-gap: 0.1rem;
  min-width: 0;
  max-width: 32rem;
}
.u-who__line {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  min-width: 0;
}
.u-who__name {
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-align: start;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.u-who__name:hover {
  color: var(--p-primary-color);
}
.u-who__link {
  flex-shrink: 0;
  width: 1.8rem !important;
  height: 1.8rem !important;
  margin-inline-end: 0.2rem;
}
.u-who__note {
  flex: 1 1 6rem;
  min-width: 0;
}
.u-who__note,
.u-who__uuid {
  max-width: 100%;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.u-who__uuid {
  /* its own line, aligned under the name past the QR button */
  flex-basis: 100%;
  padding-inline-start: 2rem;
}
.u-who__uuid {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
:deep(.u-mark) {
  padding: 0 0.1rem;
  border-radius: 3px;
  color: inherit;
  background: color-mix(in srgb, var(--p-amber-400, #fbbf24) 45%, transparent);
}

.u-tone--ok {
  --tone: var(--p-green-600, #16a34a);
}
.u-tone--warn {
  --tone: var(--p-amber-600, #d97706);
}
.u-tone--danger {
  --tone: var(--p-red-500, #ef4444);
}
.u-tone--muted {
  --tone: var(--p-text-muted-color);
}
.u-usage {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 11rem;
  max-width: 100%;
}
.u-reset {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 0.3rem;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.u-reset i {
  font-size: 0.6rem;
}
.u-edit-usage {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.u-edit-mode {
  min-width: 7.5rem;
}
.u-expire-head {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.u-date-toggle {
  display: grid;
  place-items: center;
  width: 1.4rem;
  height: 1.4rem;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.u-date-toggle i {
  font-size: 0.72rem;
}
.u-date-toggle:hover,
.u-date-toggle--on {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.u-expire {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.12rem 0.5rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 11%, transparent);
}
.u-expire i {
  font-size: 0.7rem;
}
.u-expire--btn {
  border: 0;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.u-online {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  white-space: nowrap;
  color: var(--tone);
}
.u-online i {
  font-size: 0.7rem;
}
.u-online--hover {
  cursor: help;
}
.u-dot {
  position: relative;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--p-green-500, #22c55e);
}
.u-dot::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: u-ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
}
.u-actions {
  display: flex;
}

/* Hover breakdown popover (last status / usage cells) */
.un {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 14rem;
}
.un__title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.un__title i {
  color: var(--p-primary-color);
}
.un__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}
.un__dot {
  flex: none;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
}
.un__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.un__seen {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex: none;
  white-space: nowrap;
  color: var(--tone);
}
.un__usage {
  flex: none;
  min-width: 4.5rem;
  text-align: end;
  font-variant-numeric: tabular-nums;
  color: var(--p-text-muted-color);
}

/* Cards (phones) */
.u-cards {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.u-selectall {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
}
.u-card {
  --tone: var(--p-green-500, #22c55e);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.6rem 0.4rem 0.65rem 0.65rem;
  border-radius: 16px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--tone) 7%, transparent), transparent 45%),
    var(--p-content-background);
  border: 1px solid color-mix(in srgb, var(--tone) 22%, var(--p-content-border-color));
  box-shadow: 0 6px 18px -14px color-mix(in srgb, var(--tone) 60%, rgba(15, 23, 42, 0.5));
  transition:
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}
.u-card--no_data {
  --tone: var(--p-orange-500, #f97316);
}
.u-card--expired {
  --tone: var(--p-red-500, #ef4444);
}
.u-card--disabled {
  --tone: var(--p-surface-400, #94a3b8);
}
.u-card--picked {
  border-color: var(--p-primary-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--p-primary-color) 30%, transparent);
}
.u-card__head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}
.u-card__check :deep(.p-checkbox-box) {
  width: 1.1rem;
  height: 1.1rem;
}
.u-card__qr {
  position: relative;
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.05rem;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 14%, transparent);
  cursor: pointer;
}
.u-card__qr:active {
  transform: scale(0.95);
}
.u-card__badge {
  position: absolute;
  inset-inline-end: -0.3rem;
  bottom: -0.3rem;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--tone);
  box-shadow: 0 0 0 2px var(--p-content-background);
}
.u-card__badge i {
  font-size: 0.55rem;
}
.u-card__title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.u-card__name {
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.u-card__sub {
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.u-card__body {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-inline-end: 0.25rem;
  padding: 0.5rem 0.55rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.u-card__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.u-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.12rem 0.5rem;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-size: 0.74rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--tone, var(--p-text-muted-color));
  background: var(--p-content-background);
}
.u-pill i {
  font-size: 0.65rem;
}
button.u-pill {
  cursor: pointer;
}
.u-pill--reset {
  color: var(--p-primary-color);
}

.users-fade-enter-active,
.users-fade-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.users-fade-enter-from,
.users-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@keyframes u-ping {
  75%,
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
@media (max-width: 640px) {
  .users-head__add {
    width: 100%;
  }
  .users-filters {
    flex-wrap: nowrap;
    overflow-x: auto;
    /* room inside the scroll area so nothing of a chip is cut off */
    margin-inline: -0.25rem;
    padding: 0.2rem 0.25rem 0.35rem;
    scrollbar-width: none;
  }
  .users-filters::-webkit-scrollbar {
    display: none;
  }
  .users-filter {
    flex-shrink: 0;
  }
  .users-filter:hover {
    transform: none;
  }
  .users-bar__find {
    max-width: none;
    flex-basis: 100%;
  }
  .users-bar__options {
    margin-inline-start: 0;
    width: 100%;
    justify-content: space-between;
  }
}
@media (prefers-reduced-motion: reduce) {
  .u-dot::after {
    animation: none;
  }
  .users-filter:hover {
    transform: none;
  }
}
</style>

<style>
.u-menu--danger .p-menu-item-icon,
.u-menu--danger .p-menu-item-label {
  color: var(--p-red-500, #ef4444);
}
</style>
