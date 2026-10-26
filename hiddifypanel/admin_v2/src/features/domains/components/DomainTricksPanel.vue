<script setup lang="ts">
/**
 * Domain tricks (inside Advanced): FinalMask templates + custom JSON.
 * Writes ``extra_params.tricks.finalmask`` — https://xtls.github.io/en/config/transports/finalmask.html
 */
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import {
  finalmaskOf,
  fragmentSettingsOf,
  setCustomFinalmaskInExtra,
  setTlsFragmentInExtra,
  trickTemplateOf,
  type TlsFragmentMode,
} from '@/features/domains/api'

const Json5Editor = defineAsyncComponent(() => import('@/shared/components/Json5Editor.vue'))

const extraText = defineModel<string>('extraText', { required: true })
const props = defineProps<{ enabled: boolean }>()

const { t } = useI18n()

type TemplateId = 'off' | 'tls_fragment' | 'custom'

interface FragPreset {
  id: string
  packets: string
  lengths: string
  delays: string
  maxSplit: string
}

const PRESETS: FragPreset[] = [
  { id: 'default', packets: 'tlshello', lengths: '10-100', delays: '50-200', maxSplit: '3-6' },
  { id: 'fine', packets: 'tlshello', lengths: '50-100', delays: '10-20', maxSplit: '3-6' },
  { id: 'coarse', packets: 'tlshello', lengths: '100-200', delays: '10-20', maxSplit: '3-6' },
  { id: 'multi', packets: 'tlshello', lengths: '3-5, 6-8, 10-20', delays: '10-20', maxSplit: '3-6' },
  { id: 'tight', packets: 'tlshello', lengths: '1-10', delays: '1-5', maxSplit: '2-4' },
  { id: '1-3', packets: '1-3', lengths: '10-100', delays: '50-200', maxSplit: '3-6' },
]

const CUSTOM_STARTER = `{
  "tcp": [
    {
      "type": "fragment",
      "settings": {
        "packets": "tlshello",
        "lengths": ["10-100"],
        "delays": ["50-200"],
        "maxSplit": "3-6"
      }
    }
  ]
}`

const template = ref<TemplateId>('off')
const packets = ref('tlshello')
const lengths = ref('10-100')
const delays = ref('50-200')
const maxSplit = ref('3-6')
const customText = ref(CUSTOM_STARTER)
const customError = ref<string | null>(null)
const syncing = ref(false)

const templateOptions = computed(() => [
  { value: 'off' as const, label: t('domains.tricks.off'), icon: 'pi pi-minus-circle', hint: t('domains.tricks.offHint') },
  { value: 'tls_fragment' as const, label: t('domains.tricks.tlsFragment.name'), icon: 'pi pi-objects-column', hint: t('domains.tricks.tlsFragment.hint') },
  { value: 'custom' as const, label: t('domains.tricks.custom.name'), icon: 'pi pi-code', hint: t('domains.tricks.custom.hint') },
])

const packetsOptions = [
  { label: 'tlshello', value: 'tlshello' },
  { label: '1-3', value: '1-3' },
]

const activePresetId = computed(() => {
  if (template.value !== 'tls_fragment') return null
  const norm = (s: string) =>
    s
      .split(/[,;]+/)
      .map((p) => p.trim())
      .filter(Boolean)
      .join(',')
  return (
    PRESETS.find(
      (p) =>
        p.packets === packets.value &&
        norm(p.lengths) === norm(lengths.value) &&
        norm(p.delays) === norm(delays.value) &&
        p.maxSplit === maxSplit.value.trim(),
    )?.id ?? null
  )
})

function parseExtra(): Record<string, unknown> {
  try {
    const parsed = JSON.parse(extraText.value.trim() || '{}')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return { ...parsed }
  } catch {
    /* ignore */
  }
  return {}
}

function listJoin(values: string[]): string {
  return values.join(', ')
}

function listSplit(text: string): string[] {
  return text
    .split(/[,;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function applyPreset(p: FragPreset) {
  template.value = 'tls_fragment'
  packets.value = p.packets
  lengths.value = p.lengths
  delays.value = p.delays
  maxSplit.value = p.maxSplit
}

function parseCustomFinalmask(text: string): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  try {
    const parsed = JSON.parse(text.trim() || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { ok: false, error: t('domains.tricks.custom.mustObject') }
    }
    return { ok: true, value: parsed as Record<string, unknown> }
  } catch {
    return { ok: false, error: t('domains.tricks.custom.invalidJson') }
  }
}

function loadFromExtra() {
  syncing.value = true
  try {
    const obj = parseExtra()
    const kind = trickTemplateOf(obj)
    template.value = kind
    customError.value = null
    if (kind === 'tls_fragment') {
      const settings = fragmentSettingsOf(obj)
      packets.value = settings?.packets || 'tlshello'
      lengths.value = listJoin(settings?.lengths || ['10-100'])
      delays.value = listJoin(settings?.delays || ['50-200'])
      maxSplit.value = settings?.maxSplit || '3-6'
      const fm = finalmaskOf(obj)
      customText.value = fm ? JSON.stringify(fm, null, 2) : CUSTOM_STARTER
    } else if (kind === 'custom') {
      const fm = finalmaskOf(obj)
      customText.value = fm ? JSON.stringify(fm, null, 2) : CUSTOM_STARTER
    } else {
      packets.value = 'tlshello'
      lengths.value = '10-100'
      delays.value = '50-200'
      maxSplit.value = '3-6'
      customText.value = CUSTOM_STARTER
    }
  } finally {
    syncing.value = false
  }
}

function writeToExtra() {
  if (syncing.value || !props.enabled) return
  const obj = parseExtra()
  let nextObj: Record<string, unknown>

  if (template.value === 'off') {
    customError.value = null
    nextObj = setTlsFragmentInExtra(obj, null)
  } else if (template.value === 'tls_fragment') {
    customError.value = null
    nextObj = setTlsFragmentInExtra(obj, {
      mode: 'on' satisfies TlsFragmentMode,
      packets: packets.value.trim() || 'tlshello',
      lengths: listSplit(lengths.value),
      delays: listSplit(delays.value),
      maxSplit: maxSplit.value.trim() || '3-6',
    })
    const fm = finalmaskOf(nextObj)
    if (fm) customText.value = JSON.stringify(fm, null, 2)
  } else {
    const parsed = parseCustomFinalmask(customText.value)
    if (!parsed.ok) {
      customError.value = parsed.error
      return
    }
    customError.value = null
    nextObj = setCustomFinalmaskInExtra(obj, parsed.value)
  }

  const next = JSON.stringify(nextObj, null, 2)
  if (next === extraText.value) return
  syncing.value = true
  extraText.value = next
  queueMicrotask(() => {
    syncing.value = false
  })
}

watch(
  () => props.enabled,
  (on) => {
    if (on) loadFromExtra()
  },
  { immediate: true },
)
watch(extraText, () => {
  if (!syncing.value && props.enabled) loadFromExtra()
})
watch([template, packets, lengths, delays, maxSplit], () => writeToExtra())
watch(customText, () => {
  if (template.value === 'custom') writeToExtra()
})
</script>

<template>
  <section v-if="enabled" class="tricks">
    <header class="tricks__head">
      <span class="tricks__badge"><i class="pi pi-sparkles" /></span>
      <div class="tricks__titles">
        <h3 class="tricks__title">{{ t('domains.tricks.title') }}</h3>
        <p class="tricks__lead">{{ t('domains.tricks.lead') }}</p>
      </div>
      <a class="tricks__docs" href="https://xtls.github.io/en/config/transports/finalmask.html" target="_blank" rel="noopener">
        {{ t('domains.tricks.docs') }}
        <i class="pi pi-external-link" />
      </a>
    </header>

    <div class="tricks__picker" role="list">
      <button
        v-for="opt in templateOptions"
        :key="opt.value"
        type="button"
        class="tricks__card"
        :class="{ 'tricks__card--on': template === opt.value, 'tricks__card--off': opt.value === 'off' }"
        role="listitem"
        :aria-pressed="template === opt.value"
        @click="template = opt.value"
      >
        <span class="tricks__card-ico"><i :class="opt.icon" /></span>
        <span class="tricks__card-text">
          <b>{{ opt.label }}</b>
          <small>{{ opt.hint }}</small>
        </span>
        <span v-if="template === opt.value" class="tricks__check"><i class="pi pi-check" /></span>
      </button>
    </div>

    <div v-if="template === 'tls_fragment'" class="tricks__editor">
      <div class="tricks__editor-head">
        <b>{{ t('domains.tricks.tlsFragment.tune') }}</b>
        <small>{{ t('domains.tricks.tlsFragment.tuneHint') }}</small>
      </div>

      <div class="tricks__presets" role="list">
        <button
          v-for="p in PRESETS"
          :key="p.id"
          type="button"
          class="tricks__chip"
          :class="{ 'tricks__chip--on': activePresetId === p.id }"
          role="listitem"
          @click="applyPreset(p)"
        >
          {{ t(`domains.tricks.presets.${p.id}`) }}
        </button>
      </div>

      <div class="tricks__fields">
        <label class="tricks__field">
          <span class="tricks__label">{{ t('domains.tricks.tlsFragment.packets') }}</span>
          <SelectButton v-model="packets" :options="packetsOptions" option-label="label" option-value="value" :allow-empty="false" class="tricks__packets" />
          <small class="tricks__hint">{{ t('domains.tricks.tlsFragment.packetsHint') }}</small>
        </label>

        <label class="tricks__field">
          <span class="tricks__label">{{ t('domains.tricks.tlsFragment.lengths') }}</span>
          <InputText v-model="lengths" dir="ltr" placeholder="10-100" fluid class="tricks__ltr" />
          <small class="tricks__hint">{{ t('domains.tricks.tlsFragment.lengthsHint') }}</small>
        </label>

        <label class="tricks__field">
          <span class="tricks__label">{{ t('domains.tricks.tlsFragment.delays') }}</span>
          <InputText v-model="delays" dir="ltr" placeholder="50-200" fluid class="tricks__ltr" />
          <small class="tricks__hint">{{ t('domains.tricks.tlsFragment.delaysHint') }}</small>
        </label>

        <label class="tricks__field">
          <span class="tricks__label">{{ t('domains.tricks.tlsFragment.maxSplit') }}</span>
          <InputText v-model="maxSplit" dir="ltr" placeholder="3-6" fluid class="tricks__ltr" />
          <small class="tricks__hint">{{ t('domains.tricks.tlsFragment.maxSplitHint') }}</small>
        </label>
      </div>

      <div class="tricks__preview" dir="ltr">
        <span class="tricks__preview-label">{{ t('domains.tricks.preview') }}</span>
        <code>{{ `finalmask.tcp → fragment · ${packets} · ${lengths} · ${delays} · maxSplit ${maxSplit}` }}</code>
      </div>
    </div>

    <div v-else-if="template === 'custom'" class="tricks__editor">
      <div class="tricks__editor-head">
        <b>{{ t('domains.tricks.custom.tune') }}</b>
        <small>{{ t('domains.tricks.custom.tuneHint') }}</small>
      </div>
      <Json5Editor v-model="customText" height="180px" />
      <small v-if="customError" class="tricks__err">{{ customError }}</small>
    </div>
  </section>
</template>

<style scoped>
.tricks {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1rem;
  border-radius: 1rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 22%, var(--p-content-border-color));
  background:
    radial-gradient(120% 80% at 100% 0%, color-mix(in srgb, var(--p-primary-color) 12%, transparent), transparent 55%),
    var(--p-content-background);
}
.tricks__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.75rem;
}
.tricks__badge {
  inline-size: 2.4rem;
  block-size: 2.4rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 16%, transparent);
}
.tricks__titles {
  flex: 1;
  min-width: 10rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.tricks__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}
.tricks__lead {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}
.tricks__docs {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.tricks__docs:hover {
  background: color-mix(in srgb, var(--p-primary-color) 18%, transparent);
}
.tricks__docs .pi {
  font-size: 0.7rem;
}
.tricks__picker {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}
.tricks__card {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.7rem 0.75rem;
  border-radius: 0.85rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}
.tricks__card:hover {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  transform: translateY(-1px);
}
.tricks__card--on {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, var(--p-content-border-color));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--p-primary-color) 25%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 7%, var(--p-content-background));
}
.tricks__card--off.tricks__card--on {
  border-color: color-mix(in srgb, var(--p-text-muted-color) 35%, var(--p-content-border-color));
  box-shadow: none;
  background: color-mix(in srgb, var(--p-text-muted-color) 6%, var(--p-content-background));
}
.tricks__card-ico {
  inline-size: 1.85rem;
  block-size: 1.85rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.55rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  font-size: 0.85rem;
}
.tricks__card--off .tricks__card-ico {
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-text-muted-color) 12%, transparent);
}
.tricks__card-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.tricks__card-text b {
  font-size: 0.82rem;
  font-weight: 700;
}
.tricks__card-text small {
  font-size: 0.68rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.tricks__check {
  flex: none;
  color: var(--p-primary-color);
  font-size: 0.85rem;
  margin-top: 0.15rem;
}
.tricks__editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.85rem 0.9rem;
  border-radius: 0.85rem;
  border: 1px dashed color-mix(in srgb, var(--p-primary-color) 30%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-content-background) 70%, transparent);
}
.tricks__editor-head {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.tricks__editor-head b {
  font-size: 0.88rem;
}
.tricks__editor-head small {
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}
.tricks__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.tricks__chip {
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: inherit;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}
.tricks__chip:hover {
  border-color: color-mix(in srgb, var(--p-primary-color) 40%, var(--p-content-border-color));
}
.tricks__chip--on {
  border-color: transparent;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
}
.tricks__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 0.9rem;
}
.tricks__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.tricks__label {
  font-size: 0.8rem;
  font-weight: 600;
}
.tricks__hint {
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.tricks__err {
  font-size: 0.78rem;
  color: var(--p-red-500);
}
.tricks__ltr :deep(input) {
  direction: ltr;
  text-align: start;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
}
.tricks__packets {
  width: 100%;
}
.tricks__packets :deep(.p-togglebutton) {
  flex: 1;
}
.tricks__preview {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.55rem 0.7rem;
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--p-surface-ground, var(--p-content-background)) 80%, #000 4%);
}
.tricks__preview-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}
.tricks__preview code {
  font-size: 0.72rem;
  line-height: 1.4;
  word-break: break-word;
  color: var(--p-text-color);
}
@media (max-width: 720px) {
  .tricks__picker {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 560px) {
  .tricks__fields {
    grid-template-columns: minmax(0, 1fr);
  }
  .tricks__docs {
    width: 100%;
    justify-content: center;
  }
}
</style>
