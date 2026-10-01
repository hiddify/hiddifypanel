<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { apiErrorMessage } from '@/core/api/client'
import { CONFIGURABLE_ENDPOINT_MODES, MODE_ICON, outboundsApi, type Outbound, type OutboundLists, type OutboundMode, type OutboundPayload, type OutboundsState } from '@/features/outbounds/api'

/** `outbound`: the one being edited; null adds a new one of `mode`. */
const props = defineProps<{ outbound: Outbound | null; mode: OutboundMode; state: OutboundsState | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [state: OutboundsState, name: string] }>()

const { t } = useI18n()

type ListField = keyof OutboundLists
const LIST_FIELDS: { key: ListField; icon: string }[] = [
  { key: 'sites', icon: 'pi pi-globe' },
  { key: 'geosites', icon: 'pi pi-map' },
  { key: 'rule_sets', icon: 'pi pi-list-check' },
]

const name = ref('')
const domestic = ref(false)
const lists = ref<Record<ListField, string>>({ sites: '', geosites: '', rule_sets: '' })
const host = ref('')
const port = ref<number | null>(null)
const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref<string | null>(null)
const touched = ref(false)

const editing = computed(() => props.outbound !== null)
const currentMode = computed<OutboundMode>(() => props.outbound?.mode ?? props.mode)
const needsEndpoint = computed(() => CONFIGURABLE_ENDPOINT_MODES.includes(currentMode.value))
/** Tor / Psiphon: fixed local port on the server, shown read only. */
const fixedEndpoint = computed(() => {
  if (currentMode.value !== 'tor' && currentMode.value !== 'psiphon') return null
  const e = endpointDefaults.value
  return e.host && e.port ? `${e.host}:${e.port}` : null
})
const endpointDefaults = computed(() => props.state?.endpoints[currentMode.value] ?? {})

function toLines(values: string[]): string {
  return values.join('\n')
}
function fromLines(text: string): string[] {
  return text
    .split(/[\n,]+/)
    .map((v) => v.trim())
    .filter(Boolean)
}
function countOf(key: ListField): number {
  return fromLines(lists.value[key]).length
}

watch(visible, (open) => {
  if (!open) return
  const o = props.outbound
  error.value = null
  touched.value = false
  busy.value = false
  name.value = o?.name ?? t(`outbounds.mode.${props.mode}`)
  domestic.value = o?.domestic ?? false
  lists.value = { sites: toLines(o?.sites ?? []), geosites: toLines(o?.geosites ?? []), rule_sets: toLines(o?.rule_sets ?? []) }
  host.value = o?.host || endpointDefaults.value.host || ''
  port.value = o?.port ?? endpointDefaults.value.port ?? null
  username.value = o?.username ?? ''
  password.value = ''
})

const regionDomestic = computed(() => props.state?.domestic)
const domesticPreview = computed(() => {
  const d = regionDomestic.value
  if (!d) return ''
  // Rule-sets are URLs: their file names are enough here.
  const files = d.rule_sets.map((url) => url.split('/').pop() ?? url)
  return [...d.sites.map((s) => `.${s}`), ...d.geosites, ...files].join(' · ')
})
const nameError = computed(() => touched.value && !name.value.trim())

async function submit() {
  touched.value = true
  if (!name.value.trim() || busy.value) return
  busy.value = true
  error.value = null
  const payload: OutboundPayload = {
    name: name.value.trim(),
    domestic: domestic.value,
    sites: fromLines(lists.value.sites),
    geosites: fromLines(lists.value.geosites),
    rule_sets: fromLines(lists.value.rule_sets),
  }
  if (needsEndpoint.value) {
    payload.host = host.value.trim()
    payload.port = port.value
    payload.username = username.value.trim()
    if (password.value) payload.password = password.value
  }
  try {
    const state = props.outbound ? await outboundsApi.update(props.outbound.id, payload) : await outboundsApi.create({ ...payload, mode: props.mode })
    emit('saved', state, payload.name!)
    visible.value = false
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="!busy"
    :style="{ width: 'min(46rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <template #header>
      <div class="ob-dlg__title">
        <span class="ob-dlg__icon" :class="`ob-tone--${currentMode}`"><i :class="MODE_ICON[currentMode]" /></span>
        <div class="min-w-0">
          <div class="font-semibold text-lg">{{ editing ? t('outbounds.dialog.editTitle', { name: outbound?.name }) : t('outbounds.dialog.addTitle', { mode: t(`outbounds.mode.${mode}`) }) }}</div>
          <div class="text-muted-color text-sm">{{ t(`outbounds.modeHint.${currentMode}`) }}</div>
        </div>
      </div>
    </template>

    <form class="ob-dlg" @submit.prevent="submit">
      <div class="ob-dlg__field">
        <label for="ob-name" class="font-medium">{{ t('outbounds.dialog.name') }}</label>
        <InputText id="ob-name" v-model="name" maxlength="100" :invalid="nameError" :disabled="busy" autofocus />
        <small v-if="nameError" class="ob-dlg__error">{{ t('outbounds.dialog.nameRequired') }}</small>
      </div>

      <!-- Tor / Psiphon: nothing to set, just where it connects -->
      <Message v-if="fixedEndpoint" severity="secondary" :closable="false" size="small" icon="pi pi-server">
        {{ t(`outbounds.dialog.endpointHint.${currentMode}`, { endpoint: fixedEndpoint }) }}
      </Message>

      <!-- SOCKS endpoint -->
      <section v-if="needsEndpoint" class="ob-dlg__section">
        <h4 class="ob-dlg__heading"><i class="pi pi-server" />{{ t('outbounds.dialog.endpoint') }}</h4>
        <div class="ob-dlg__grid">
          <div class="ob-dlg__field ob-dlg__field--wide">
            <label for="ob-host" class="font-medium">{{ t('outbounds.dialog.host') }}</label>
            <InputText id="ob-host" v-model="host" dir="ltr" :disabled="busy" :placeholder="endpointDefaults.host" />
          </div>
          <div class="ob-dlg__field">
            <label for="ob-port" class="font-medium">{{ t('outbounds.dialog.port') }}</label>
            <InputNumber v-model="port" input-id="ob-port" :min="1" :max="65535" :use-grouping="false" :disabled="busy" fluid />
          </div>
          <div class="ob-dlg__field">
            <label for="ob-user" class="font-medium">{{ t('outbounds.dialog.username') }} <span class="text-muted-color font-normal">({{ t('outbounds.dialog.optional') }})</span></label>
            <InputText id="ob-user" v-model="username" dir="ltr" autocomplete="off" :disabled="busy" />
          </div>
          <div class="ob-dlg__field">
            <label for="ob-pass" class="font-medium">{{ t('outbounds.dialog.password') }}</label>
            <Password
              v-model="password"
              input-id="ob-pass"
              :feedback="false"
              toggle-mask
              fluid
              :disabled="busy"
              :placeholder="outbound?.has_password ? t('outbounds.dialog.passwordKeep') : ''"
              :input-props="{ autocomplete: 'new-password' }"
            />
          </div>
        </div>
      </section>

      <!-- What goes through this outbound -->
      <section class="ob-dlg__section">
        <h4 class="ob-dlg__heading"><i class="pi pi-directions" />{{ t('outbounds.dialog.routes') }}</h4>
        <p class="ob-dlg__hint">{{ outbound?.is_default ? t('outbounds.dialog.routesHintDefault') : t('outbounds.dialog.routesHint') }}</p>

        <label class="ob-dlg__switch" for="ob-domestic">
          <span class="flex flex-col gap-1 min-w-0">
            <span class="font-medium">{{ t('outbounds.dialog.domestic', { region: t(`outbounds.region.${state?.region || 'other'}`) }) }}</span>
            <small class="text-muted-color ob-dlg__preview" dir="ltr">{{ domesticPreview }}</small>
          </span>
          <ToggleSwitch v-model="domestic" input-id="ob-domestic" :disabled="busy" />
        </label>

        <div class="ob-dlg__lists">
          <div v-for="field in LIST_FIELDS" :key="field.key" class="ob-dlg__field" :class="{ 'ob-dlg__field--full': field.key === 'rule_sets' }">
            <label :for="`ob-${field.key}`" class="ob-dlg__list-label">
              <i :class="field.icon" />
              <span>{{ t(`outbounds.list.${field.key}`) }}</span>
              <span class="ob-dlg__count">{{ countOf(field.key) }}</span>
            </label>
            <Textarea
              :id="`ob-${field.key}`"
              v-model="lists[field.key]"
              rows="5"
              dir="ltr"
              class="ob-dlg__textarea"
              spellcheck="false"
              :disabled="busy"
              :placeholder="t(`outbounds.list.${field.key}Placeholder`)"
            />
            <small class="text-muted-color">
              {{ t(`outbounds.list.${field.key}Hint`) }}
              <a v-if="field.key === 'rule_sets'" href="https://github.com/SagerNet/sing-geosite/tree/rule-set" target="_blank" rel="noopener">{{ t('outbounds.list.browse') }}</a>
            </small>
          </div>
        </div>
      </section>

      <Message v-if="error" severity="error" :closable="false"><span class="whitespace-pre-line">{{ error }}</span></Message>

      <div class="flex flex-wrap justify-end gap-2">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button type="submit" :icon="editing ? 'pi pi-check' : 'pi pi-plus'" :label="editing ? t('common.save') : t('outbounds.dialog.add')" :loading="busy" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.ob-dlg__title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.ob-dlg__icon {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.1rem;
  color: var(--ob-color);
  background: color-mix(in srgb, var(--ob-color) 14%, transparent);
}
.ob-dlg {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}
.ob-dlg__section {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--p-content-border-color);
}
.ob-dlg__heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.ob-dlg__heading i {
  color: var(--p-primary-color);
}
.ob-dlg__hint {
  margin: -0.35rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.ob-dlg__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.ob-dlg__grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 0.9rem;
}
.ob-dlg__error {
  color: var(--p-red-500, #ef4444);
}
.ob-dlg__switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0.9rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
}
.ob-dlg__preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.ob-dlg__lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}
/* Rule-set URLs are long: a full row */
.ob-dlg__field--full {
  grid-column: 1 / -1;
}
.ob-dlg__list-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 500;
  font-size: 0.9rem;
}
.ob-dlg__list-label i {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.ob-dlg__count {
  margin-inline-start: auto;
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.ob-dlg__textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  resize: vertical;
  min-height: 7.5rem;
}
@media (max-width: 760px) {
  .ob-dlg__lists {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .ob-dlg__grid {
    grid-template-columns: 1fr;
  }
}
</style>

<style>
/* Mode colors, shared with the outbounds page */
.ob-tone--warp {
  --ob-color: var(--p-orange-500, #f97316);
}
.ob-tone--direct {
  --ob-color: var(--p-green-500, #22c55e);
}
.ob-tone--block {
  --ob-color: var(--p-red-500, #ef4444);
}
.ob-tone--socks {
  --ob-color: var(--p-sky-500, #0ea5e9);
}
.ob-tone--tor {
  --ob-color: var(--p-violet-500, #8b5cf6);
}
.ob-tone--psiphon {
  --ob-color: var(--p-teal-500, #14b8a6);
}
</style>
