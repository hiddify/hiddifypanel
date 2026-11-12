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
      <!-- Where I am: one chip per domain (added, skipped, this one, still to do) -->
      <ol v-if="steps.length > 1" class="pd__steps">
        <li v-for="(s, i) in steps" :key="s.url" class="pd__chip" :class="`pd__chip--${chipState(i)}`">
          <i :class="chipIcon(i)" aria-hidden="true" />
          <bdi dir="ltr">{{ s.domain }}</bdi>
        </li>
      </ol>

      <section v-if="step && !finished" class="pd__card" :class="{ 'pd__card--added': results[index] === 'added' }">
        <span class="pd__icon" aria-hidden="true"><i :class="results[index] === 'added' ? 'pi pi-check' : 'pi pi-key'" /></span>
        <small v-if="steps.length > 1" class="pd__count">{{ t('account.passkeys.domains.step', { step: index + 1, total: steps.length }) }}</small>
        <p class="pd__heading">{{ t('account.passkeys.domains.heading') }}</p>
        <bdi dir="ltr" class="pd__domain">{{ step.domain }}</bdi>
        <p class="pd__hint">{{ t('account.passkeys.domains.hint') }}</p>

        <!-- The other domain's own button (the passkey is made there); it takes this page's colours and mode -->
        <div class="pd__frame">
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
        <a v-if="step" :href="step.url" target="_blank" rel="noopener noreferrer" class="pd__tab" :class="{ 'pd__tab--strong': status === 'frame' }">
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
import type { PasskeyStep } from '@/features/admins/api'

/** Adds my passkey on the panel's other domains: each one's button in a frame, one domain after the other, with a
 * summary at the end (see passkeys.py). A domain can be skipped. */
const props = defineProps<{ steps: PasskeyStep[]; visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; done: [added: number] }>()

type Result = 'added' | 'skipped'
/** What the step page reports (passkey_enroll.html). */
type FrameStatus = 'ready' | 'busy' | 'added' | 'cancelled' | 'failed' | 'expired' | 'frame' | 'unsupported'

const { t, locale } = useI18n()
const index = ref(0)
const results = ref<(Result | undefined)[]>([])
const loaded = ref(false)
const status = ref<FrameStatus | null>(null)
const finished = ref(false)
const dark = ref(false)
const step = computed<PasskeyStep | undefined>(() => props.steps[index.value])
const added = computed(() => results.value.filter((r) => r === 'added').length)
const isRtl = computed(() => ['fa', 'ar'].includes(locale.value))

const STATUS_TEXT: Partial<Record<FrameStatus, string>> = {
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
  if (status.value === 'busy') return 'muted'
  return status.value === 'cancelled' || status.value === 'frame' || status.value === 'unsupported' ? 'warn' : 'error'
})

function chipState(i: number): string {
  return results.value[i] ?? (i === index.value && !finished.value ? 'current' : 'todo')
}
function chipIcon(i: number): string {
  const state = chipState(i)
  if (state === 'added') return 'pi pi-check-circle'
  if (state === 'skipped') return 'pi pi-minus-circle'
  return state === 'current' ? 'pi pi-key' : 'pi pi-circle'
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
    loaded.value = false
    status.value = null
    finished.value = false
  },
  { immediate: true },
)

function finish() {
  if (!props.visible) return
  emit('update:visible', false)
  emit('done', added.value)
}

let advance: number | undefined
function next(result: Result) {
  window.clearTimeout(advance)
  results.value[index.value] = result
  loaded.value = false
  status.value = null
  if (index.value + 1 >= props.steps.length) finished.value = true
  else index.value++
}

/** Only the frame's own domain may say how it went (another page can not move this on). */
function onMessage(event: MessageEvent) {
  const s = step.value
  if (!props.visible || finished.value || !s || event.origin !== s.origin) return
  const data = event.data as { type?: string; status?: FrameStatus } | null
  if (!data || data.type !== 'hiddify-passkey' || !data.status) return
  loaded.value = true
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
})
</script>

<style scoped>
.pd {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.pd__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.pd__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  max-width: 100%;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
  transition:
    background-color 0.25s ease,
    color 0.25s ease,
    border-color 0.25s ease;
}
.pd__chip bdi {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pd__chip i {
  font-size: 0.75rem;
}
.pd__chip--current {
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  font-weight: 600;
}
.pd__chip--added {
  color: var(--p-green-600, #16a34a);
  border-color: color-mix(in srgb, var(--p-green-500, #22c55e) 45%, transparent);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 10%, transparent);
}
.pd__chip--skipped {
  opacity: 0.65;
  text-decoration: line-through;
}
.pd__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.35rem;
  padding: 1.4rem 1.1rem 1.1rem;
  border-radius: 16px;
  border: 1px solid var(--p-content-border-color);
  background: linear-gradient(180deg, color-mix(in srgb, var(--p-primary-color) 7%, transparent), transparent 70%);
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
.pd__tab:hover,
.pd__tab--strong {
  color: var(--p-primary-color);
}
.pd__tab--strong {
  font-weight: 600;
}
</style>
