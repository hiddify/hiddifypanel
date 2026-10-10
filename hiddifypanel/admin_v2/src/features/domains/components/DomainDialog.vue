<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import Json5Editor from '@/shared/components/Json5Editor.vue'
import { apiErrorMessage } from '@/core/api/client'
import KindPicker from '@/features/domains/components/KindPicker.vue'
import TlsPicker from '@/features/domains/components/TlsPicker.vue'
import PortField from '@/features/domains/components/PortField.vue'
import ProxyPicker from '@/features/domains/components/ProxyPicker.vue'
import {
  KIND_META,
  KINDS,
  domainsApi,
  isFakeProxyMode,
  kindOf,
  tlsModeSelectable,
  type DomainKind,
  type DomainMode,
  type DomainPayload,
  type DomainRow,
  type DomainsOptions,
  type DomainsState,
  type TlsMode,
} from '@/features/domains/api'

const props = defineProps<{ row: DomainRow | null; state: DomainsState | null; options: DomainsOptions | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [state: DomainsState, row: DomainRow] }>()

const { t } = useI18n()

const domain = ref('')
const alias = ref('')
const mode = ref<DomainMode>('direct')
const fakeMode = ref<TlsMode>('valid')
const proxyIds = ref<number[]>([])
const choosingL7 = ref(false)
const showIds = ref<number[]>([])
const serverDomainId = ref<number | null>(null)
const downloadDomainId = ref<number | null>(null)
const cdnIp = ref('')
const resolveIp = ref(false)
const ech = ref(false)
const servernames = ref('')
const extraText = ref('{}')
const tlsPort = ref<number | null>(null)
const httpPort = ref<number | null>(null)
const tlsPortOk = ref(true)
const httpPortOk = ref(true)
const showAdvanced = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)

const meta = computed(() => props.state?.meta)
const others = computed(() => (props.state?.domains ?? []).filter((d) => d.id !== props.row?.id))

watch(visible, (open) => {
  if (!open || !props.row) return
  const r = props.row
  domain.value = r.domain
  alias.value = r.alias
  mode.value = r.mode
  fakeMode.value = r.fake_mode
  proxyIds.value = [...r.custom_proxy_ids]
  choosingL7.value = false
  showIds.value = [...r.show_domain_ids]
  serverDomainId.value = r.server_domain_id
  downloadDomainId.value = r.download_domain_id
  cdnIp.value = r.cdn_ip
  resolveIp.value = r.resolve_ip
  ech.value = r.ech
  servernames.value = r.servernames
  extraText.value = r.extra_params || '{}'
  tlsPort.value = r.tls_port
  httpPort.value = r.http_port
  error.value = null
  busy.value = false
  // Open Advanced right away when something in it is set.
  showAdvanced.value = !!((r.mode === 'cdn' && r.servernames) || r.tls_port || r.http_port || r.server_domain_id || r.download_domain_id || (r.cdn_ip && r.fake_mode === 'valid') || r.resolve_ip || r.ech || (r.extra_params && r.extra_params !== '{}'))
})

const kind = computed<DomainKind>({
  get: () => kindOf(mode.value),
  set: (k) => {
    mode.value = KIND_META[k].mode
    // CDN, worker and subscription domains always use a real certificate.
    if (!tlsModeSelectable(mode.value)) fakeMode.value = 'valid'
  },
})
const isSublink = computed(() => mode.value === 'sub_link_only')
const isCdn = computed(() => mode.value === 'cdn')
const isReality = computed(() => fakeMode.value === 'reality')
/** Telegram / ShadowTLS / SS FakeTLS front domain: like Reality, but no custom proxies and no download domain. */
const isFakeProxy = computed(() => isFakeProxyMode(fakeMode.value))
const takenFakeModes = computed(() => others.value.map((d) => d.fake_mode).filter(isFakeProxyMode))
// Until the options arrive every proxy is offered, so nothing is dropped from the selection.
const compatibleIds = computed(() => (props.options ? (props.options.compatible[`${mode.value}:${fakeMode.value}`] ?? []) : (meta.value?.proxies ?? []).map((p) => p.id)))
// Another mode: drop the proxies that do not fit it (the server would drop them too).
watch(compatibleIds, (ids) => {
  if (visible.value) proxyIds.value = proxyIds.value.filter((id) => ids.includes(id))
})

/** Whose configs this domain shows: sub-link domains, or any real-certificate domain while there is no sub-link domain. */
const showDomainsAllowed = computed(() => isSublink.value || (!meta.value?.has_sublink && fakeMode.value === 'valid'))
/** Like the classic page: `Node[name] alias [domain] mode(tls)` for nodes' domains. */
const showOptions = computed(() =>
  (props.options?.show_options ?? []).map((d) => {
    const name = d.alias && d.alias !== d.domain ? `${d.alias} [${d.domain || t('domains.noName')}]` : d.domain || t('domains.noName')
    const kind = `${t(`domains.kind.${kindOf(d.mode)}.name`)} (${t(`domains.tlsMode.${d.fake_mode}`)})`
    return { id: d.id, label: `${d.node ? `Node[${d.node}] ` : ''}${name} ${kind}` }
  }),
)
const serverDomainOptions = computed(() =>
  others.value.filter((d) => (d.mode === 'direct' || d.mode === 'relay') && d.fake_mode === 'valid').map((d) => ({ id: d.id, label: d.domain })),
)
const downloadOptions = computed(() => others.value.filter((d) => d.mode !== 'sub_link_only' && d.domain).map((d) => ({ id: d.id, label: d.domain })))

const extraError = computed(() => {
  const text = extraText.value.trim()
  if (!text) return null
  try {
    const v = JSON.parse(text)
    return v && typeof v === 'object' && !Array.isArray(v) ? null : t('domains.field.extraObject')
  } catch {
    return t('domains.field.extraInvalid')
  }
})
const domainError = computed(() => {
  const d = domain.value.trim()
  if (!d) return fakeMode.value === 'fake' ? null : t('domains.field.domainRequired')
  return /^(\*\.)?([A-Za-z0-9\-.]+\.[a-zA-Z]{2,})$|^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$/.test(d) ? null : t('domains.field.domainInvalid')
})
/** Comma / space separated host names (Reality server names or CDN fronting names). */
const cleanServernames = computed(() =>
  servernames.value
    .split(/[\s,;]+/)
    .map((v) => v.trim().toLowerCase())
    .filter(Boolean)
    .join(','),
)
const servernamesError = computed(() =>
  (isReality.value || isCdn.value) && cleanServernames.value.split(',').some((v) => v && !/^([\w-]+\.)+[\w-]+$/.test(v)) ? t('domains.field.hostnamesInvalid') : null,
)
// Reality server names and CDN fronting names mean different things: switching modes starts empty
// (going back restores what the domain had).
watch([mode, fakeMode], ([m, f]) => {
  if (!visible.value || !props.row) return
  servernames.value = m === props.row.mode && f === props.row.fake_mode ? props.row.servernames : ''
})
const relayNeedsIp = computed(() => mode.value === 'relay' && fakeMode.value !== 'valid' && !cdnIp.value.trim())
const canSave = computed(() => !busy.value && !servernamesError.value && !domainError.value && !extraError.value && (isSublink.value || (tlsPortOk.value && httpPortOk.value)) && !relayNeedsIp.value)

async function save() {
  if (!props.row || !canSave.value) {
    if (extraError.value) showAdvanced.value = true
    return
  }
  busy.value = true
  error.value = null
  const payload: DomainPayload = {
    domain: domain.value.trim().toLowerCase(),
    alias: alias.value.trim(),
    mode: mode.value,
    fake_mode: fakeMode.value,
    custom_proxy_ids: isFakeProxy.value ? [] : proxyIds.value,
    show_domain_ids: showDomainsAllowed.value ? showIds.value : [],
    server_domain_id: serverDomainId.value,
    download_domain_id: isFakeProxy.value ? null : downloadDomainId.value,
    // Subscription-only domains run no proxies: no forced IPs, resolve IP or gateway ports.
    cdn_ip: isSublink.value ? '' : cdnIp.value.trim(),
    resolve_ip: !isSublink.value && resolveIp.value,
    ech: isCdn.value && ech.value,
    // Reality: the sites it borrows; CDN: domain fronting names. Other modes keep what they had.
    servernames: isReality.value || isCdn.value ? cleanServernames.value : props.row.servernames,
    extra_params: extraText.value.trim() || '{}',
    tls_port: isSublink.value ? null : tlsPort.value,
    http_port: isSublink.value ? null : httpPort.value,
  }
  try {
    const next = await domainsApi.update(props.row.id, payload)
    const saved = next.domains.find((d) => d.id === props.row!.id) ?? props.row
    emit('saved', next, saved)
    visible.value = false
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" class="dd" :style="{ width: 'min(46rem, calc(100vw - 1.5rem))' }" :breakpoints="{ '640px': '100vw' }">
    <template #header>
      <div class="dd__head">
        <span class="dd__emoji" :style="{ '--kind-color': KIND_META[kind].color }">{{ KIND_META[kind].emoji }}</span>
        <div class="dd__head-text">
          <span class="dd__title">{{ t('domains.editTitle') }}</span>
          <span class="dd__sub" dir="ltr">{{ row?.domain || t('domains.noName') }}</span>
        </div>
      </div>
    </template>

    <form v-if="row" class="dd__form" @submit.prevent="save">
      <div class="dd__grid">
        <label class="dd__field">
          <span class="dd__label">{{ t('domains.field.domain') }}</span>
          <InputText v-model="domain" dir="ltr" autocomplete="off" spellcheck="false" :invalid="!!domainError" fluid />
          <small v-if="domainError" class="dd__err">{{ domainError }}</small>
        </label>
        <label class="dd__field">
          <span class="dd__label">{{ t('domains.field.alias') }}</span>
          <InputText v-model="alias" :placeholder="domain" fluid />
          <small class="dd__hint">{{ t('domains.field.aliasHint') }}</small>
        </label>
      </div>

      <section class="dd__section">
        <h3 class="dd__h">{{ t('domains.field.mode') }}</h3>
        <KindPicker v-model="kind" :kinds="row.mode === 'worker' ? [...KINDS, 'worker'] : KINDS" compact />
        <p class="dd__kind-desc">
          {{ t(`domains.kind.${kind}.desc`) }}
          <a v-if="KIND_META[kind].link" :href="KIND_META[kind].link" target="_blank" rel="noopener" class="dd__more">{{ t('domains.readMore') }} <i class="pi pi-external-link" /></a>
        </p>
      </section>

      <section class="dd__section">
        <h3 class="dd__h">{{ t('domains.field.tlsMode') }}</h3>
        <TlsPicker v-model="fakeMode" :locked="!tlsModeSelectable(mode)" :taken="takenFakeModes" />
        <Message v-if="isFakeProxy" severity="info" size="small" :closable="false">{{ t('domains.tlsMode.fakeProxyNote') }}</Message>
        <Message v-if="relayNeedsIp" severity="warn" size="small" :closable="false">{{ t('domains.field.relayNeedsIp') }}</Message>
      </section>

      <section v-if="isReality" class="dd__section">
        <label class="dd__field">
          <span class="dd__label">{{ t('domains.field.servernames') }}</span>
          <InputText v-model="servernames" dir="ltr" :placeholder="domain" fluid />
          <small class="dd__hint">{{ t('domains.field.servernamesHint') }}</small>
        </label>
      </section>

      <section v-if="!isSublink && !isFakeProxy" class="dd__section">
        <h3 class="dd__h">{{ t('domains.field.proxies') }}</h3>
        <ProxyPicker v-model="proxyIds" v-model:choosing="choosingL7" :proxies="meta?.proxies ?? []" :compatible-ids="compatibleIds" :reality="isReality" />
      </section>

      <section v-if="showDomainsAllowed" class="dd__section">
        <h3 class="dd__h">{{ t('domains.field.showDomains') }}</h3>
        <MultiSelect
          v-model="showIds"
          :options="showOptions"
          option-label="label"
          option-value="id"
          display="chip"
          filter
          :placeholder="t('domains.field.showAll')"
          :max-selected-labels="4"
          class="dd__ltr"
          fluid
        />
        <small class="dd__hint">{{ t('domains.field.showDomainsHint') }}</small>
      </section>

      <button type="button" class="dd__adv-toggle" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
        <i class="pi pi-sliders-h" />
        <span>{{ t('domains.advanced') }}</span>
        <i class="pi dd__chev" :class="showAdvanced ? 'pi-chevron-up' : 'pi-chevron-down'" />
      </button>

      <div v-show="showAdvanced" class="dd__adv">
        <section v-if="isCdn" class="dd__section">
          <label class="dd__field">
            <span class="dd__label">{{ t('domains.field.fronting') }}</span>
            <InputText v-model="servernames" dir="ltr" spellcheck="false" autocomplete="off" :placeholder="t('domains.field.frontingPlaceholder')" :invalid="!!servernamesError" fluid />
            <small v-if="servernamesError" class="dd__err">{{ servernamesError }}</small>
            <small class="dd__hint">{{ t('domains.field.frontingHint') }}</small>
          </label>
        </section>

        <section v-if="!isSublink" class="dd__section">
          <h3 class="dd__h">{{ t('domains.field.ports') }}</h3>
          <p class="dd__hint dd__hint--top">{{ t('domains.field.portsHint') }}</p>
          <div class="dd__ports">
            <PortField v-model="tlsPort" v-model:valid="tlsPortOk" kind="tls" :default-port="meta?.default_tls_port ?? 443" :domain-id="row.id" input-id="dd-tls-port" />
            <PortField v-model="httpPort" v-model:valid="httpPortOk" kind="http" :default-port="meta?.default_http_port ?? 80" :domain-id="row.id" input-id="dd-http-port" />
          </div>
        </section>

        <div class="dd__grid">
          <label v-if="!isSublink" class="dd__field">
            <span class="dd__label">{{ t('domains.field.serverDomain') }}</span>
            <Select v-model="serverDomainId" :options="serverDomainOptions" option-label="label" option-value="id" show-clear :placeholder="t('domains.field.none')" class="dd__ltr" fluid />
            <small class="dd__hint">{{ t('domains.field.serverDomainHint') }}</small>
          </label>
          <label v-if="!isSublink && !isFakeProxy" class="dd__field">
            <span class="dd__label">{{ t('domains.field.downloadDomain') }}</span>
            <Select v-model="downloadDomainId" :options="downloadOptions" option-label="label" option-value="id" show-clear filter :placeholder="t('domains.field.none')" class="dd__ltr" fluid />
            <small class="dd__hint">{{ t('domains.field.downloadDomainHint') }}</small>
          </label>
        </div>

        <label v-if="!isSublink" class="dd__field">
          <span class="dd__label">{{ t('domains.field.cdnIp') }}</span>
          <Textarea v-model="cdnIp" dir="ltr" rows="2" auto-resize spellcheck="false" :invalid="relayNeedsIp" fluid />
          <small class="dd__hint">{{ t('domains.field.cdnIpHint') }}</small>
        </label>

        <div v-if="!isSublink" class="dd__toggles">
          <label class="dd__toggle">
            <ToggleSwitch v-model="resolveIp" />
            <span>
              <b>{{ t('domains.field.resolveIp') }}</b>
              <small>{{ t('domains.field.resolveIpHint') }}</small>
            </span>
          </label>
          <label v-if="isCdn" class="dd__toggle" :class="{ 'dd__toggle--off': !meta?.ech_enabled }">
            <ToggleSwitch v-model="ech" :disabled="!meta?.ech_enabled && !ech" />
            <span>
              <b>{{ t('domains.field.ech') }}</b>
              <small>{{ meta?.ech_enabled ? t('domains.field.echHint') : t('domains.field.echNeedsSetting') }}</small>
            </span>
          </label>
        </div>

        <section class="dd__section">
          <h3 class="dd__h">{{ t('domains.field.extra') }}</h3>
          <Json5Editor v-model="extraText" height="120px" />
          <small v-if="extraError" class="dd__err">{{ extraError }}</small>
        </section>
      </div>

      <Message v-if="error" severity="error" :closable="false" class="dd__error">{{ error }}</Message>
      <button type="submit" hidden />
    </form>

    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" text @click="visible = false" />
      <Button :label="t('common.save')" icon="pi pi-check" :loading="busy" :disabled="!canSave" @click="save" />
    </template>
  </Dialog>
</template>

<style scoped>
.dd__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.dd__emoji {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.3rem;
  background: color-mix(in srgb, var(--kind-color) 15%, transparent);
}
.dd__head-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.dd__title {
  font-weight: 700;
  font-size: 1.1rem;
}
.dd__sub {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.dd__form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}
.dd__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}
.dd__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.dd__label,
.dd__h {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
}
.dd__section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dd__kind-desc,
.dd__hint {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}
.dd__more {
  color: var(--p-primary-color);
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.dd__more i {
  font-size: 0.65rem;
}
.dd__hint--top {
  margin-top: -0.25rem;
}
.dd__err {
  font-size: 0.78rem;
  color: var(--p-red-500, #ef4444);
}
.dd__tls {
  flex-wrap: wrap;
}
.dd__ltr :deep(.p-select-label),
.dd__ltr :deep(.p-multiselect-label) {
  direction: ltr;
  text-align: start;
}
.dd__adv-toggle {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  padding: 0.7rem 0.9rem;
  border-radius: 12px;
  border: 1px dashed var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}
.dd__adv-toggle:hover {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
.dd__chev {
  margin-inline-start: auto;
  font-size: 0.8rem;
}
.dd__adv {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 0.25rem 0.1rem 0;
}
.dd__ports {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem 1rem;
}
@media (max-width: 520px) {
  .dd__ports {
    grid-template-columns: minmax(0, 1fr);
  }
}
.dd__toggles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 0.6rem;
}
.dd__toggle {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.7rem 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
}
.dd__toggle span {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.dd__toggle b {
  font-size: 0.86rem;
  font-weight: 600;
}
.dd__toggle small {
  font-size: 0.76rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.dd__toggle--off b {
  opacity: 0.6;
}
@media (max-width: 640px) {
  .dd__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
