<script setup lang="ts">
/**
 * Add a domain step by step: the name → what the DNS says (detection, as in quick setup) → the mode →
 * the name shown in configs → saving, then waiting (at most a minute) for its real certificate.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { apiErrorMessage } from '@/core/api/client'
import CertProgress from '@/features/domains/components/CertProgress.vue'
import KindPicker from '@/features/domains/components/KindPicker.vue'
import TlsPicker from '@/features/domains/components/TlsPicker.vue'
import {
  KIND_META,
  KINDS,
  TLS_MODES,
  FAKE_PROXY_MODES,
  domainsApi,
  kindFitsDetection,
  suggestedSetup,
  tlsModeSelectable,
  type DomainDetection,
  type DomainKind,
  type TlsMode,
  type DomainRow,
  type DomainsState,
} from '@/features/domains/api'

const props = defineProps<{ state: DomainsState | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ added: [state: DomainsState, row: DomainRow]; edit: [row: DomainRow] }>()

const { t } = useI18n()

type Step = 'name' | 'mode' | 'alias' | 'saving' | 'cert' | 'done'
const STEPS: Step[] = ['name', 'mode', 'alias', 'cert']
const step = ref<Step>('name')
const name = ref('')
const detecting = ref(false)
const found = ref<DomainDetection | null>(null)
const kind = ref<DomainKind>('direct')
const tls = ref<TlsMode>('valid')
const alias = ref('')
const error = ref<string | null>(null)
const warnings = ref<string[]>([])
const created = ref<DomainRow | null>(null)
const certOk = ref<boolean | null>(null)
const nameBox = ref<HTMLElement | null>(null)

watch(visible, (open) => {
  if (!open) return
  step.value = 'name'
  name.value = ''
  found.value = null
  kind.value = 'direct'
  tls.value = 'valid'
  alias.value = ''
  error.value = null
  warnings.value = []
  created.value = null
  certOk.value = null
  void nextTick(() => nameBox.value?.querySelector('input')?.focus())
})

const stepIndex = computed(() => {
  const s = step.value === 'saving' ? 'alias' : step.value === 'done' ? 'cert' : step.value
  return STEPS.indexOf(s)
})

function normalize(raw: string): string {
  let v = raw.trim().toLowerCase()
  v = v.replace(/^[a-z]+:\/\//, '').split('/')[0]!.split('?')[0]!
  return v.replace(/:\d+$/, '').replace(/\.$/, '')
}
const cleanName = computed(() => normalize(name.value))
const nameError = computed(() => {
  if (!cleanName.value) return null
  return /^(\*\.)?([a-z0-9\-.]+\.[a-z]{2,})$/.test(cleanName.value) ? null : t('domains.field.domainInvalid')
})
const takenLocally = computed(() => (props.state?.domains ?? []).some((d) => d.domain === cleanName.value))

async function detect() {
  if (!cleanName.value || nameError.value || detecting.value) return
  error.value = null
  detecting.value = true
  try {
    found.value = await domainsApi.detect(cleanName.value)
    const suggested = suggestedSetup(found.value)
    kind.value = suggested.kind
    tls.value = suggested.tls
    step.value = 'mode'
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    detecting.value = false
  }
}

const tlsShown = computed(() => tlsModeSelectable(KIND_META[kind.value].mode))
/** The TLS mode that is saved: CDN, worker and subscription domains always use a real certificate. */
const tlsMode = computed<TlsMode>(() => (tlsShown.value ? tls.value : 'valid'))
/** Which TLS mode DNS suggests for this mode. */
const tlsFit = computed(() =>
  Object.fromEntries(TLS_MODES.map((m) => [m, kindFitsDetection(kind.value, m, found.value) === 'good' ? 'good' : kindFitsDetection(kind.value, m, found.value) === 'bad' ? 'bad' : undefined])) as Partial<Record<TlsMode, 'good' | 'bad'>>,
)
const fit = computed(() => Object.fromEntries(KINDS.map((k) => [k, kindFitsDetection(k, tlsModeSelectable(KIND_META[k].mode) ? tls.value : 'valid', found.value)])) as Record<DomainKind, 'good' | 'ok' | 'bad'>)
const decoy = computed(() => tlsMode.value !== 'valid')
/** Fake-proxy modes that already have a domain on this panel (one of each only). */
const takenFakeModes = computed(() => (props.state?.domains ?? []).map((d) => d.fake_mode).filter((m) => FAKE_PROXY_MODES.includes(m)))

/** What we found, in words. */
const finding = computed(() => {
  const f = found.value
  if (!f) return null
  if (f.mode === 'direct') return { icon: 'pi pi-server', tone: 'good', text: t('domains.wizard.found.direct', { ips: f.ips.join(', ') }) }
  if (f.mode === 'cdn') return { icon: 'pi pi-cloud', tone: 'good', text: t('domains.wizard.found.cdn', { cdn: f.cdn || 'CDN' }) }
  if (f.mode === 'reality')
    return {
      icon: 'pi pi-globe',
      tone: f.reality_friendly === false ? 'warn' : 'info',
      text: t(f.reality_friendly === false ? 'domains.wizard.found.externalNotFriendly' : 'domains.wizard.found.external', { ips: f.ips.join(', ') }),
    }
  return { icon: 'pi pi-question-circle', tone: 'warn', text: t('domains.wizard.found.unresolved') }
})

/** A friendly default name for configs. */
const aliasSuggestions = computed(() => {
  const base = cleanName.value.replace(/^\*\./, '')
  const label = base.split('.')[0] ?? base
  const kindName = t(`domains.kind.${kind.value}.name`)
  const out = [`${KIND_META[kind.value].emoji} ${label}`, `${label} ${kindName}`]
  if (found.value?.cdn && kind.value === 'cdn') out.push(`${found.value.cdn} ${label}`)
  return [...new Set(out)]
})

function toAlias() {
  if (!alias.value) alias.value = aliasSuggestions.value[0] ?? cleanName.value
  step.value = 'alias'
}

async function save() {
  step.value = 'saving'
  error.value = null
  const meta = KIND_META[kind.value]
  try {
    const next = await domainsApi.create({
      domain: cleanName.value,
      alias: alias.value.trim() || cleanName.value,
      mode: meta.mode,
      fake_mode: tlsMode.value,
      ...(tlsMode.value === 'reality' ? { servernames: cleanName.value } : {}),
    })
    const row = next.domains.find((d) => d.id === next.created_id)
    warnings.value = next.warnings ?? []
    if (row) {
      created.value = row
      emit('added', next, row)
    }
    step.value = next.certificate_requested && row ? 'cert' : 'done'
  } catch (err) {
    error.value = apiErrorMessage(err)
    step.value = 'alias'
  }
}

function onCertFinished(_tls: unknown, ok: boolean) {
  certOk.value = ok
}

function editMore() {
  if (created.value) emit('edit', created.value)
  visible.value = false
}

/** Server warnings may carry <br> line breaks; shown as text. */
function plain(w: string): string {
  return w.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '')
}

function back() {
  error.value = null
  if (step.value === 'mode') step.value = 'name'
  else if (step.value === 'alias') step.value = 'mode'
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :draggable="false"
    :closable="step !== 'saving'"
    class="wz"
    :style="{ width: 'min(44rem, calc(100vw - 1.5rem))' }"
    :breakpoints="{ '640px': '100vw' }"
    :header="t('domains.wizard.title')"
  >
    <!-- Steps -->
    <ol class="wz__steps" :aria-label="t('domains.wizard.title')">
      <li v-for="(s, i) in STEPS" :key="s" class="wz__step" :class="{ 'wz__step--done': i < stepIndex, 'wz__step--now': i === stepIndex }">
        <span class="wz__dot"><i v-if="i < stepIndex" class="pi pi-check" /><template v-else>{{ i + 1 }}</template></span>
        <span class="wz__step-label">{{ t(`domains.wizard.steps.${s}`) }}</span>
      </li>
    </ol>

    <Transition name="wz-slide" mode="out-in">
      <!-- 1. Name -->
      <form v-if="step === 'name'" key="name" class="wz__pane" @submit.prevent="detect">
        <h3 class="wz__q">{{ t('domains.wizard.nameQ') }}</h3>
        <p class="wz__lead">{{ t('domains.wizard.nameLead') }}</p>
        <div ref="nameBox" class="wz__name">
          <span class="wz__globe"><i class="pi pi-globe" /></span>
          <InputText
            v-model="name"
            dir="ltr"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            placeholder="sub.example.com"
            :invalid="!!nameError || takenLocally"
            class="wz__name-input"
            fluid
          />
        </div>
        <small v-if="nameError" class="wz__err">{{ nameError }}</small>
        <small v-else-if="takenLocally" class="wz__err">{{ t('domains.wizard.taken') }}</small>
        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
        <div class="wz__actions">
          <span />
          <Button type="submit" :label="detecting ? t('domains.wizard.checking') : t('domains.wizard.check')" icon="pi pi-search" icon-pos="right" :loading="detecting" :disabled="!cleanName || !!nameError || takenLocally" />
        </div>
      </form>

      <!-- 2. Mode -->
      <div v-else-if="step === 'mode'" key="mode" class="wz__pane">
        <div v-if="finding" class="wz__finding" :class="`wz__finding--${finding.tone}`">
          <i :class="finding.icon" />
          <div>
            <b dir="ltr">{{ cleanName }}</b>
            <span>{{ finding.text }}</span>
          </div>
        </div>
        <section class="wz__part">
          <h3 class="wz__part-title"><span class="wz__part-n">1</span>{{ t('domains.wizard.modeQ') }}</h3>
          <KindPicker v-model="kind" :kinds="KINDS" :fit="fit" />
        </section>
        <section class="wz__part">
          <h3 class="wz__part-title"><span class="wz__part-n">2</span>{{ t('domains.wizard.tlsQ') }}</h3>
          <TlsPicker v-model="tls" :locked="!tlsShown" :fit="tlsFit" :taken="takenFakeModes" />
        </section>
        <Message v-if="fit[kind] === 'bad'" severity="warn" size="small" :closable="false">{{ t(decoy && tlsMode === 'reality' ? 'domains.wizard.mismatch.reality' : `domains.wizard.mismatch.${kind}`) }}</Message>
        <div class="wz__actions">
          <Button :label="t('common.back')" icon="pi pi-arrow-left" severity="secondary" text @click="back" />
          <Button :label="t('domains.wizard.next')" icon="pi pi-arrow-right" icon-pos="right" @click="toAlias" />
        </div>
      </div>

      <!-- 3. Alias -->
      <form v-else-if="step === 'alias' || step === 'saving'" key="alias" class="wz__pane" @submit.prevent="save">
        <h3 class="wz__q">{{ t('domains.wizard.aliasQ') }}</h3>
        <p class="wz__lead">{{ t('domains.wizard.aliasLead') }}</p>
        <InputText v-model="alias" :placeholder="cleanName" :disabled="step === 'saving'" fluid autofocus />
        <div class="wz__suggest">
          <button v-for="s in aliasSuggestions" :key="s" type="button" class="wz__chip" :class="{ 'wz__chip--on': alias === s }" :disabled="step === 'saving'" @click="alias = s">{{ s }}</button>
        </div>
        <div class="wz__summary">
          <span class="wz__summary-emoji">{{ KIND_META[kind].emoji }}</span>
          <span class="wz__summary-text">
            <b dir="ltr">{{ cleanName }}</b>
            <small>{{ t(`domains.kind.${kind}.name`) }}<template v-if="decoy"> · {{ t(`domains.tlsMode.${tlsMode}`) }}</template> · {{ alias || cleanName }}</small>
          </span>
        </div>
        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
        <div class="wz__actions">
          <Button :label="t('common.back')" icon="pi pi-arrow-left" severity="secondary" text :disabled="step === 'saving'" @click="back" />
          <Button type="submit" :label="step === 'saving' ? t('domains.wizard.saving') : t('domains.wizard.add')" icon="pi pi-check" :loading="step === 'saving'" />
        </div>
      </form>

      <!-- 4. Certificate -->
      <div v-else-if="step === 'cert' && created" key="cert" class="wz__pane">
        <CertProgress :domain-id="created.id" :domain="created.domain" @finished="onCertFinished" />
        <Message v-for="w in warnings" :key="w" severity="warn" size="small" :closable="false"><span class="wz__warn">{{ plain(w) }}</span></Message>
        <div class="wz__actions">
          <Button :label="t('domains.wizard.moreSettings')" icon="pi pi-sliders-h" severity="secondary" text @click="editMore" />
          <Button :label="certOk === null ? t('domains.wizard.continueBackground') : t('domains.wizard.finish')" icon="pi pi-check" @click="visible = false" />
        </div>
      </div>

      <!-- Done (no certificate needed) -->
      <div v-else key="done" class="wz__pane wz__done">
        <span class="wz__done-icon"><i class="pi pi-check" /></span>
        <h3 class="wz__q">{{ t('domains.wizard.added', { name: created?.domain || cleanName }) }}</h3>
        <p class="wz__lead">{{ t(decoy ? 'domains.wizard.noCertDecoy' : 'domains.wizard.noCert') }}</p>
        <Message v-for="w in warnings" :key="w" severity="warn" size="small" :closable="false"><span class="wz__warn">{{ plain(w) }}</span></Message>
        <div class="wz__actions">
          <Button :label="t('domains.wizard.moreSettings')" icon="pi pi-sliders-h" severity="secondary" text @click="editMore" />
          <Button :label="t('domains.wizard.finish')" icon="pi pi-check" @click="visible = false" />
        </div>
      </div>
    </Transition>
  </Dialog>
</template>

<style scoped>
.wz__steps {
  display: flex;
  gap: 0.35rem;
  margin: 0 0 1.25rem;
  padding: 0;
  list-style: none;
}
.wz__step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  padding-bottom: 0.55rem;
  border-bottom: 3px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  transition:
    border-color 0.3s ease,
    color 0.3s ease;
}
.wz__step--done {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, transparent);
}
.wz__step--now {
  border-color: var(--p-primary-color);
  color: var(--p-text-color);
  font-weight: 600;
}
.wz__dot {
  flex-shrink: 0;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.72rem;
  font-weight: 700;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.wz__step--done .wz__dot,
.wz__step--now .wz__dot {
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
}
.wz__dot i {
  font-size: 0.65rem;
}
.wz__step-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wz__pane {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.wz__q {
  margin: 0;
  font-size: 1.12rem;
  font-weight: 700;
}
.wz__lead {
  margin: -0.4rem 0 0;
  font-size: 0.86rem;
  color: var(--p-text-muted-color);
}
.wz__name {
  position: relative;
}
.wz__globe {
  position: absolute;
  inset-inline-start: 0.9rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--p-text-muted-color);
  pointer-events: none;
}
.wz__name-input {
  padding-inline-start: 2.5rem;
  height: 3.1rem;
  font-size: 1.05rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  border-radius: 14px;
}
.wz__err {
  margin-top: -0.4rem;
  font-size: 0.8rem;
  color: var(--p-red-500, #ef4444);
}
.wz__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.4rem;
}
.wz__finding {
  --tone: var(--p-primary-color);
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--tone) 35%, transparent);
  background: color-mix(in srgb, var(--tone) 8%, transparent);
}
.wz__finding--good {
  --tone: var(--p-green-500, #22c55e);
}
.wz__finding--warn {
  --tone: var(--p-amber-500, #f59e0b);
}
.wz__finding > i {
  margin-top: 0.15rem;
  font-size: 1.15rem;
  color: var(--tone);
}
.wz__finding div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.wz__finding b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88rem;
  text-align: start;
  overflow-wrap: anywhere;
}
.wz__finding span {
  font-size: 0.84rem;
  color: var(--p-text-muted-color);
}
.wz__suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.wz__chip {
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.wz__chip:hover,
.wz__chip--on {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
.wz__summary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.9rem;
  border-radius: 14px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.wz__summary-emoji {
  font-size: 1.5rem;
}
.wz__summary-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.wz__summary-text b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  overflow-wrap: anywhere;
  text-align: start;
}
.wz__summary-text small {
  color: var(--p-text-muted-color);
}
.wz__part {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.wz__part + .wz__part {
  padding-top: 0.9rem;
  border-top: 1px dashed var(--p-content-border-color);
}
.wz__part-title {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}
.wz__part-n {
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.wz__warn {
  white-space: pre-line;
}
.wz__done {
  align-items: center;
  text-align: center;
}
.wz__done .wz__actions {
  width: 100%;
}
.wz__done-icon {
  width: 3.6rem;
  height: 3.6rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 1.5rem;
  color: #fff;
  background: var(--p-green-500, #22c55e);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--p-green-500, #22c55e) 35%, transparent);
  animation: wz-pop 0.45s cubic-bezier(0.3, 1.6, 0.5, 1) both;
}
.wz-slide-enter-active,
.wz-slide-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.wz-slide-enter-from {
  opacity: 0;
  transform: translateX(14px);
}
.wz-slide-leave-to {
  opacity: 0;
  transform: translateX(-14px);
}
:global([dir='rtl']) .wz-slide-enter-from {
  transform: translateX(-14px);
}
:global([dir='rtl']) .wz-slide-leave-to {
  transform: translateX(14px);
}
@keyframes wz-pop {
  from {
    transform: scale(0.5);
  }
  to {
    transform: none;
  }
}
@media (max-width: 520px) {
  .wz__step-label {
    display: none;
  }
  .wz__step--now .wz__step-label {
    display: inline;
  }
}
@media (prefers-reduced-motion: reduce) {
  .wz-slide-enter-active,
  .wz-slide-leave-active {
    transition: none;
  }
  .wz__done-icon {
    animation: none;
  }
}
</style>
