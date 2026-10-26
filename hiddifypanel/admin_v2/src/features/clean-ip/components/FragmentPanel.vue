<script setup lang="ts">
/**
 * Scanner → Fragment: apply FinalMask TLS-fragment presets to a CDN/worker domain.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { apiErrorMessage } from '@/core/api/client'
import { domainsApi, fragmentSettingsOf, setTlsFragmentInExtra, type DomainRow, type TlsFragmentMode } from '@/features/domains/api'

export interface FragmentPreset {
  id: string
  mode: TlsFragmentMode
  packets?: string
  lengths?: string[]
  delays?: string[]
  maxSplit?: string
}

const PRESETS: FragmentPreset[] = [
  { id: 'off', mode: 'off' },
  { id: 'default', mode: 'on', packets: 'tlshello', lengths: ['10-100'], delays: ['50-200'], maxSplit: '3-6' },
  { id: 'fine', mode: 'on', packets: 'tlshello', lengths: ['50-100'], delays: ['10-20'], maxSplit: '3-6' },
  { id: 'coarse', mode: 'on', packets: 'tlshello', lengths: ['100-200'], delays: ['10-20'], maxSplit: '3-6' },
  { id: 'multi', mode: 'on', packets: 'tlshello', lengths: ['3-5', '6-8', '10-20'], delays: ['10-20'], maxSplit: '3-6' },
  { id: '1-3', mode: 'on', packets: '1-3', lengths: ['10-100'], delays: ['50-200'], maxSplit: '3-6' },
  { id: 'tight', mode: 'on', packets: 'tlshello', lengths: ['1-10'], delays: ['1-5'], maxSplit: '2-4' },
]

function listKey(values: string[]): string {
  return values.join(',')
}

const props = defineProps<{ domains: DomainRow[]; loaded: boolean }>()
const emit = defineEmits<{ saved: [domains: DomainRow[]] }>()
const domainId = defineModel<number | null>('domainId', { required: true })

const { t } = useI18n()
const toast = useToast()
const applying = ref<string | null>(null)

const cdnDomains = computed(() => props.domains.filter((d) => d.mode === 'cdn' || d.mode === 'worker'))
const domainOptions = computed(() =>
  cdnDomains.value.map((d) => ({
    id: d.id,
    label: d.alias && d.alias !== d.domain ? `${d.alias} (${d.domain})` : d.domain || `#${d.id}`,
  })),
)
const domain = computed(() => props.domains.find((d) => d.id === domainId.value) ?? null)

const current = computed(() => {
  try {
    const settings = fragmentSettingsOf(JSON.parse(domain.value?.extra_params || '{}') as Record<string, unknown>)
    if (!settings) return { mode: 'off' as TlsFragmentMode, label: '' }
    return {
      mode: 'on' as TlsFragmentMode,
      label: `${settings.packets} · ${settings.lengths.join(', ')} · ${settings.delays.join(', ')} · ${settings.maxSplit}`,
      ...settings,
    }
  } catch {
    return { mode: 'off' as TlsFragmentMode, label: '' }
  }
})

watch(
  cdnDomains,
  (list) => {
    if (!list.length) {
      domainId.value = null
      return
    }
    if (!list.some((d) => d.id === domainId.value)) domainId.value = list[0].id
  },
  { immediate: true },
)

function mergeExtra(extraRaw: string, preset: FragmentPreset): string {
  let obj: Record<string, unknown> = {}
  try {
    const parsed = JSON.parse(extraRaw.trim() || '{}')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) obj = { ...parsed }
  } catch {
    obj = {}
  }
  if (preset.mode === 'off') return JSON.stringify(setTlsFragmentInExtra(obj, { mode: 'off' }), null, 2)
  return JSON.stringify(
    setTlsFragmentInExtra(obj, {
      mode: 'on',
      packets: preset.packets,
      lengths: preset.lengths,
      delays: preset.delays,
      maxSplit: preset.maxSplit,
    }),
    null,
    2,
  )
}

async function applyPreset(preset: FragmentPreset) {
  if (!domain.value) return
  applying.value = preset.id
  try {
    const state = await domainsApi.update(domain.value.id, { extra_params: mergeExtra(domain.value.extra_params || '{}', preset) })
    emit('saved', state.domains)
    toast.add({
      severity: 'success',
      summary: t('cleanIp.fragment.applied', { name: t(`cleanIp.fragment.presets.${preset.id}`), domain: domain.value.domain }),
      life: 4000,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
  } finally {
    applying.value = null
  }
}

function presetMatches(p: FragmentPreset): boolean {
  const c = current.value
  if (p.mode === 'off') return c.mode === 'off'
  if (c.mode !== 'on' || !('lengths' in c)) return false
  return (
    c.packets === p.packets &&
    listKey(c.lengths) === listKey(p.lengths || []) &&
    listKey(c.delays) === listKey(p.delays || []) &&
    c.maxSplit === p.maxSplit
  )
}
</script>

<template>
  <div class="frag">
    <Message severity="info" :closable="false" class="frag__lead">{{ t('cleanIp.fragment.lead') }}</Message>

    <label class="frag__field">
      <span class="frag__label">{{ t('cleanIp.domain') }}</span>
      <Select
        v-model="domainId"
        :options="domainOptions"
        option-label="label"
        option-value="id"
        :placeholder="t('cleanIp.pickDomain')"
        :disabled="!loaded || !domainOptions.length"
        class="frag__ltr"
        fluid
      />
      <small v-if="loaded && !domainOptions.length" class="frag__hint">{{ t('cleanIp.fragment.noCdn') }}</small>
    </label>

    <div v-if="domain" class="frag__current">
      <div class="frag__current-head">
        <b>{{ t('cleanIp.fragment.current') }}</b>
        <Tag :value="t(`cleanIp.fragment.mode.${current.mode}`)" :severity="current.mode === 'off' ? 'secondary' : 'success'" />
      </div>
      <p v-if="current.mode === 'on'" class="frag__values" dir="ltr">{{ current.label }}</p>
      <p v-else class="frag__values">{{ t('cleanIp.fragment.disabled') }}</p>
    </div>

    <div class="frag__presets">
      <h3 class="frag__h">{{ t('cleanIp.fragment.presetsTitle') }}</h3>
      <p class="frag__hint">{{ t('cleanIp.fragment.presetsHint') }}</p>
      <ul class="frag__list">
        <li v-for="p in PRESETS" :key="p.id" class="frag__card" :class="{ 'frag__card--active': presetMatches(p) }">
          <div class="frag__card-main">
            <b>{{ t(`cleanIp.fragment.presets.${p.id}`) }}</b>
            <small v-if="p.mode === 'off'">{{ t('cleanIp.fragment.presets.offHint') }}</small>
            <small v-else dir="ltr">{{ p.packets }} · {{ (p.lengths || []).join(', ') }} · {{ (p.delays || []).join(', ') }} · {{ p.maxSplit }}</small>
          </div>
          <Button
            size="small"
            :label="presetMatches(p) ? t('cleanIp.fragment.currentBtn') : t('cleanIp.fragment.apply')"
            :icon="presetMatches(p) ? 'pi pi-check' : 'pi pi-save'"
            :severity="presetMatches(p) ? 'success' : 'primary'"
            :outlined="!presetMatches(p)"
            :loading="applying === p.id"
            :disabled="!domain || !!applying"
            @click="applyPreset(p)"
          />
        </li>
      </ul>
    </div>

    <Message severity="secondary" :closable="false">{{ t('cleanIp.fragment.testHint') }}</Message>
  </div>
</template>

<style scoped>
.frag {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.frag__lead :deep(.p-message-text) {
  line-height: 1.45;
}
.frag__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-width: 28rem;
}
.frag__label,
.frag__h {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
}
.frag__hint {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}
.frag__ltr :deep(.p-select-label) {
  direction: ltr;
  text-align: start;
}
.frag__current {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.85rem 1rem;
  border-radius: 0.9rem;
  border: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-content-background));
  max-width: 36rem;
}
.frag__current-head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}
.frag__values {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
}
.frag__presets {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.frag__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  max-width: 40rem;
}
.frag__card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.9rem;
  border-radius: 0.85rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.frag__card--active {
  border-color: color-mix(in srgb, var(--p-green-500) 55%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-green-500) 8%, var(--p-content-background));
}
.frag__card-main {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.frag__card-main b {
  font-size: 0.9rem;
}
.frag__card-main small {
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
}
@media (max-width: 520px) {
  .frag__card {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
