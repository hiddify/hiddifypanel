<template>
  <div class="protocols-page" :class="{ 'protocols-page--dirty': dirtyCount > 0 }">
    <PageHeader :title="t('protocols.title')" :subtitle="t('protocols.subtitle')" />

    <!-- Summary + filters -->
    <section class="proto-summary">
      <div class="proto-summary__stat">
        <div class="proto-ring" :style="{ '--proto-progress': `${enabledRatio * 360}deg` }">
          <span class="proto-ring__value">{{ enabledCount }}</span>
        </div>
        <div class="min-w-0">
          <div class="font-semibold text-lg">{{ t('protocols.enabledOf', { on: enabledCount, total: items.length }) }}</div>
          <div class="text-muted-color text-sm">{{ t('protocols.summaryHint') }}</div>
        </div>
      </div>
      <div class="proto-summary__filters">
        <IconField class="proto-search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="search" :placeholder="t('protocols.search')" class="w-full" />
        </IconField>
        <SelectButton
          v-model="filter"
          :options="filterOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          class="proto-filter"
        />
      </div>
    </section>

    <!-- Apply notice after a save that needs it -->
    <ApplyNotice v-model="pendingApply" />

    <!-- Loading -->
    <div v-if="loading" class="proto-grid">
      <Skeleton v-for="i in 9" :key="i" height="6.5rem" border-radius="14px" />
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <!-- Groups -->
    <template v-else>
      <TransitionGroup name="proto-group" tag="div" class="flex flex-col gap-5">
        <section v-for="group in visibleGroups" :key="group.id" class="proto-group">
          <header class="proto-group__header">
            <span class="proto-group__icon" :style="{ '--proto-accent': group.accent }"><i :class="group.icon" /></span>
            <div class="min-w-0 flex-1">
              <h3 class="proto-group__title">{{ group.title }}</h3>
              <p class="proto-group__hint">{{ group.hint }}</p>
            </div>
            <Tag :value="`${group.on}/${group.total}`" :severity="group.on ? 'success' : 'secondary'" rounded />
            <div class="proto-group__bulk">
              <Button size="small" text :label="t('protocols.enableAll')" :disabled="group.on === group.total" @click="setGroup(group, true)" />
              <Button size="small" text severity="secondary" :label="t('protocols.disableAll')" :disabled="group.on === 0" @click="setGroup(group, false)" />
            </div>
          </header>

          <TransitionGroup name="proto-tile" tag="div" class="proto-grid">
            <article
              v-for="(item, index) in group.items"
              :key="item.key"
              class="proto-tile"
              :class="{ 'proto-tile--on': draft[item.key], 'proto-tile--changed': isChanged(item) }"
              :style="{ '--proto-delay': `${Math.min(index, 12) * 35}ms`, '--proto-accent': group.accent }"
              role="switch"
              :aria-checked="draft[item.key]"
              tabindex="0"
              @click="toggle(item)"
              @keydown.enter.prevent="toggle(item)"
              @keydown.space.prevent="toggle(item)"
            >
              <div class="proto-tile__top">
                <span class="proto-tile__name">{{ displayLabel(item.label) }}</span>
                <ToggleSwitch :model-value="draft[item.key]" :input-id="`proto-${item.key}`" @click.stop @update:model-value="draft[item.key] = $event" />
              </div>
              <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
              <p v-if="item.description" class="proto-tile__desc" @click="onDescriptionClick" v-html="item.description" />
              <div class="proto-tile__meta">
                <RouterLink
                  :to="{ name: 'settings', query: { category: item.category } }"
                  class="proto-chip proto-chip--link"
                  :title="t('protocols.relatedSettings')"
                  @click.stop
                >
                  <i class="pi pi-cog" />{{ t('protocols.relatedSettings') }}
                </RouterLink>
                <span v-if="item.apply_mode === 'reinstall'" class="proto-chip proto-chip--warn"><i class="pi pi-refresh" />{{ t('protocols.reinstallChip') }}</span>
                <span v-else-if="item.apply_mode === 'nothing'" class="proto-chip"><i class="pi pi-bolt" />{{ t('protocols.instantChip') }}</span>
                <Transition name="proto-fade">
                  <span v-if="isChanged(item)" class="proto-chip proto-chip--changed"><i class="pi pi-pencil" />{{ t('protocols.changed') }}</span>
                </Transition>
              </div>
            </article>
          </TransitionGroup>
        </section>
      </TransitionGroup>

      <div v-if="!visibleGroups.length" class="proto-empty">
        <i class="pi pi-filter-slash" />
        <span>{{ t('protocols.noMatch') }}</span>
      </div>
    </template>

    <StickySaveBar :count="dirtyCount" :saving="saving" @save="save" @discard="discard" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import PageHeader from '@/shared/components/PageHeader.vue'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import StickySaveBar from '@/shared/components/StickySaveBar.vue'
import { apiErrorMessage } from '@/core/api/client'
import { displayConfigLabel as displayLabel, htmlToText as plainText } from '@/shared/utils/config-labels'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import { protocolsApi, type ProtocolSwitch } from '@/features/protocols/api'

type GroupId = 'protocols' | 'transports' | 'security' | 'other'
type Filter = 'all' | 'on' | 'off'

interface GroupDef {
  id: GroupId
  icon: string
  accent: string
}

// Friendlier buckets than the raw config categories; unknown keys fall into "other".
const GROUP_OF: Record<string, GroupId> = {
  vless_enable: 'protocols',
  vmess_enable: 'protocols',
  trojan_enable: 'protocols',
  shadowsocks2022_enable: 'protocols',
  shadowtls_enable: 'protocols',
  ssfaketls_enable: 'protocols',
  naive_enable: 'protocols',
  anytls_enable: 'protocols',
  snell_enable: 'protocols',
  socks_enable: 'protocols',
  tuic_enable: 'protocols',
  hysteria_enable: 'protocols',
  mieru_enable: 'protocols',
  wireguard_enable: 'protocols',
  ssh_server_enable: 'protocols',
  telegram_enable: 'protocols',
  dnstt_enable: 'protocols',
  http_proxy_enable: 'protocols',
  tcp_enable: 'transports',
  ws_enable: 'transports',
  grpc_enable: 'transports',
  httpupgrade_enable: 'transports',
  xhttp_enable: 'transports',
  xhttp_different_up_down_enable: 'transports',
  h2_enable: 'transports',
  quic_enable: 'transports',
  reality_enable: 'security',
  tls_ech_enable: 'security',
  tls_fragment_enable: 'security',
  tls_padding_enable: 'security',
  mux_enable: 'security',
}

const GROUPS: GroupDef[] = [
  { id: 'protocols', icon: 'pi pi-shield', accent: '#6366f1' },
  { id: 'transports', icon: 'pi pi-arrows-h', accent: '#0ea5e9' },
  { id: 'security', icon: 'pi pi-lock', accent: '#10b981' },
  { id: 'other', icon: 'pi pi-sliders-h', accent: '#f59e0b' },
]

const { t } = useI18n()
const toast = useToast()

const items = ref<ProtocolSwitch[]>([])
const draft = reactive<Record<string, boolean>>({})
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const search = ref('')
const filter = ref<Filter>('all')
const pendingApply = ref<RestartMode>('nothing')

const filterOptions = computed(() => [
  { label: t('protocols.filterAll'), value: 'all' },
  { label: t('protocols.filterOn'), value: 'on' },
  { label: t('protocols.filterOff'), value: 'off' },
])

function isChanged(item: ProtocolSwitch): boolean {
  return draft[item.key] !== item.enabled
}

const enabledCount = computed(() => items.value.filter((item) => draft[item.key]).length)
const enabledRatio = computed(() => (items.value.length ? enabledCount.value / items.value.length : 0))
const dirtyCount = computed(() => items.value.filter(isChanged).length)

const visibleGroups = computed(() => {
  const query = search.value.trim().toLowerCase()
  return GROUPS.map((def) => {
    const all = items.value.filter((item) => (GROUP_OF[item.key] ?? 'other') === def.id)
    const shown = all.filter((item) => {
      if (filter.value === 'on' && !draft[item.key]) return false
      if (filter.value === 'off' && draft[item.key]) return false
      if (!query) return true
      return `${displayLabel(item.label)} ${item.key} ${plainText(item.description)}`.toLowerCase().includes(query)
    })
    return {
      ...def,
      title: t(`protocols.groups.${def.id}.title`),
      hint: t(`protocols.groups.${def.id}.hint`),
      items: shown,
      on: all.filter((item) => draft[item.key]).length,
      total: all.length,
    }
  }).filter((group) => group.items.length > 0)
})

function toggle(item: ProtocolSwitch) {
  draft[item.key] = !draft[item.key]
}

function setGroup(group: { items: ProtocolSwitch[] }, value: boolean) {
  for (const item of group.items) draft[item.key] = value
}

// Links inside a description must not toggle the tile.
function onDescriptionClick(event: MouseEvent) {
  if ((event.target as HTMLElement | null)?.closest('a')) event.stopPropagation()
}

function resetDraft() {
  for (const key of Object.keys(draft)) delete draft[key]
  for (const item of items.value) draft[item.key] = item.enabled
}

function discard() {
  resetDraft()
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    items.value = (await protocolsApi.list()).items
    resetDraft()
  } catch (error) {
    loadError.value = apiErrorMessage(error) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function save() {
  const values = Object.fromEntries(items.value.filter(isChanged).map((item) => [item.key, draft[item.key]]))
  saving.value = true
  try {
    const res = await protocolsApi.update(values)
    items.value = res.items
    resetDraft()
    pendingApply.value = strongerRestartMode(pendingApply.value, res.restart_mode)
    toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(error), life: 6000 })
  } finally {
    saving.value = false
  }
}

function confirmLeave(): boolean {
  return dirtyCount.value === 0 || window.confirm(t('protocols.leaveUnsaved'))
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (dirtyCount.value > 0) event.preventDefault()
}

onBeforeRouteLeave(() => confirmLeave())
onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
  void load()
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
</script>

<style>
/* Registered so the summary ring can animate its fill. */
@property --proto-progress {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
</style>

<style scoped>
.protocols-page {
  transition: padding-bottom 0.25s ease;
}
.protocols-page--dirty {
  padding-bottom: 5.5rem;
}

/* Summary */
.proto-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.proto-summary__stat {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}
.proto-summary__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  flex: 1 1 22rem;
  justify-content: flex-end;
}
.proto-search {
  flex: 1 1 14rem;
  max-width: 22rem;
}
.proto-ring {
  --proto-progress: 0deg;
  flex-shrink: 0;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(var(--p-primary-color) var(--proto-progress), var(--p-content-border-color) 0);
  transition: --proto-progress 0.6s ease;
}
.proto-ring__value {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 700;
  background: var(--p-content-background);
}

/* Groups */
.proto-group {
  padding: 1rem 1.25rem 1.25rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.proto-group__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.proto-group__icon {
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--proto-accent);
  background: color-mix(in srgb, var(--proto-accent) 14%, transparent);
  font-size: 1.1rem;
}
.proto-group__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.proto-group__hint {
  margin: 0.15rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.proto-group__bulk {
  display: flex;
  gap: 0.25rem;
}

/* Tiles */
.proto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 17rem), 1fr));
  gap: 0.75rem;
}
.proto-tile {
  --proto-accent: var(--p-primary-color);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.9rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  cursor: pointer;
  user-select: none;
  outline: none;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease,
    background-color 0.25s ease;
  animation: proto-in 0.35s ease both;
  animation-delay: var(--proto-delay, 0ms);
}
.proto-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px -8px color-mix(in srgb, var(--proto-accent) 45%, transparent);
}
.proto-tile:focus-visible {
  border-color: var(--proto-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--proto-accent) 30%, transparent);
}
.proto-tile:active {
  transform: scale(0.99);
}
.proto-tile--on {
  border-color: color-mix(in srgb, var(--proto-accent) 55%, transparent);
  background: color-mix(in srgb, var(--proto-accent) 7%, var(--p-content-background));
}
.proto-tile--changed::after {
  content: '';
  position: absolute;
  inset-block-start: -1px;
  inset-inline-start: 1rem;
  inset-inline-end: 1rem;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--p-orange-400, #fb923c);
  animation: proto-in 0.25s ease both;
}
.proto-tile__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.proto-tile__name {
  font-weight: 600;
  line-height: 1.3;
}
.proto-tile__desc {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.proto-tile__desc :deep(a) {
  color: var(--p-primary-color);
}
.proto-tile__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: auto;
}
.proto-tile__meta:empty {
  display: none;
}
.proto-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.proto-chip i {
  font-size: 0.65rem;
}
.proto-chip--warn {
  color: var(--p-orange-600, #c2410c);
  background: color-mix(in srgb, var(--p-orange-400, #fb923c) 18%, transparent);
}
.proto-chip--link {
  text-decoration: none;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}
.proto-chip--link:hover {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.proto-chip--changed {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}

.proto-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem 1rem;
  color: var(--p-text-muted-color);
}
.proto-empty i {
  font-size: 1.75rem;
}

/* Animations */
@keyframes proto-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes proto-pulse {
  50% {
    opacity: 0.35;
  }
}
.proto-fade-enter-active,
.proto-fade-leave-active {
  transition: opacity 0.2s ease;
}
.proto-fade-enter-from,
.proto-fade-leave-to {
  opacity: 0;
}
.proto-tile-move,
.proto-group-move {
  transition: transform 0.3s ease;
}
.proto-tile-enter-active,
.proto-group-enter-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.proto-tile-leave-active,
.proto-group-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
  position: absolute;
  visibility: hidden;
}
.proto-tile-enter-from,
.proto-tile-leave-to,
.proto-group-enter-from,
.proto-group-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

@media (max-width: 640px) {
  .proto-summary,
  .proto-group {
    padding: 0.9rem;
    border-radius: 14px;
  }
  .proto-summary__filters {
    justify-content: stretch;
  }
  .proto-search {
    max-width: none;
  }
  .proto-filter {
    width: 100%;
    display: flex;
  }
  .proto-filter :deep(.p-togglebutton) {
    flex: 1;
  }
  .proto-group__bulk {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (prefers-reduced-motion: reduce) {
  .proto-tile,
  .proto-tile--changed::after {
    animation: none;
  }
  .proto-tile,
  .proto-tile:hover {
    transition: none;
    transform: none;
  }
}
</style>
