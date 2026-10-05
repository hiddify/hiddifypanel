<template>
  <div class="ob-page">
    <div class="ob-head">
      <PageHeader :title="t('outbounds.title')" :subtitle="t('outbounds.subtitle')" />
      <Button
        v-if="state?.addable_modes.length"
        icon="pi pi-plus"
        :label="t('outbounds.add')"
        class="ob-head__add"
        aria-haspopup="true"
        @click="(e) => addMenu?.toggle(e)"
      />
      <Menu ref="addMenu" :model="addItems" popup />
    </div>

    <ApplyNotice v-model="pendingApply" />

    <div v-if="loading" class="ob-list">
      <Skeleton v-for="i in 3" :key="i" height="5.5rem" border-radius="16px" />
    </div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <p class="ob-howto"><i class="pi pi-info-circle" />{{ t('outbounds.howto') }}</p>

      <TransitionGroup name="ob-row" tag="ol" class="ob-list" :class="{ 'ob-list--dragging': dragId !== null }">
        <li
          v-for="(o, i) in rows"
          :key="o.id"
          class="ob-row"
          :class="[
            `ob-tone--${o.mode}`,
            {
              'ob-row--default': o.is_default,
              'ob-row--off': !o.enabled,
              'ob-row--idle': o.enabled && !o.active,
              'ob-row--new': o.id === justChanged,
              'ob-row--drag': o.id === dragId,
              'ob-row--over': o.id === overId && o.id !== dragId,
            },
          ]"
          @dragover.prevent="onDragOver(o)"
          @drop.prevent="onDrop(o)"
        >
          <!-- Order: drag handle (mouse) and number -->
          <div class="ob-row__order">
            <span
              class="ob-row__handle"
              draggable="true"
              :aria-label="t('outbounds.drag')"
              v-tooltip.top="t('outbounds.drag')"
              @dragstart="onDragStart($event, o)"
              @dragend="onDragEnd"
            ><i class="pi pi-bars" /></span>
            <span class="ob-row__n">{{ i + 1 }}</span>
          </div>

          <span class="ob-row__icon"><i :class="MODE_ICON[o.mode]" /></span>

          <div class="ob-row__body">
            <div class="ob-row__name">
              <span class="ob-row__name-text" :title="o.name">{{ o.name }}</span>
              <span class="ob-badge">{{ t(`outbounds.mode.${o.mode}`) }}</span>
              <span v-if="o.is_default" class="ob-badge ob-badge--default" v-tooltip.top="t('outbounds.defaultHint')"><i class="pi pi-crown" />{{ t('outbounds.default') }}</span>
              <span v-else-if="!o.enabled" class="ob-badge ob-badge--off">{{ t('outbounds.off') }}</span>
              <span v-else-if="!o.active" class="ob-badge ob-badge--off" v-tooltip.top="t('outbounds.idleHint')"><i class="pi pi-minus-circle" />{{ t('outbounds.idle') }}</span>
            </div>

            <div class="ob-row__what">
              <template v-if="o.is_default">
                <span class="ob-row__everything"><i class="pi pi-arrow-down-right" />{{ t('outbounds.everythingElse') }}</span>
              </template>
              <template v-else>
                <span v-if="o.domestic" class="ob-count ob-count--domestic"><i class="pi pi-home" />{{ t('outbounds.domesticChip', { region: t(`outbounds.region.${state.region || 'other'}`) }) }}</span>
                <span v-for="c in counts(o)" :key="c.key" class="ob-count" :class="{ 'ob-count--zero': !c.n }"><b>{{ c.n }}</b>{{ t(`outbounds.count.${c.key}`, c.n) }}</span>
              </template>
              <span v-if="o.mode === 'socks' || o.mode === 'tor' || o.mode === 'psiphon'" class="ob-row__endpoint" dir="ltr">{{ o.host }}:{{ o.port }}</span>
              <span v-else-if="o.tag" class="ob-row__endpoint" dir="ltr" v-tooltip.top="t('outbounds.dialog.configBridge', { tag: o.tag, port: o.bridge_port })">{{ o.tag }}</span>
            </div>
            <p v-if="!o.is_default && (o.sites.length || o.geosites.length)" class="ob-row__sample" dir="ltr" :title="sample(o, 40)">{{ sample(o, 6) }}</p>

            <div v-if="o.is_builtin && !o.is_default" class="ob-row__builtin" :class="{ 'ob-row__builtin--edited': o.lists_override }">
              <i class="pi" :class="o.lists_override ? 'pi-pencil' : 'pi-sync'" />
              <span>{{ o.lists_override ? t('outbounds.edited') : t('outbounds.followsDefaults') }}</span>
            </div>
          </div>

          <div class="ob-row__side">
            <ToggleSwitch
              :model-value="o.enabled"
              :disabled="busy"
              :aria-label="t('outbounds.enabled')"
              v-tooltip.left="o.enabled ? t('outbounds.disable') : t('outbounds.enable')"
              @update:model-value="(v: boolean) => toggleEnabled(o, v)"
            />
            <div class="ob-row__actions">
              <Button icon="pi pi-arrow-up" text rounded size="small" severity="secondary" :disabled="busy || i === 0" :aria-label="t('outbounds.moveUp')" v-tooltip.top="t('outbounds.moveUp')" @click="move(o, -1)" />
              <Button icon="pi pi-arrow-down" text rounded size="small" severity="secondary" :disabled="busy || i === rows.length - 1" :aria-label="t('outbounds.moveDown')" v-tooltip.top="t('outbounds.moveDown')" @click="move(o, 1)" />
              <Button icon="pi pi-pencil" text rounded size="small" :aria-label="t('common.edit')" v-tooltip.top="t('common.edit')" @click="openEdit(o)" />
              <Button icon="pi pi-ellipsis-v" text rounded size="small" severity="secondary" :aria-label="t('outbounds.more')" aria-haspopup="true" @click="openMenu($event, o)" />
            </div>
          </div>
        </li>
      </TransitionGroup>
    </template>

    <Menu ref="rowMenu" :model="rowItems" popup />
    <OutboundDialog v-model:visible="dialogVisible" :outbound="editing" :mode="addMode" :state="state" @saved="onSaved" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import ToggleSwitch from 'primevue/toggleswitch'
import PageHeader from '@/shared/components/PageHeader.vue'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import OutboundDialog from '@/features/outbounds/components/OutboundDialog.vue'
import { MODE_ICON, outboundsApi, type Outbound, type OutboundMode, type OutboundsState } from '@/features/outbounds/api'

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()
const dangerConfirm = useDangerConfirm()

const state = ref<OutboundsState | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const pendingApply = ref<RestartMode>('nothing')
const busy = ref(false)
const justChanged = ref<number | null>(null)

const dialogVisible = ref(false)
const editing = ref<Outbound | null>(null)
const addMode = ref<OutboundMode>('socks')
const addMenu = ref<InstanceType<typeof Menu> | null>(null)
const rowMenu = ref<InstanceType<typeof Menu> | null>(null)
const menuRow = ref<Outbound | null>(null)

const dragId = ref<number | null>(null)
const overId = ref<number | null>(null)

/** The server's order: first checked first; the last enabled one is the default. */
const rows = computed(() => state.value?.outbounds ?? [])

const addItems = computed<MenuItem[]>(() =>
  (state.value?.addable_modes ?? []).map((mode) => ({ label: t(`outbounds.mode.${mode}`), icon: MODE_ICON[mode], command: () => openAdd(mode) })),
)

const rowItems = computed<MenuItem[]>(() => {
  const o = menuRow.value
  if (!o) return []
  return [
    { label: t('common.edit'), icon: 'pi pi-pencil', command: () => openEdit(o) },
    { label: t('outbounds.makeDefault'), icon: 'pi pi-crown', disabled: o.is_default || o.mode === 'block', command: () => makeDefault(o) },
    { label: t('outbounds.reset'), icon: 'pi pi-sync', visible: o.is_builtin && o.lists_override, command: () => confirmReset(o) },
    { separator: true, visible: !o.is_builtin },
    { label: t('common.delete'), icon: 'pi pi-trash', class: 'ob-menu--danger', visible: !o.is_builtin, command: () => confirmDelete(o) },
  ]
})

function counts(o: Outbound) {
  return (['sites', 'geosites', 'rule_sets'] as const).map((key) => ({ key, n: o[key].length }))
}

function sample(o: Outbound, max: number): string {
  const all = [...o.geosites, ...o.sites]
  return all.slice(0, max).join(', ') + (all.length > max ? ` +${all.length - max}` : '')
}

function apply(next: OutboundsState) {
  state.value = next
  if (next.restart_mode) pendingApply.value = strongerRestartMode(pendingApply.value, next.restart_mode)
}

function flash(id: number | null | undefined) {
  if (!id) return
  justChanged.value = id
  window.setTimeout(() => (justChanged.value = null), 2200)
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    state.value = await outboundsApi.list()
  } catch (err) {
    loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

/** Runs a change; on refusal (e.g. "Block can not be last") the server's state stays as it was. */
async function run(action: () => Promise<OutboundsState>, flashId?: number, done?: string) {
  busy.value = true
  try {
    apply(await action())
    flash(flashId)
    if (done) toast.add({ severity: 'success', summary: done, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'warn', summary: t('outbounds.notChanged'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    busy.value = false
  }
}

function reorder(ids: number[], flashId?: number) {
  const before = state.value
  // Show the new order right away; the server answer replaces it (or the old one comes back on refusal).
  if (before) {
    const byId = new Map(before.outbounds.map((o) => [o.id, o]))
    state.value = { ...before, outbounds: ids.map((id) => byId.get(id)!).filter(Boolean) }
  }
  return run(async () => {
    try {
      return await outboundsApi.reorder(ids)
    } catch (err) {
      if (before) state.value = before
      throw err
    }
  }, flashId)
}

function move(o: Outbound, delta: number) {
  const ids = rows.value.map((r) => r.id)
  const from = ids.indexOf(o.id)
  const to = from + delta
  if (to < 0 || to >= ids.length) return
  ids.splice(from, 1)
  ids.splice(to, 0, o.id)
  void reorder(ids, o.id)
}

function onDragStart(e: DragEvent, o: Outbound) {
  dragId.value = o.id
  e.dataTransfer?.setData('text/plain', String(o.id))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onDragOver(o: Outbound) {
  if (dragId.value !== null) overId.value = o.id
}
function onDragEnd() {
  dragId.value = null
  overId.value = null
}
function onDrop(target: Outbound) {
  const id = dragId.value
  onDragEnd()
  if (id === null || id === target.id) return
  const ids = rows.value.map((r) => r.id).filter((x) => x !== id)
  ids.splice(ids.indexOf(target.id) + (rows.value.findIndex((r) => r.id === id) < rows.value.findIndex((r) => r.id === target.id) ? 1 : 0), 0, id)
  void reorder(ids, id)
}

function openMenu(e: Event, o: Outbound) {
  menuRow.value = o
  rowMenu.value?.toggle(e)
}

function openAdd(mode: OutboundMode) {
  editing.value = null
  addMode.value = mode
  dialogVisible.value = true
}

function openEdit(o: Outbound) {
  editing.value = o
  addMode.value = o.mode
  dialogVisible.value = true
}

function onSaved(next: OutboundsState, name: string) {
  apply(next)
  flash(editing.value?.id ?? next.created_id)
  toast.add({ severity: 'success', summary: t('outbounds.saved', { name }), life: 3000 })
}

function toggleEnabled(o: Outbound, enabled: boolean) {
  void run(() => outboundsApi.update(o.id, { enabled }), o.id)
}

function makeDefault(o: Outbound) {
  void run(() => outboundsApi.makeDefault(o.id), o.id, t('outbounds.nowDefault', { name: o.name }))
}

function confirmReset(o: Outbound) {
  confirm.require({
    header: t('outbounds.resetTitle', { name: o.name }),
    message: t('outbounds.resetMessage'),
    icon: 'pi pi-sync',
    defaultFocus: 'reject',
    rejectProps: { label: t('common.cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('outbounds.reset') },
    accept: () => run(() => outboundsApi.reset(o.id), o.id, t('outbounds.resetDone', { name: o.name })),
  })
}

function confirmDelete(o: Outbound) {
  dangerConfirm({
    header: t('outbounds.deleteTitle', { name: o.name }),
    message: o.is_default ? t('outbounds.deleteMessageDefault') : t('outbounds.deleteMessage'),
    acceptLabel: t('common.delete'),
    accept: () => run(() => outboundsApi.remove(o.id), undefined, t('outbounds.deleted', { name: o.name })),
  })
}

onMounted(load)
</script>

<style scoped>
.ob-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0 1rem;
}
.ob-head__add {
  margin-bottom: 1.25rem;
}
.ob-howto {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 0.88rem;
  color: var(--p-text-muted-color);
}
.ob-howto i {
  margin-top: 0.15rem;
  color: var(--p-primary-color);
}

/* Ordered list */
.ob-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ob-row {
  position: relative;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.85rem;
  padding: 0.85rem 1rem 0.85rem 0.6rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 4px solid var(--ob-color);
  animation: ob-in 0.35s ease both;
  transition:
    opacity 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.15s ease,
    border-color 0.2s ease;
}
.ob-row--default {
  border-color: color-mix(in srgb, var(--ob-color) 55%, var(--p-content-border-color));
  border-inline-start-color: var(--ob-color);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--ob-color) 25%, transparent);
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--ob-color) 7%, transparent), transparent 55%),
    var(--p-content-background);
}
:global([dir='rtl']) .ob-row--default {
  background:
    linear-gradient(-90deg, color-mix(in srgb, var(--ob-color) 7%, transparent), transparent 55%),
    var(--p-content-background);
}
.ob-row--off,
.ob-row--idle {
  border-inline-start-color: var(--p-content-border-color);
}
.ob-row--off > :not(.ob-row__side),
.ob-row--idle > :not(.ob-row__side) {
  opacity: 0.5;
}
.ob-row--new {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.ob-row--drag {
  opacity: 0.45;
}
.ob-row--over {
  transform: translateY(2px);
  box-shadow: 0 -3px 0 0 var(--p-primary-color);
}

.ob-row__order {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}
.ob-row__handle {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 2rem;
  border-radius: 8px;
  color: var(--p-text-muted-color);
  cursor: grab;
}
.ob-row__handle:hover {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.ob-row__handle:active {
  cursor: grabbing;
}
.ob-row__n {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.74rem;
  font-weight: 700;
  color: #fff;
  background: var(--ob-color);
}
.ob-row--off .ob-row__n,
.ob-row--idle .ob-row__n {
  background: var(--p-text-muted-color);
}
.ob-row__icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.05rem;
  color: var(--ob-color);
  background: color-mix(in srgb, var(--ob-color) 14%, transparent);
}
.ob-row__body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.ob-row__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  min-width: 0;
}
.ob-row__name-text {
  font-size: 1.02rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.ob-row__what {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}
.ob-row__everything {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ob-color);
}
.ob-row__endpoint {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.ob-row__sample {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.73rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.ob-row__builtin {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--p-green-600, #16a34a);
}
.ob-row__builtin--edited {
  color: var(--p-amber-700, #b45309);
}
.ob-row__side {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.ob-row__actions {
  display: flex;
  align-items: center;
}

.ob-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--ob-color);
  background: color-mix(in srgb, var(--ob-color) 12%, transparent);
}
.ob-badge--default {
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 16%, transparent);
}
.ob-badge--off {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.ob-count {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3rem;
  padding: 0.1rem 0.5rem;
  border-radius: 8px;
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.ob-count b {
  color: var(--p-text-color);
}
.ob-count--zero {
  opacity: 0.55;
}
.ob-count--domestic {
  align-items: center;
  color: var(--ob-color);
  background: color-mix(in srgb, var(--ob-color) 10%, transparent);
  font-weight: 600;
}

@keyframes ob-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.ob-row-move {
  transition: transform 0.3s ease;
}
.ob-row-leave-active {
  transition: opacity 0.2s ease;
}
.ob-row-leave-to {
  opacity: 0;
}

/* Phones: number + icon + body on top, controls below */
@media (max-width: 640px) {
  .ob-head__add {
    width: 100%;
  }
  .ob-row {
    grid-template-columns: auto auto minmax(0, 1fr);
    gap: 0.6rem 0.7rem;
    padding: 0.75rem 0.75rem 0.6rem 0.4rem;
    border-radius: 14px;
  }
  .ob-row__handle {
    display: none; /* touch: use the arrows */
  }
  .ob-row__side {
    grid-column: 1 / -1;
    justify-content: space-between;
    padding-top: 0.5rem;
    border-top: 1px solid var(--p-content-border-color);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ob-row {
    animation: none;
  }
  .ob-row-move {
    transition: none;
  }
}
</style>

<style>
.ob-menu--danger .p-menu-item-icon,
.ob-menu--danger .p-menu-item-label {
  color: var(--p-red-500, #ef4444);
}
</style>
