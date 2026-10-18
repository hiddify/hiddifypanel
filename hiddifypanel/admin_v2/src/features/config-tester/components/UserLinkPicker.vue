<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AutoComplete from 'primevue/autocomplete'
import Tag from 'primevue/tag'
import MeterBar from '@/shared/components/MeterBar.vue'
import { getHttp } from '@/core/api/client'
import { UNLIMITED_DAYS, UNLIMITED_GB, STATUS_ICON, type UserStatus } from '@/features/users/api'
import { expireTone, relativeDays, sizeText } from '@/features/users/format'

/** One user row from ``GET config-tester/user-link/``. */
export interface UserHit {
  name: string
  comment: string
  uuid: string
  url: string
  status: UserStatus
  remaining_days: number
  package_days: number
  current_usage_GB: number
  usage_limit_GB: number
}

const model = defineModel<string>({ required: true })
defineProps<{ disabled?: boolean; inputId?: string }>()
const emit = defineEmits<{ enter: [KeyboardEvent]; pick: [UserHit] }>()

const { t, locale } = useI18n()
const hits = ref<UserHit[]>([])
const loading = ref(false)
let seq = 0
/** Local field value: AutoComplete may briefly hold a UserHit; parent ``model`` stays a URL string. */
const draft = ref<string | UserHit>(model.value || '')

const STATUS_SEVERITY: Record<UserStatus, 'success' | 'warn' | 'danger' | 'secondary'> = {
  active: 'success',
  disabled: 'secondary',
  expired: 'danger',
  no_data: 'warn',
}

function asUrl(value: string | UserHit | null | undefined): string {
  if (value && typeof value === 'object' && typeof value.url === 'string') return value.url
  return typeof value === 'string' ? value : ''
}

watch(
  model,
  (value) => {
    const text = typeof value === 'string' ? value : asUrl(value)
    if (asUrl(draft.value) !== text) draft.value = text
  },
  { immediate: true },
)

watch(draft, (value) => {
  const text = asUrl(value)
  if (value && typeof value === 'object') {
    // Selection assigned the whole user: keep only the URL in the input and parent.
    draft.value = text
  }
  if (model.value !== text) model.value = text
})

async function search(event: { query: string }) {
  const q = (event.query || '').trim()
  if (/^https?:\/\//i.test(q)) {
    hits.value = []
    return
  }
  const n = ++seq
  loading.value = true
  try {
    const { data } = await getHttp().get<{ users: UserHit[] }>('config-tester/user-link/', {
      params: { q },
      skipAuthRedirect: true,
    })
    if (n === seq) hits.value = data.users || []
  } catch {
    if (n === seq) hits.value = []
  } finally {
    if (n === seq) loading.value = false
  }
}

function onPick(event: { value: UserHit }) {
  const hit = event.value
  if (!hit?.url) return
  hits.value = []
  draft.value = hit.url
  model.value = hit.url
  void nextTick(() => {
    draft.value = hit.url
    model.value = hit.url
  })
  emit('pick', hit)
}

function onEnter(event: KeyboardEvent) {
  emit('enter', event)
}

function initial(name: string): string {
  const s = (name || '?').trim()
  return s ? s[0]!.toUpperCase() : '?'
}

function unlimitedGb(v: number): boolean {
  return v >= UNLIMITED_GB
}

function usageLabel(u: UserHit): string {
  const used = sizeText(u.current_usage_GB, locale.value)
  if (unlimitedGb(u.usage_limit_GB)) return `${used} / ∞`
  return `${used} / ${sizeText(u.usage_limit_GB, locale.value)}`
}

function daysLabel(u: UserHit): string {
  if (u.package_days >= UNLIMITED_DAYS) return '∞'
  return relativeDays(u.remaining_days, locale.value)
}

function daysTone(u: UserHit): string {
  if (u.package_days >= UNLIMITED_DAYS) return 'ok'
  return expireTone(u.remaining_days)
}

const panelHint = computed(() => t('configTester.findHint'))
</script>

<template>
  <AutoComplete
    v-model="draft"
    :input-id="inputId"
    :suggestions="hits"
    option-label="name"
    data-key="uuid"
    :force-selection="false"
    :complete-on-focus="true"
    :min-length="0"
    :delay="180"
    :disabled="disabled"
    :loading="loading"
    fluid
    dir="ltr"
    class="ulp"
    input-class="ulp__input font-mono"
    panel-class="ulp-panel"
    overlay-class="ulp-overlay"
    scroll-height="min(70dvh, 26rem)"
    :placeholder="t('configTester.urlPlaceholder')"
    @complete="search"
    @item-select="onPick"
    @keydown.enter="onEnter"
  >
    <template #option="{ option }">
      <div class="ulp-row" :class="`ulp-row--${option.status}`">
        <span class="ulp-avatar" aria-hidden="true">{{ initial(option.name) }}</span>
        <div class="ulp-main">
          <div class="ulp-top">
            <span class="ulp-name">{{ option.name || '—' }}</span>
            <Tag :value="t(`users.status.${option.status}`)" :severity="STATUS_SEVERITY[option.status as UserStatus]" :icon="STATUS_ICON[option.status as UserStatus]" class="ulp-status" />
          </div>
          <p v-if="option.comment" class="ulp-note">{{ option.comment }}</p>
          <div class="ulp-meta">
            <div class="ulp-usage">
              <MeterBar :used="option.current_usage_GB" :max="unlimitedGb(option.usage_limit_GB) ? null : option.usage_limit_GB" :text="usageLabel(option)" size="xs" />
            </div>
            <span class="ulp-days" :class="`is-${daysTone(option)}`" dir="auto">
              <i class="pi pi-calendar" />
              {{ daysLabel(option) }}
            </span>
          </div>
          <span class="ulp-uuid" dir="ltr">{{ option.uuid }}</span>
        </div>
        <i class="pi pi-link ulp-go" aria-hidden="true" />
      </div>
    </template>
    <template #empty>
      <div class="ulp-empty">
        <i class="pi pi-users" />
        <span>{{ t('configTester.findEmpty') }}</span>
        <small>{{ panelHint }}</small>
      </div>
    </template>
  </AutoComplete>
</template>

<style scoped>
.ulp {
  flex: 1;
  min-width: 0;
  width: 100%;
}
.ulp :deep(.p-autocomplete),
.ulp.p-autocomplete {
  width: 100%;
}
.ulp :deep(.p-autocomplete-input),
.ulp :deep(.ulp__input) {
  width: 100%;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
}

.ulp-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  width: min(100%, 36rem);
  max-width: 92vw;
  padding: 0.35rem 0.15rem;
  box-sizing: border-box;
}
.ulp-avatar {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 12px;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--p-primary-contrast-color);
  background: linear-gradient(145deg, var(--p-primary-color), color-mix(in srgb, var(--p-primary-color) 55%, #111));
  box-shadow: 0 4px 12px -6px var(--p-primary-color);
}
.ulp-row--disabled .ulp-avatar,
.ulp-row--expired .ulp-avatar {
  filter: grayscale(0.35);
  opacity: 0.85;
}
.ulp-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}
.ulp-top {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}
.ulp-name {
  font-weight: 700;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ulp-status {
  flex-shrink: 0;
  font-size: 0.7rem;
}
.ulp-note {
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ulp-meta {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}
.ulp-usage {
  flex: 1;
  min-width: 0;
}
.ulp-days {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  font-size: 0.75rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 12%, transparent);
}
.ulp-days.is-ok {
  color: var(--p-green-600, #16a34a);
}
.ulp-days.is-warn {
  color: var(--p-yellow-600, #ca8a04);
}
.ulp-days.is-danger {
  color: var(--p-red-600, #dc2626);
}
.ulp-uuid {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.85;
}
.ulp-go {
  flex-shrink: 0;
  align-self: center;
  color: var(--p-primary-color);
  opacity: 0.55;
  font-size: 0.85rem;
}
.ulp-row:hover .ulp-go {
  opacity: 1;
}
.ulp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 1.25rem 1rem;
  color: var(--p-text-muted-color);
  text-align: center;
}
.ulp-empty i {
  font-size: 1.4rem;
  opacity: 0.7;
}
.ulp-empty small {
  font-size: 0.75rem;
  max-width: 16rem;
}

@media (max-width: 640px) {
  .ulp-row {
    width: 100%;
    max-width: 100%;
    gap: 0.6rem;
  }
  .ulp-avatar {
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 10px;
  }
  .ulp-meta {
    flex-wrap: wrap;
  }
  .ulp-usage {
    flex: 1 1 100%;
  }
  .ulp-go {
    display: none;
  }
  .ulp-uuid {
    font-size: 0.62rem;
  }
}
</style>

<!-- Overlay is teleported to body: unscoped panel polish -->
<style>
.ulp-overlay.p-autocomplete-overlay,
.p-autocomplete-overlay.ulp-overlay {
  border-radius: 16px !important;
  overflow: hidden;
  box-shadow:
    0 18px 50px -24px rgba(15, 23, 42, 0.45),
    0 0 0 1px color-mix(in srgb, var(--p-primary-color) 18%, var(--p-content-border-color)) !important;
  border: none !important;
  max-width: min(36rem, calc(100vw - 1.25rem));
}
.ulp-overlay .p-autocomplete-list,
.ulp-panel .p-autocomplete-list {
  padding: 0.35rem !important;
  gap: 0.2rem;
}
.ulp-overlay .p-autocomplete-option,
.ulp-panel .p-autocomplete-option {
  border-radius: 12px !important;
  padding: 0.45rem 0.55rem !important;
  margin: 0 !important;
}
.ulp-overlay .p-autocomplete-option:not(.p-disabled).p-focus,
.ulp-overlay .p-autocomplete-option:not(.p-disabled).p-autocomplete-option-selected {
  background: color-mix(in srgb, var(--p-primary-color) 12%, var(--p-content-background)) !important;
}
@media (max-width: 640px) {
  .ulp-overlay.p-autocomplete-overlay,
  .p-autocomplete-overlay.ulp-overlay {
    max-width: calc(100vw - 0.75rem);
    border-radius: 14px !important;
  }
}
</style>
