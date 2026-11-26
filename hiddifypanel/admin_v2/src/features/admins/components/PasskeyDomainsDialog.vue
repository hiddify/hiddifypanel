<template>
  <Dialog
    :visible="visible"
    modal
    :draggable="false"
    :header="t('account.passkeys.domains.title')"
    :style="{ width: 'min(28rem, calc(100vw - 1.5rem))' }"
    class="pd-dialog"
    @update:visible="(v: boolean) => !v && finish()"
  >
    <div class="pd">
      <!-- Every domain of the panel, each in its own colour: a tap adds the passkey for that one -->
      <ul v-if="chips.length > 1" class="pd__domains" :aria-label="t('account.passkeys.domains.all')">
        <li v-for="c in chips" :key="c.domain">
          <button
            type="button"
            class="pd__chip"
            :class="`pd__chip--${c.state}`"
            :style="{ '--hue': c.hue }"
            :disabled="c.state === 'added' || c.state === 'busy'"
            :aria-current="c.state === 'current' ? 'step' : undefined"
            @click="pick(c)"
          >
            <i :class="CHIP_ICON[c.state]" aria-hidden="true" />
            <bdi dir="ltr">{{ c.domain }}</bdi>
          </button>
        </li>
      </ul>

      <section
        v-if="step && !finished"
        class="pd__card"
        :class="{ 'pd__card--added': results[index] === 'added' }"
        :style="{ '--hue': currentHue }"
      >
        <span class="pd__icon" aria-hidden="true"><i :class="results[index] === 'added' ? 'pi pi-check' : 'pi pi-key'" /></span>
        <small v-if="steps.length > 1" class="pd__count">{{ t('account.passkeys.domains.step', { step: index + 1, total: steps.length }) }}</small>
        <p class="pd__heading">{{ t('account.passkeys.domains.heading') }}</p>
        <bdi dir="ltr" class="pd__domain">{{ step.domain }}</bdi>
        <p class="pd__hint">{{ useTab ? t('account.passkeys.domains.tabHint') : t('account.passkeys.domains.hint') }}</p>

        <!-- Safari makes passkeys only on the domain's own page: a short tab of it, which closes itself when done -->
        <Button
          v-if="useTab"
          class="pd__create"
          :label="t('account.passkeys.domains.create')"
          icon="pi pi-key"
          rounded
          :loading="status === 'tab' || status === 'busy'"
          :disabled="results[index] === 'added'"
          @click="openStep"
        />
        <!-- The other domain's own button (the passkey is made there); it takes this page's colours and mode -->
        <div v-else class="pd__frame">
          <iframe
            :key="step.url"
            :src="frameSrc(step)"
            :title="t('account.passkeys.domains.frameTitle', { domain: step.domain })"
            allow="publickey-credentials-create; publickey-credentials-get"
            referrerpolicy="no-referrer"
            scrolling="no"
            :style="{ colorScheme: dark ? 'dark' : 'light' }"
            @load="loaded = true"
          />
          <Skeleton v-if="!loaded" class="pd__skeleton" height="100%" />
        </div>

        <small v-if="status" class="pd__status" :class="`pd__status--${statusTone}`" role="status">
          <i v-if="status === 'busy'" class="pi pi-spin pi-spinner" aria-hidden="true" />
          {{ statusText }}
        </small>
        <small v-else class="pd__why">{{ t('account.passkeys.domains.why') }}</small>
      </section>

      <!-- The end: what was added where -->
      <section v-else-if="finished" class="pd__card pd__card--done">
        <span class="pd__icon" aria-hidden="true"><i :class="added ? 'pi pi-check' : 'pi pi-info'" /></span>
        <p class="pd__title">{{ added ? t('account.passkeys.domains.doneTitle') : t('account.passkeys.domains.skipped') }}</p>
        <p class="pd__hint">
          {{ added ? t('account.passkeys.domains.doneSummary', { n: added, total: steps.length }) : t('account.passkeys.domains.doneNone') }}
        </p>
        <p v-if="added" class="pd__why">{{ t('account.passkeys.domains.doneHint') }}</p>
      </section>
    </div>

    <template #footer>
      <div v-if="!finished" class="pd__actions">
        <a v-if="step && !useTab" :href="step.url" target="_blank" class="pd__tab" @click.prevent="openStep">
          <i class="pi pi-external-link" aria-hidden="true" /> {{ t('account.passkeys.domains.openTab') }}
        </a>
        <span class="flex-1" />
        <Button
          :label="t('account.passkeys.domains.skip')"
          :icon="isRtl ? 'pi pi-angle-left' : 'pi pi-angle-right'"
          icon-pos="right"
          severity="secondary"
          outlined
          :disabled="results[index] === 'added'"
          @click="next('skipped')"
        />
      </div>
      <Button v-else :label="t('account.passkeys.domains.doneButton')" icon="pi pi-check" autofocus @click="finish" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Skeleton from 'primevue/skeleton'
import { adminsApi, type PasskeyStep } from '@/features/admins/api'
import { addPasskeyHere, passkeysVersion } from '@/features/admins/passkey-add'

/** Adds my passkey on the panel's other domains: each one's button in a frame, one domain after the other, with a
 * summary at the end (see passkeys.py). A domain can be skipped. */
const props = defineProps<{ steps: PasskeyStep[]; visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; done: [added: number] }>()

type Result = 'added' | 'skipped'
/** What the step page reports (passkey_enroll.html). */
type FrameStatus = 'ready' | 'busy' | 'added' | 'cancelled' | 'failed' | 'expired' | 'frame' | 'unsupported'
/** This page's own: the step's tab is open, or the browser did not open it. */
type StepStatus = FrameStatus | 'tab' | 'blocked'

const { t, locale } = useI18n()
const index = ref(0)
const results = ref<(Result | undefined)[]>([])
const loaded = ref(false)
const status = ref<StepStatus | null>(null)
const finished = ref(false)
const dark = ref(false)
const step = computed<PasskeyStep | undefined>(() => props.steps[index.value])
const added = computed(() => results.value.filter((r) => r === 'added').length)
const isRtl = computed(() => ['fa', 'ar'].includes(locale.value))

/** WebKit (Safari, and every browser on an iPhone or iPad) does not make passkeys in another domain's frame. */
function framesBlocked(): boolean {
  const ua = navigator.userAgent
  const ios = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)
  const safari = /Safari\//.test(ua) && !/Chrome\/|Chromium\/|Edg\/|OPR\/|Firefox\//.test(ua)
  return ios || safari
}
/** Each step in its own short tab instead of a frame (also once a frame said the browser refuses it there). */
const useTab = ref(framesBlocked())

const STATUS_TEXT: Partial<Record<StepStatus, string>> = {
  tab: 'account.passkeys.domains.inTab',
  blocked: 'account.passkeys.domains.tabBlocked',
  busy: 'account.passkeys.domains.waiting',
  added: 'account.passkeys.domains.added',
  cancelled: 'account.passkeys.domains.cancelled',
  failed: 'account.passkeys.domains.failed',
  expired: 'account.passkeys.domains.expired',
  frame: 'account.passkeys.domains.needsTab',
  unsupported: 'account.passkeys.domains.needsTab',
}
const statusText = computed(() => (status.value && STATUS_TEXT[status.value] ? t(STATUS_TEXT[status.value]!) : ''))
const statusTone = computed(() => {
  if (status.value === 'added') return 'ok'
  if (status.value === 'busy' || status.value === 'tab') return 'muted'
  return status.value === 'cancelled' || status.value === 'frame' || status.value === 'unsupported' || status.value === 'blocked' ? 'warn' : 'error'
})

/** Apple's system colours, one per domain (in the panel's order, so a domain keeps its colour). */
const HUES = ['#0a84ff', '#bf5af2', '#ff9f0a', '#30d158', '#ff375f', '#40c8e0', '#5e5ce6', '#ffd60a', '#ac8e68', '#63e6be']
type ChipState = 'added' | 'skipped' | 'current' | 'todo' | 'busy'
const CHIP_ICON: Record<ChipState, string> = {
  added: 'pi pi-check-circle',
  skipped: 'pi pi-minus-circle',
  current: 'pi pi-key',
  todo: 'pi pi-plus-circle',
  busy: 'pi pi-spin pi-spinner',
}
interface DomainChip {
  domain: string
  hue: string
  /** Its step here (-1: this page's own domain, or none to add). */
  step: number
  state: ChipState
}

/** All of the panel's domains, and those where I have a passkey already (read when the window opens). */
const allDomains = ref<string[]>([])
const have = ref<Set<string>>(new Set())
const addingHere = ref(false)
const here = window.location.hostname

const chips = computed<DomainChip[]>(() => {
  const list = [...allDomains.value]
  for (const s of props.steps) if (!list.includes(s.domain)) list.push(s.domain)
  return list.map((domain, i) => {
    const stepAt = props.steps.findIndex((s) => s.domain === domain)
    let state: ChipState
    if (stepAt >= 0) state = results.value[stepAt] ?? (stepAt === index.value && !finished.value ? 'current' : 'todo')
    else if (domain === here && addingHere.value) state = 'busy'
    else state = have.value.has(domain) ? 'added' : 'todo'
    return { domain, hue: HUES[i % HUES.length], step: stepAt, state }
  })
})
const currentHue = computed(() => chips.value.find((c) => c.step === index.value)?.hue ?? HUES[0])

/** A tap on a domain: its step now (on Safari straight to its tab: the tap lets it open). */
async function pick(c: DomainChip) {
  if (c.state === 'added' || c.state === 'busy') return
  if (c.step >= 0) {
    window.clearTimeout(advance)
    stopWatching()
    popup = null
    results.value[c.step] = undefined
    index.value = c.step
    finished.value = false
    loaded.value = false
    status.value = null
    if (useTab.value) openStep()
    return
  }
  // This page's own domain (skipped or closed before): the device's prompt right here.
  if (c.domain !== here) return
  addingHere.value = true
  try {
    const { added: made } = await addPasskeyHere(here, [here])
    if (made) have.value = new Set([...have.value, here])
  } catch {
    // closed or refused: the chip stays to try again
  } finally {
    addingHere.value = false
  }
}

async function loadDomains() {
  try {
    const mine = await adminsApi.myPasskeys()
    allDomains.value = mine.domains ?? []
    have.value = new Set(mine.passkeys.map((p) => p.domain))
  } catch {
    allDomains.value = []
  }
}

/** `#rrggbb` (alpha dropped) of a computed `rgb()`/`rgba()` colour, or '' when it is not one. */
function hex(color: string): string {
  const m = color.match(/rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/)
  return m ? m.slice(1, 4).map((n) => Number(n).toString(16).padStart(2, '0')).join('') : ''
}

/** This page's button look (PrimeVue's primary button), measured once per window, for the frame's button. */
let look = ''
function measureLook(): string {
  const probe = document.createElement('button')
  probe.className = 'p-button'
  probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none'
  document.body.appendChild(probe)
  const css = getComputedStyle(probe)
  const params = new URLSearchParams()
  const bg = hex(css.backgroundColor)
  const fg = hex(css.color)
  if (bg) params.set('c', bg)
  if (fg) params.set('f', fg)
  const radius = parseFloat(css.borderTopLeftRadius)
  if (radius >= 0 && radius < 100) params.set('r', `${Math.round(radius)}px`)
  probe.remove()
  return params.toString()
}

/** The frame follows this page's mode and colours (it can not read this domain's settings). */
function frameSrc(s: PasskeyStep): string {
  return `${s.url}#m=${dark.value ? 'dark' : 'light'}&${look}`
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    dark.value = document.documentElement.classList.contains('app-dark')
    look = measureLook()
    index.value = 0
    results.value = []
    void loadDomains()
    loaded.value = false
    status.value = null
    finished.value = false
  },
  { immediate: true },
)

/** The step's page in a tab of its own (opened by my tap, so not blocked). It tells this page how it went and
 * closes itself once the passkey is made, which brings the admin back here. */
let popup: Window | null = null
let popupWatch: number | undefined
function stopWatching() {
  window.clearInterval(popupWatch)
  popupWatch = undefined
}
function openStep() {
  const s = step.value
  if (!s || results.value[index.value] === 'added') return
  // Not noopener: the page answers through window.opener (only to this page's origin, see passkey_enroll.html).
  popup = window.open(frameSrc(s), 'hiddify-passkey')
  if (!popup) {
    status.value = 'blocked'
    return
  }
  status.value = 'tab'
  stopWatching()
  // Closed by the admin before the passkey was made: the button is ready again.
  popupWatch = window.setInterval(() => {
    if (popup && !popup.closed) return
    stopWatching()
    popup = null
    if (status.value === 'tab' || status.value === 'busy') status.value = null
  }, 600)
}

function finish() {
  if (!props.visible) return
  stopWatching()
  emit('update:visible', false)
  emit('done', added.value)
}

let advance: number | undefined
function next(result: Result) {
  window.clearTimeout(advance)
  stopWatching()
  popup = null
  results.value[index.value] = result
  if (result === 'added') passkeysVersion.value++
  loaded.value = false
  status.value = null
  // The next domain still to do (after this one, then from the start: a tap may have jumped ahead).
  const n = props.steps.length
  const order = Array.from({ length: n }, (_, k) => (index.value + 1 + k) % n)
  const todo = order.find((i) => !results.value[i])
  if (todo === undefined) finished.value = true
  else index.value = todo
}

/** Only the frame's own domain may say how it went (another page can not move this on). */
function onMessage(event: MessageEvent) {
  const s = step.value
  if (!props.visible || finished.value || !s || event.origin !== s.origin) return
  const data = event.data as { type?: string; status?: FrameStatus } | null
  if (!data || data.type !== 'hiddify-passkey' || !data.status) return
  loaded.value = true
  // The tab's own first try is no news while it is open.
  if (data.status === 'ready' && popup && !popup.closed) return
  // A frame the browser refuses: this step and the next ones go through a tab instead.
  if (data.status === 'frame' && !useTab.value) {
    useTab.value = true
    status.value = null
    return
  }
  status.value = data.status === 'ready' ? null : data.status
  if (data.status === 'added') {
    results.value[index.value] = 'added'
    // A moment to see the tick, then the next domain (whose page asks for the passkey right away where it may).
    advance = window.setTimeout(() => next('added'), 900)
  }
}

onMounted(() => window.addEventListener('message', onMessage))
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  window.clearTimeout(advance)
  stopWatching()
})
</script>

<style scoped>
.pd {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.pd__domains {
  list-style: none;
  margin: 0;
  padding: 0.1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  max-height: 7.6rem;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.pd__domains li {
  min-width: 0;
  max-width: 100%;
}
/* Very light, each in its domain's own colour (--hue) */
.pd__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  max-width: 100%;
  min-height: 2rem;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--hue) 20%, transparent);
  background: color-mix(in srgb, var(--hue) 7%, transparent);
  color: color-mix(in srgb, var(--hue) 62%, var(--p-text-color));
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    transform 0.15s ease,
    opacity 0.25s ease;
}
.pd__chip:hover:not(:disabled) {
  background: color-mix(in srgb, var(--hue) 12%, transparent);
}
.pd__chip:active:not(:disabled) {
  transform: scale(0.96);
}
.pd__chip:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--hue) 60%, transparent);
  outline-offset: 2px;
}
.pd__chip bdi {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pd__chip i {
  flex: none;
  font-size: 0.8rem;
  color: var(--hue);
}
.pd__chip--current {
  border-color: color-mix(in srgb, var(--hue) 45%, transparent);
  background: color-mix(in srgb, var(--hue) 13%, transparent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--hue) 12%, transparent);
}
.pd__chip--added {
  cursor: default;
}
.pd__chip--added i {
  color: #30d158;
}
.pd__chip--skipped {
  opacity: 0.6;
}
.pd__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.35rem;
  padding: 1.4rem 1.1rem 1.1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--hue, var(--p-primary-color)) 18%, var(--p-content-border-color));
  background: linear-gradient(180deg, color-mix(in srgb, var(--hue, var(--p-primary-color)) 8%, transparent), transparent 70%);
  transition:
    background 0.35s ease,
    border-color 0.35s ease;
}
.pd__icon {
  width: 3.1rem;
  height: 3.1rem;
  margin-bottom: 0.35rem;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 1.35rem;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
  box-shadow: 0 8px 22px -8px color-mix(in srgb, var(--p-primary-color) 70%, transparent);
  transition: background-color 0.3s ease;
}
.pd__card--added .pd__icon,
.pd__card--done .pd__icon {
  background: var(--p-green-500, #22c55e);
  color: #fff;
  box-shadow: 0 8px 22px -8px color-mix(in srgb, var(--p-green-500, #22c55e) 70%, transparent);
}
.pd__count {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
}
.pd__heading,
.pd__title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--p-text-muted-color);
}
.pd__title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--p-text-color);
}
.pd__domain {
  font-family: var(--p-font-family-mono, ui-monospace, monospace);
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--p-text-color);
  overflow-wrap: anywhere;
}
.pd__hint {
  margin: 0.25rem 0 0.6rem;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
}
.pd__create {
  align-self: stretch;
  min-height: 2.9rem;
  font-weight: 600;
}
.pd__frame {
  position: relative;
  width: 100%;
  height: 3rem;
}
.pd__frame iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: transparent;
  overflow: hidden;
}
.pd__skeleton {
  position: absolute;
  inset: 0;
}
.pd__status,
.pd__why {
  margin-top: 0.35rem;
  font-size: 0.78rem;
  line-height: 1.45;
}
.pd__why {
  color: var(--p-text-muted-color);
}
.pd__status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.pd__status--muted {
  color: var(--p-text-muted-color);
}
.pd__status--ok {
  color: var(--p-green-600, #16a34a);
  font-weight: 600;
}
.pd__status--warn {
  color: var(--p-orange-600, #ea580c);
}
.pd__status--error {
  color: var(--p-red-500, #ef4444);
}
.pd__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}
.pd__tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  text-decoration: none;
}
.pd__tab:hover {
  color: var(--p-primary-color);
}
</style>
