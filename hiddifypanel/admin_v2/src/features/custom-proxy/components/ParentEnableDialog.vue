<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import { apiErrorMessage } from '@/core/api/client'
import { strongerRestartMode, type RestartMode } from '@/shared/utils/restart-mode'
import { settingsApi, type SettingField, type SettingValue } from '@/features/settings/api'
import { parentEnablePrompt } from '@/features/custom-proxy/parent-enable'

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** A failure, in words: what happened (`code`: why and what to do), and the server's own text for the details. */
interface Failure {
  phase: 'load' | 'save'
  code: 'newer' | 'network' | 'auth' | 'invalid' | 'server'
  detail: string
}

const fields = ref<SettingField[]>([])
/** Each setting's category name, as on the Settings page: where to find it there. */
const categoryOf = ref<Record<string, string>>({})
const values = ref<Record<string, SettingValue>>({})
const loading = ref(false)
const saving = ref(false)
const failure = ref<Failure | null>(null)
const detailsOpen = ref(false)
const copied = ref(false)
const pendingApply = ref<RestartMode>('nothing')

const visible = computed({
  get: () => parentEnablePrompt.visible,
  set: (v: boolean) => (parentEnablePrompt.visible = v),
})

/** The value that lifts the block: on for a switch, "both" for a core choice (it serves every proxy). */
function unblockingValue(field: SettingField): SettingValue {
  if (field.type === 'bool') return true
  const both = field.choices?.find((c) => c.value === 'both')
  return both?.value ?? field.value
}

/** Sorts an API error into a cause the admin can act on. */
function explain(err: unknown, phase: Failure['phase']): Failure {
  const detail = apiErrorMessage(err)
  const res = (err as { response?: { status?: number } })?.response
  let code: Failure['code'] = 'server'
  // A setting in the database that this version does not know: written by a newer panel (a beta, then back).
  if (/not among the defined enum values/i.test(detail)) code = 'newer'
  else if (!res) code = 'network'
  else if (res.status === 401 || res.status === 403) code = 'auth'
  else if (res.status === 400 || res.status === 422) code = 'invalid'
  return { phase, code, detail }
}

watch(
  () => parentEnablePrompt.visible,
  async (open) => {
    if (!open) return
    failure.value = null
    detailsOpen.value = false
    fields.value = []
    loading.value = true
    try {
      const keys = new Set(parentEnablePrompt.blocked.map((b) => b.key))
      const categories = await settingsApi.list()
      fields.value = categories.flatMap((c) => c.fields).filter((f) => keys.has(f.key))
      categoryOf.value = Object.fromEntries(categories.flatMap((c) => c.fields.map((f) => [f.key, c.label])))
      values.value = Object.fromEntries(fields.value.map((f) => [f.key, unblockingValue(f)]))
    } catch (err) {
      failure.value = explain(err, 'load')
    } finally {
      loading.value = false
    }
  },
)

/** Every blocker is one we can set here; otherwise only the settings link is offered. */
const canQuickEnable = computed(() => fields.value.length > 0 && fields.value.length === parentEnablePrompt.blocked.length)
/** One card per blocking setting, with its control when it could be loaded. */
const items = computed(() => parentEnablePrompt.blocked.map((b) => ({ ...b, field: fields.value.find((f) => f.key === b.key) })))

async function quickEnable() {
  saving.value = true
  failure.value = null
  try {
    const res = await settingsApi.update(values.value)
    pendingApply.value = strongerRestartMode(pendingApply.value, res.restart_mode)
    for (const warning of res.warnings) toast.add({ severity: 'warn', summary: warning, life: 8000 })
    await parentEnablePrompt.onEnabled?.()
    parentEnablePrompt.visible = false
    toast.add({ severity: 'success', summary: t('proxy.quickEnableDone'), life: 3000 })
  } catch (err) {
    failure.value = explain(err, 'save')
  } finally {
    saving.value = false
  }
}

async function copyDetail() {
  if (!failure.value) return
  try {
    await navigator.clipboard.writeText(failure.value.detail)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1500)
  } catch {
    /* no clipboard (plain http): the text is there to select */
  }
}

/** Opens the admin_v2 settings page in a new tab, at the first blocking setting. */
function openSettings() {
  const key = parentEnablePrompt.blocked[0]?.key
  const { href } = router.resolve({ name: 'settings', query: key ? { key } : {} })
  window.open(href, '_blank', 'noopener,noreferrer')
  parentEnablePrompt.visible = false
}
</script>

<template>
  <ApplyNotice v-model="pendingApply" />
  <Dialog v-model:visible="visible" modal class="pe" :style="{ width: '34rem' }" :breakpoints="{ '575px': '95vw' }">
    <template #header>
      <div class="pe__head">
        <span class="pe__badge" aria-hidden="true"><i class="pi pi-lock" /></span>
        <span class="pe__title">{{ t('proxy.cannotEnable') }}</span>
      </div>
    </template>

    <p class="pe__lead">{{ canQuickEnable || loading ? t('proxy.enableBlock.lead') : t('proxy.enableBlock.leadManual') }}</p>

    <div v-if="loading" class="pe__loading"><i class="pi pi-spin pi-spinner" /></div>
    <ul v-else class="pe__items">
      <li v-for="item in items" :key="item.key" class="pe__item" :class="{ 'pe__item--on': item.field && values[item.key] === unblockingValue(item.field) }">
        <span class="pe__icon" aria-hidden="true"><i class="pi pi-sliders-h" /></span>
        <div class="pe__text">
          <label :for="`pe-${item.key}`" class="pe__label">{{ item.field?.label ?? item.label }}</label>
          <small class="pe__where"><i class="pi pi-cog" />{{ categoryOf[item.key] ? t('proxy.enableBlock.where', { category: categoryOf[item.key] }) : t('proxy.enableBlock.whereUnknown') }}</small>
        </div>
        <template v-if="item.field">
          <ToggleSwitch v-if="item.field.type === 'bool'" :input-id="`pe-${item.key}`" v-model="values[item.key] as boolean" />
          <Select
            v-else-if="item.field.choices?.length"
            :input-id="`pe-${item.key}`"
            v-model="values[item.key]"
            :options="item.field.choices"
            option-label="label"
            option-value="value"
            class="pe__select"
          />
        </template>
      </li>
    </ul>

    <!-- A failure in words: what happened, why, what to do; the server's own text folded away -->
    <section v-if="failure" class="pe__error" role="alert">
      <header class="pe__error-head">
        <i class="pi pi-exclamation-triangle" />
        <div>
          <strong>{{ t(`proxy.enableBlock.error.${failure.phase}`) }}</strong>
          <p>{{ t(`proxy.enableBlock.error.${failure.code}.why`) }}</p>
        </div>
      </header>
      <div class="pe__fix">
        <span class="pe__fix-title">{{ t('proxy.enableBlock.error.fixTitle') }}</span>
        <ol>
          <li>{{ t(`proxy.enableBlock.error.${failure.code}.fix1`) }}</li>
          <li>{{ t(`proxy.enableBlock.error.${failure.code}.fix2`) }}</li>
        </ol>
      </div>
      <div v-if="failure.detail" class="pe__details">
        <button type="button" class="pe__details-toggle" :aria-expanded="detailsOpen" @click="detailsOpen = !detailsOpen">
          <i :class="detailsOpen ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" />{{ t('proxy.enableBlock.error.details') }}
        </button>
        <div v-if="detailsOpen" class="pe__details-body">
          <code dir="ltr">{{ failure.detail }}</code>
          <Button :icon="copied ? 'pi pi-check' : 'pi pi-copy'" :label="copied ? t('proxy.enableBlock.error.copied') : t('proxy.enableBlock.error.copy')" text size="small" @click="copyDetail" />
        </div>
      </div>
    </section>

    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="visible = false" />
      <Button :label="t('proxy.goToSettings')" severity="secondary" text icon="pi pi-external-link" @click="openSettings" />
      <Button v-if="canQuickEnable" :label="t('proxy.quickEnable')" icon="pi pi-bolt" :loading="saving" @click="quickEnable" />
    </template>
  </Dialog>
</template>

<style scoped>
.pe__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.pe__badge {
  display: grid;
  place-items: center;
  width: 2.4rem;
  height: 2.4rem;
  flex-shrink: 0;
  border-radius: 12px;
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 15%, transparent);
}
.pe__title {
  font-size: 1.15rem;
  font-weight: 700;
}
.pe__lead {
  margin: 0 0 0.9rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}
.pe__loading {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
  font-size: 1.4rem;
}
.pe__items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
/* A blocking setting: its name, where it lives in Settings, and its switch beside it */
.pe__item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.05));
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.pe__item--on {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
}
.pe__icon {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 10px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.pe__text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
  min-width: 0;
}
.pe__label {
  font-weight: 600;
}
.pe__where {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--p-text-muted-color);
}
.pe__where .pi {
  font-size: 0.75rem;
}
.pe__select {
  min-width: 10rem;
}
/* The failure card: plain words first, the server's text folded away */
.pe__error {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  margin-top: 1rem;
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--p-red-500, #ef4444) 35%, transparent);
  border-inline-start-width: 4px;
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 6%, transparent);
}
.pe__error-head {
  display: flex;
  gap: 0.65rem;
}
.pe__error-head > .pi {
  margin-top: 0.15rem;
  color: var(--p-red-500, #ef4444);
}
.pe__error-head strong {
  display: block;
  margin-bottom: 0.2rem;
}
.pe__error-head p {
  margin: 0;
  line-height: 1.5;
}
.pe__fix-title {
  font-size: 0.85rem;
  font-weight: 700;
}
.pe__fix ol {
  margin: 0.3rem 0 0;
  list-style: decimal;
  padding-inline-start: 1.2rem;
  line-height: 1.55;
}
.pe__details-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.pe__details-toggle .pi {
  font-size: 0.7rem;
}
.pe__details-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  margin-top: 0.4rem;
}
.pe__details-body code {
  display: block;
  width: 100%;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  font-size: 0.78rem;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: left;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
</style>
