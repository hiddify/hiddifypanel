<template>
  <div class="settings-page" :class="{ 'settings-page--dirty': dirtyCount > 0 }">
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')" />

    <!-- Toolbar -->
    <section class="settings-toolbar">
      <IconField class="settings-search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="search" :placeholder="t('settings.search')" class="w-full" />
        <InputIcon v-if="search" class="pi pi-times settings-search__clear" @click="search = ''" />
      </IconField>
      <label class="settings-advanced" for="settings-show-advanced">
        <ToggleSwitch v-model="showAdvanced" input-id="settings-show-advanced" />
        <span>
          <span class="font-medium">{{ t('settings.showAdvanced') }}</span>
          <span v-if="!showAdvanced && hiddenTotal" class="settings-advanced__count">{{ t('settings.hiddenCount', { count: hiddenTotal }, hiddenTotal) }}</span>
        </span>
      </label>
    </section>

    <ApplyNotice v-model="pendingApply" />
    <Message v-if="newAdminPath" severity="warn" class="mb-4" :closable="false">
      {{ t('settings.adminPathChanged') }}
      <code class="settings-code">{{ newAdminPath }}</code>
    </Message>
    <Transition name="settings-fade">
      <Message v-if="formErrors.length" severity="error" class="mb-4" :closable="false">
        <ul class="settings-errors">
          <li v-for="error in formErrors" :key="error">{{ error }}</li>
        </ul>
      </Message>
    </Transition>

    <div v-if="loading" class="settings-layout">
      <div class="settings-nav settings-nav--skeleton"><Skeleton v-for="i in 8" :key="i" height="2.25rem" class="mb-2" /></div>
      <div class="flex flex-col gap-4">
        <Skeleton v-for="i in 3" :key="i" height="14rem" border-radius="16px" />
      </div>
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <div v-else class="settings-layout">
      <!-- Category navigation: sidebar on desktop, scrollable chips on mobile -->
      <nav class="settings-nav" :aria-label="t('settings.categories')">
        <button
          v-for="cat in visibleCategories"
          :key="cat.id"
          type="button"
          class="settings-nav__item"
          :class="{ 'settings-nav__item--active': activeCategory === cat.id }"
          :style="{ '--settings-accent': cat.accent }"
          @click="scrollToCategory(cat.id)"
        >
          <i :class="cat.icon" class="settings-nav__icon" />
          <span class="settings-nav__label">{{ cat.title }}</span>
          <span v-if="cat.changed" class="settings-nav__dot" :title="t('settings.changed')" />
        </button>
      </nav>

      <div class="settings-sections">
        <TransitionGroup name="settings-card" tag="div" class="flex flex-col gap-4">
          <section
            v-for="cat in visibleCategories"
            :id="`settings-cat-${cat.id}`"
            :key="cat.id"
            :ref="(el) => registerSection(cat.id, el as Element | null)"
            :data-category="cat.id"
            class="settings-card"
            :class="{ 'settings-card--collapsed': !cat.fields.length, 'settings-card--highlight': highlightCategory === cat.id }"
            :style="{ '--settings-accent': cat.accent }"
          >
            <header class="settings-card__header">
              <span class="settings-card__icon"><i :class="cat.icon" /></span>
              <div class="min-w-0 flex-1">
                <h3 class="settings-card__title">{{ cat.title }}</h3>
                <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
                <p v-if="cat.description" class="settings-card__desc" v-html="cat.description" />
              </div>
              <RouterLink v-if="cat.hasProtocolSwitches" :to="{ name: 'protocols' }" class="settings-card__link">
                <i class="pi pi-sliders-h" />{{ t('settings.openProtocols') }}
              </RouterLink>
            </header>

            <TransitionGroup v-if="cat.fields.length" name="settings-row" tag="div" class="settings-card__fields">
              <SettingFieldRow
                v-for="field in cat.fields"
                :key="field.key"
                v-model="draft[field.key]"
                :field="field"
                :errors="fieldErrors[field.key]"
                :changed="isChanged(field)"
                :highlighted="highlightKey === field.key"
                :mark-advanced="cat.mixed"
              />
            </TransitionGroup>

            <button v-if="cat.hidden > 0" type="button" class="settings-card__more" @click="expandCategory(cat.id)">
              <i class="pi pi-angle-down" />
              {{ cat.fields.length ? t('settings.showMore', { count: cat.hidden }, cat.hidden) : t('settings.showAdvancedIn', { count: cat.hidden }, cat.hidden) }}
            </button>
            <button v-else-if="cat.expanded && !showAdvanced && !searching" type="button" class="settings-card__more" @click="collapseCategory(cat.id)">
              <i class="pi pi-angle-up" />{{ t('settings.showLess') }}
            </button>
          </section>
        </TransitionGroup>

        <div v-if="!visibleCategories.length" class="settings-empty">
          <i class="pi pi-search" />
          <span>{{ t('settings.noMatch') }}</span>
          <Button v-if="searching" icon="pi pi-times" :label="t('common.resetFilters')" size="small" severity="secondary" outlined @click="search = ''" />
        </div>
      </div>
    </div>

    <StickySaveBar :count="dirtyCount" :saving="saving" @save="save" @discard="discard" />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import { useHashState } from '@/shared/composables/useHashState'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import ToggleSwitch from 'primevue/toggleswitch'
import PageHeader from '@/shared/components/PageHeader.vue'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import StickySaveBar from '@/shared/components/StickySaveBar.vue'
import SettingFieldRow from '@/features/settings/components/SettingFieldRow.vue'
import { apiErrorMessage } from '@/core/api/client'
import { displayConfigLabel, htmlToText } from '@/shared/utils/config-labels'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import { settingsApi, type SettingCategory, type SettingField, type SettingsErrorBody, type SettingValue } from '@/features/settings/api'

const ADVANCED_STORAGE_KEY = 'hiddify.settings.showAdvanced'

// Icon + accent per config category; unknown categories get the default.
const CATEGORY_LOOK: Record<string, { icon: string; accent: string }> = {
  admin: { icon: 'pi pi-user', accent: '#6366f1' },
  branding: { icon: 'pi pi-palette', accent: '#ec4899' },
  general: { icon: 'pi pi-cog', accent: '#0ea5e9' },
  proxies: { icon: 'pi pi-sitemap', accent: '#8b5cf6' },
  domain_fronting: { icon: 'pi pi-globe', accent: '#14b8a6' },
  telegram: { icon: 'pi pi-send', accent: '#0ea5e9' },
  http: { icon: 'pi pi-link', accent: '#64748b' },
  tls: { icon: 'pi pi-lock', accent: '#10b981' },
  mux: { icon: 'pi pi-clone', accent: '#f59e0b' },
  tls_trick: { icon: 'pi pi-bolt', accent: '#f97316' },
  ssh: { icon: 'pi pi-desktop', accent: '#64748b' },
  ssfaketls: { icon: 'pi pi-shield', accent: '#8b5cf6' },
  shadowtls: { icon: 'pi pi-shield', accent: '#8b5cf6' },
  shadowsocks: { icon: 'pi pi-shield', accent: '#8b5cf6' },
  mieru: { icon: 'pi pi-shield', accent: '#a855f7' },
  restls: { icon: 'pi pi-shield', accent: '#a855f7' },
  tuic: { icon: 'pi pi-send', accent: '#06b6d4' },
  hysteria: { icon: 'pi pi-wave-pulse', accent: '#06b6d4' },
  ssr: { icon: 'pi pi-shield', accent: '#a855f7' },
  kcp: { icon: 'pi pi-forward', accent: '#06b6d4' },
  warp: { icon: 'pi pi-cloud', accent: '#f97316' },
  reality: { icon: 'pi pi-eye-slash', accent: '#ef4444' },
  wireguard: { icon: 'pi pi-key', accent: '#22c55e' },
  dnstt: { icon: 'pi pi-server', accent: '#64748b' },
  advanced: { icon: 'pi pi-sliders-h', accent: '#f59e0b' },
  too_advanced: { icon: 'pi pi-exclamation-triangle', accent: '#ef4444' },
}
const DEFAULT_LOOK = { icon: 'pi pi-cog', accent: '#6366f1' }

const { t } = useI18n()
const toast = useToast()
const route = useRoute()

const categories = ref<SettingCategory[]>([])
const draft = reactive<Record<string, SettingValue>>({})
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const search = ref('')
const showAdvanced = ref(readStoredAdvanced())
const expanded = ref<Set<string>>(new Set())
const fieldErrors = ref<Record<string, string[]>>({})
const formErrors = ref<string[]>([])
const pendingApply = ref<RestartMode>('nothing')
const newAdminPath = ref<string | null>(null)
const activeCategory = ref<string | null>(null)
useHashState({ q: search, cat: activeCategory })
const highlightCategory = ref<string | null>(null)
const highlightKey = ref<string | null>(null)

function readStoredAdvanced(): boolean {
  try {
    return localStorage.getItem(ADVANCED_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

watch(showAdvanced, (value) => {
  try {
    localStorage.setItem(ADVANCED_STORAGE_KEY, value ? '1' : '0')
  } catch {
    // storage blocked: the toggle still works for this visit
  }
})

const allFields = computed(() => categories.value.flatMap((cat) => cat.fields))
const searching = computed(() => search.value.trim().length > 0)

function isChanged(field: SettingField): boolean {
  return draft[field.key] !== field.value
}

/** Local pattern/required check (the server re-validates). */
function localErrors(field: SettingField): string[] {
  if (field.type === 'bool' || !isChanged(field)) return []
  const value = String(draft[field.key] ?? '')
  if (field.required && !value.trim()) return [t('settings.required')]
  if (field.pattern && value) {
    try {
      if (!new RegExp(`^(?:${field.pattern})$`).test(value)) return [field.pattern_message || t('settings.invalid')]
    } catch {
      // pattern not valid JS; leave it to the server
    }
  }
  return []
}

const dirtyCount = computed(() => allFields.value.filter(isChanged).length)
const hasLocalErrors = computed(() => allFields.value.some((field) => localErrors(field).length > 0))

function matches(field: SettingField, query: string): boolean {
  return `${displayConfigLabel(field.label)} ${field.key} ${htmlToText(field.description)}`.toLowerCase().includes(query)
}

const visibleCategories = computed(() => {
  const query = search.value.trim().toLowerCase()
  return categories.value
    .map((cat) => {
      const look = CATEGORY_LOOK[cat.id] ?? DEFAULT_LOOK
      const isExpanded = expanded.value.has(cat.id)
      let fields: SettingField[]
      let hidden = 0
      if (query) {
        const catMatches = displayConfigLabel(cat.label).toLowerCase().includes(query)
        fields = catMatches ? cat.fields : cat.fields.filter((field) => matches(field, query))
      } else if (showAdvanced.value || isExpanded) {
        fields = cat.fields
      } else {
        // Keep changed and invalid fields visible even when they are advanced.
        fields = cat.fields.filter((field) => field.essential || isChanged(field) || fieldErrors.value[field.key])
        hidden = cat.fields.length - fields.length
      }
      return {
        id: cat.id,
        title: displayConfigLabel(cat.label),
        description: cat.description,
        icon: look.icon,
        accent: look.accent,
        fields,
        hidden,
        expanded: isExpanded,
        mixed: cat.fields.some((f) => f.essential) && cat.fields.some((f) => !f.essential),
        changed: cat.fields.some(isChanged),
        hasProtocolSwitches: cat.fields.some((f) => f.protocol_switch),
      }
    })
    .filter((cat) => cat.fields.length > 0 || cat.hidden > 0)
})

const hiddenTotal = computed(() => visibleCategories.value.reduce((sum, cat) => sum + cat.hidden, 0))

function expandCategory(id: string) {
  expanded.value = new Set([...expanded.value, id])
}

function collapseCategory(id: string) {
  const next = new Set(expanded.value)
  next.delete(id)
  expanded.value = next
}

// --- scroll spy + deep links ---
const sections = new Map<string, Element>()
let observer: IntersectionObserver | null = null

function registerSection(id: string, el: Element | null) {
  const previous = sections.get(id)
  if (previous && previous !== el) observer?.unobserve(previous)
  if (el) {
    sections.set(id, el)
    observer?.observe(el)
  } else {
    sections.delete(id)
  }
}

function scrollToCategory(id: string) {
  activeCategory.value = id
  document.getElementById(`settings-cat-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function flash(target: { category?: string; key?: string }) {
  highlightCategory.value = target.category ?? null
  highlightKey.value = target.key ?? null
  window.setTimeout(() => {
    highlightCategory.value = null
    highlightKey.value = null
  }, 1900)
}

async function openDeepLink() {
  const category = typeof route.query.category === 'string' ? route.query.category : ''
  const key = typeof route.query.key === 'string' ? route.query.key : ''
  const targetCategory = category || categories.value.find((cat) => cat.fields.some((f) => f.key === key))?.id
  if (!targetCategory) return
  expandCategory(targetCategory)
  await nextTick()
  const target = key ? document.getElementById(`setting-row-${key}`) : document.getElementById(`settings-cat-${targetCategory}`)
  target?.scrollIntoView({ behavior: 'smooth', block: key ? 'center' : 'start' })
  activeCategory.value = targetCategory
  flash({ category: key ? undefined : targetCategory, key: key || undefined })
}

// --- data ---
function resetDraft() {
  for (const key of Object.keys(draft)) delete draft[key]
  for (const field of allFields.value) draft[field.key] = field.value
}

function discard() {
  resetDraft()
  fieldErrors.value = {}
  formErrors.value = []
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    categories.value = await settingsApi.list()
    resetDraft()
  } catch (error) {
    loadError.value = apiErrorMessage(error) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
  await nextTick()
  await openDeepLink()
}

async function save() {
  const local: Record<string, string[]> = {}
  for (const field of allFields.value) {
    const errors = localErrors(field)
    if (errors.length) local[field.key] = errors
  }
  if (hasLocalErrors.value) {
    fieldErrors.value = local
    formErrors.value = [t('settings.fixErrors')]
    focusFirstError()
    return
  }
  const values = Object.fromEntries(allFields.value.filter(isChanged).map((field) => [field.key, draft[field.key]]))
  saving.value = true
  try {
    const res = await settingsApi.update(values)
    fieldErrors.value = {}
    formErrors.value = []
    categories.value = res.categories
    resetDraft()
    pendingApply.value = strongerRestartMode(pendingApply.value, res.restart_mode)
    if (res.new_admin_path) newAdminPath.value = res.new_admin_path
    for (const warning of res.warnings) toast.add({ severity: 'warn', summary: warning, life: 8000 })
    toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    if (res.reload) {
      toast.add({ severity: 'info', summary: t('settings.reloading'), life: 2000 })
      window.setTimeout(() => window.location.reload(), 900)
    }
  } catch (error) {
    const body = (error as { response?: { data?: SettingsErrorBody } })?.response?.data
    if (body && (body.errors || body.field_errors)) {
      fieldErrors.value = body.field_errors ?? {}
      formErrors.value = body.errors ?? []
      focusFirstError()
    } else {
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(error), life: 6000 })
    }
  } finally {
    saving.value = false
  }
}

async function focusFirstError() {
  const key = Object.keys(fieldErrors.value)[0]
  const category = key ? categories.value.find((cat) => cat.fields.some((f) => f.key === key))?.id : undefined
  if (category) expandCategory(category)
  await nextTick()
  const target = key ? document.getElementById(`setting-row-${key}`) : null
  ;(target ?? document.querySelector('.settings-page .p-message'))?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// Editing a field clears its error: compare with the value it had when the error was reported.
let errorSnapshot: Record<string, SettingValue> = {}
watch(fieldErrors, (errors) => {
  errorSnapshot = Object.fromEntries(Object.keys(errors).map((key) => [key, draft[key]]))
})
watch(
  draft,
  () => {
    const current = fieldErrors.value
    const next = Object.fromEntries(Object.entries(current).filter(([key]) => draft[key] === errorSnapshot[key]))
    if (Object.keys(next).length !== Object.keys(current).length) {
      fieldErrors.value = next
      if (!Object.keys(next).length) formErrors.value = []
    }
  },
  { deep: true },
)

function confirmLeave(): boolean {
  return dirtyCount.value === 0 || window.confirm(t('settings.leaveUnsaved'))
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (dirtyCount.value > 0) event.preventDefault()
}

onBeforeRouteLeave(() => confirmLeave())
watch(
  () => [route.query.category, route.query.key],
  () => {
    if (!loading.value) void openDeepLink()
  },
)

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
      const first = visible[0]?.target as HTMLElement | undefined
      if (first?.dataset.category) activeCategory.value = first.dataset.category
    },
    { rootMargin: '-80px 0px -60% 0px' },
  )
  for (const el of sections.values()) observer.observe(el)
  window.addEventListener('beforeunload', onBeforeUnload)
  void load()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<style scoped>
.settings-page {
  transition: padding-bottom 0.25s ease;
}
.settings-page--dirty {
  padding-bottom: 5.5rem;
}

/* Toolbar */
.settings-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.25rem;
  padding: 0.85rem 1.1rem;
  margin-bottom: 1.25rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.settings-search {
  flex: 1 1 16rem;
  max-width: 28rem;
}
.settings-search__clear {
  cursor: pointer;
}
.settings-advanced {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  cursor: pointer;
  user-select: none;
}
.settings-advanced__count {
  display: block;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.settings-errors {
  margin: 0;
  padding-inline-start: 1.1rem;
}
.settings-code {
  padding: 0.05rem 0.4rem;
  border-radius: 6px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}

/* Layout */
.settings-layout {
  display: grid;
  grid-template-columns: 14rem minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}
.settings-nav {
  position: sticky;
  top: 5.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  max-height: calc(100vh - 7rem);
  overflow-y: auto;
  padding: 0.5rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  scrollbar-width: thin;
}
.settings-nav__item {
  --settings-accent: var(--p-primary-color);
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease;
}
.settings-nav__item:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.settings-nav__item--active {
  color: var(--settings-accent);
  background: color-mix(in srgb, var(--settings-accent) 12%, transparent);
  font-weight: 600;
}
.settings-nav__icon {
  width: 1rem;
  text-align: center;
  color: var(--settings-accent);
}
.settings-nav__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.settings-nav__dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--p-orange-400, #fb923c);
}

/* Cards */
.settings-card {
  --settings-accent: var(--p-primary-color);
  scroll-margin-top: 5.5rem;
  padding: 1rem 1.1rem 0.75rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  transition:
    box-shadow 0.3s ease,
    border-color 0.3s ease;
}
.settings-card--collapsed {
  padding-bottom: 0.9rem;
}
.settings-card--highlight {
  border-color: var(--settings-accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--settings-accent) 22%, transparent);
}
.settings-card__header {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  margin-bottom: 0.4rem;
}
.settings-card__icon {
  width: 2.4rem;
  height: 2.4rem;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--settings-accent);
  background: color-mix(in srgb, var(--settings-accent) 14%, transparent);
}
.settings-card__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.settings-card__desc {
  margin: 0.2rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.settings-card__desc :deep(a) {
  color: var(--p-primary-color);
}
.settings-card__link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  text-decoration: none;
  color: var(--settings-accent);
  background: color-mix(in srgb, var(--settings-accent) 10%, transparent);
  transition: background-color 0.15s ease;
}
.settings-card__link:hover {
  background: color-mix(in srgb, var(--settings-accent) 18%, transparent);
}
.settings-card__fields {
  position: relative;
  display: flex;
  flex-direction: column;
}
.settings-card__more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  width: 100%;
  margin-top: 0.35rem;
  padding: 0.55rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: 10px;
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    background-color 0.15s ease;
}
.settings-card__more:hover {
  color: var(--settings-accent);
  border-color: var(--settings-accent);
  background: color-mix(in srgb, var(--settings-accent) 6%, transparent);
}
.settings-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem 1rem;
  color: var(--p-text-muted-color);
}
.settings-empty i {
  font-size: 1.75rem;
}

/* Animations */
.settings-fade-enter-active,
.settings-fade-leave-active {
  transition: opacity 0.2s ease;
}
.settings-fade-enter-from,
.settings-fade-leave-to {
  opacity: 0;
}
.settings-card-move,
.settings-row-move {
  transition: transform 0.3s ease;
}
.settings-card-enter-active,
.settings-row-enter-active {
  transition:
    opacity 0.28s ease,
    transform 0.28s ease;
}
.settings-card-leave-active,
.settings-row-leave-active {
  transition: opacity 0.15s ease;
  position: absolute;
  inset-inline: 0;
  visibility: hidden;
}
.settings-card-enter-from,
.settings-row-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.settings-card-leave-to,
.settings-row-leave-to {
  opacity: 0;
}

/* Mobile: the category list becomes a sticky, horizontally scrolling chip bar. */
@media (max-width: 991px) {
  .settings-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .settings-nav {
    top: 4.25rem;
    z-index: 5;
    flex-direction: row;
    max-height: none;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0.4rem;
    border-radius: 14px;
    scroll-snap-type: x proximity;
    box-shadow: 0 6px 16px -12px rgba(0, 0, 0, 0.4);
  }
  .settings-nav--skeleton {
    display: none;
  }
  .settings-nav__item {
    width: auto;
    flex-shrink: 0;
    scroll-snap-align: start;
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
  }
  .settings-nav__label {
    overflow: visible;
  }
  .settings-card {
    scroll-margin-top: 8rem;
  }
}
@media (max-width: 640px) {
  .settings-toolbar,
  .settings-card {
    padding: 0.85rem;
    border-radius: 14px;
  }
  .settings-search {
    max-width: none;
  }
  .settings-card__header {
    flex-wrap: wrap;
  }
  .settings-card__link {
    margin-inline-start: auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .settings-card-move,
  .settings-row-move,
  .settings-card-enter-active,
  .settings-row-enter-active {
    transition: none;
  }
}
</style>
