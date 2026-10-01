<script setup lang="ts">
/**
 * Waits (at most CERT_WAIT_SECONDS) for a requested certificate: polls the server, shows a progress bar,
 * then whether a real certificate was issued. `start` asks for one first (the add wizard already did).
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { apiErrorMessage } from '@/core/api/client'
import { CERT_WAIT_SECONDS, domainsApi, type DomainTls } from '@/features/domains/api'

const props = defineProps<{ domainId: number; domain: string; start?: boolean }>()
const emit = defineEmits<{ finished: [tls: DomainTls | null, ok: boolean] }>()

const { t } = useI18n()

type Phase = 'waiting' | 'ok' | 'failed' | 'timeout'
const phase = ref<Phase>('waiting')
const elapsed = ref(0)
const tls = ref<DomainTls | null>(null)
const error = ref('')
let startedAt = Date.now()
let tick: number | undefined
let poll: number | undefined
let stopped = false

/** Moves steadily but slows down near the end, so a slow ACME server does not look stuck at 100%. */
const percent = computed(() => {
  if (phase.value === 'ok') return 100
  const x = Math.min(elapsed.value / CERT_WAIT_SECONDS, 1)
  return Math.round((1 - Math.pow(1 - x, 1.6)) * 96)
})
const remaining = computed(() => Math.max(0, CERT_WAIT_SECONDS - Math.floor(elapsed.value)))

const STEPS = ['contact', 'verify', 'install'] as const
const step = computed(() => (elapsed.value < 8 ? 0 : elapsed.value < 30 ? 1 : 2))

function stop() {
  stopped = true
  window.clearInterval(tick)
  window.clearTimeout(poll)
}

function finish(next: Phase) {
  phase.value = next
  stop()
  emit('finished', tls.value, next === 'ok')
}

function newerThanStart(iso: string | null): boolean {
  return !!iso && Date.parse(iso) >= startedAt - 2000
}

async function check() {
  if (stopped) return
  try {
    const cur = await domainsApi.certificate(props.domainId)
    tls.value = cur
    const job = cur.job
    if (cur.status === 'valid' && (job?.state === 'done' || newerThanStart(cur.updated_at))) return finish('ok')
    if (job?.state === 'failed') {
      error.value = job.error || cur.error
      return finish('failed')
    }
    if (job?.state === 'done') {
      // The script finished but there is no real certificate (DNS, firewall or rate limit).
      error.value = cur.error
      return finish(cur.status === 'valid' ? 'ok' : 'failed')
    }
  } catch {
    // Keep waiting: the panel may be busy while acme.sh runs.
  }
  if (elapsed.value >= CERT_WAIT_SECONDS) return finish(tls.value?.status === 'valid' ? 'ok' : 'timeout')
  poll = window.setTimeout(check, 3000)
}

async function begin() {
  stopped = false
  phase.value = 'waiting'
  error.value = ''
  elapsed.value = 0
  startedAt = Date.now()
  window.clearInterval(tick)
  tick = window.setInterval(() => (elapsed.value = (Date.now() - startedAt) / 1000), 250)
  if (props.start) {
    try {
      await domainsApi.requestCertificate(props.domainId)
    } catch (err) {
      error.value = apiErrorMessage(err)
      return finish('failed')
    }
  }
  poll = window.setTimeout(check, 2500)
}

/** Ask again (after fixing DNS or the firewall). */
async function retry() {
  try {
    await domainsApi.requestCertificate(props.domainId)
  } catch (err) {
    error.value = apiErrorMessage(err)
    return
  }
  stopped = false
  phase.value = 'waiting'
  error.value = ''
  elapsed.value = 0
  startedAt = Date.now()
  tick = window.setInterval(() => (elapsed.value = (Date.now() - startedAt) / 1000), 250)
  poll = window.setTimeout(check, 2500)
}

onMounted(begin)
onBeforeUnmount(stop)
</script>

<template>
  <div class="cert" :class="`cert--${phase}`" role="status" aria-live="polite">
    <div class="cert__icon">
      <i v-if="phase === 'waiting'" class="pi pi-spin pi-spinner" />
      <i v-else-if="phase === 'ok'" class="pi pi-verified" />
      <i v-else-if="phase === 'timeout'" class="pi pi-hourglass" />
      <i v-else class="pi pi-times-circle" />
    </div>

    <div class="cert__body">
      <p class="cert__title">{{ t(`domains.cert.${phase}`) }}</p>
      <p class="cert__domain" dir="ltr">{{ domain }}</p>

      <template v-if="phase === 'waiting'">
        <ProgressBar :value="percent" :show-value="false" class="cert__bar" />
        <div class="cert__steps">
          <span v-for="(s, i) in STEPS" :key="s" class="cert__step" :class="{ 'cert__step--on': i <= step, 'cert__step--now': i === step }">
            <i class="pi" :class="i < step ? 'pi-check' : 'pi-circle-fill'" />{{ t(`domains.cert.steps.${s}`) }}
          </span>
          <span class="cert__left">{{ t('domains.cert.secondsLeft', { n: remaining }) }}</span>
        </div>
      </template>

      <template v-else-if="phase === 'ok'">
        <p class="cert__hint">
          {{ t('domains.cert.okHint') }}
          <span v-if="tls?.issuer" class="cert__issuer">{{ tls.issuer }}</span>
        </p>
      </template>

      <template v-else>
        <p class="cert__hint">{{ t(phase === 'timeout' ? 'domains.cert.timeoutHint' : 'domains.cert.failedHint') }}</p>
        <pre v-if="error" class="cert__error" dir="ltr">{{ error }}</pre>
        <ul class="cert__tips">
          <li>{{ t('domains.cert.tips.dns') }}</li>
          <li>{{ t('domains.cert.tips.port80') }}</li>
          <li>{{ t('domains.cert.tips.cdn') }}</li>
        </ul>
        <Button :label="t('domains.cert.retry')" icon="pi pi-refresh" size="small" outlined @click="retry" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.cert {
  --cert-color: var(--p-primary-color);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  padding: 1.1rem 1.15rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--cert-color) 35%, var(--p-content-border-color));
  background: linear-gradient(135deg, color-mix(in srgb, var(--cert-color) 9%, transparent), transparent 70%), var(--p-content-background);
}
.cert--ok {
  --cert-color: var(--p-green-500, #22c55e);
}
.cert--failed {
  --cert-color: var(--p-red-500, #ef4444);
}
.cert--timeout {
  --cert-color: var(--p-amber-500, #f59e0b);
}
.cert__icon {
  width: 3rem;
  height: 3rem;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 1.4rem;
  color: var(--cert-color);
  background: color-mix(in srgb, var(--cert-color) 14%, transparent);
}
.cert--ok .cert__icon {
  animation: cert-pop 0.45s cubic-bezier(0.3, 1.6, 0.5, 1) both;
}
.cert__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.cert__title {
  margin: 0;
  font-weight: 700;
  font-size: 1.02rem;
}
.cert__domain {
  margin: -0.3rem 0 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: start;
}
.cert__bar {
  height: 0.55rem;
  border-radius: 999px;
}
.cert__bar :deep(.p-progressbar-value) {
  background: linear-gradient(90deg, var(--p-primary-400, var(--p-primary-color)), var(--p-primary-color));
  transition: width 0.25s linear;
}
.cert__steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.9rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.cert__step {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  opacity: 0.55;
  transition: opacity 0.3s ease;
}
.cert__step i {
  font-size: 0.55rem;
}
.cert__step--on {
  opacity: 1;
}
.cert__step--on i.pi-check {
  font-size: 0.7rem;
  color: var(--p-green-500, #22c55e);
}
.cert__step--now {
  color: var(--p-primary-color);
  font-weight: 600;
}
.cert__left {
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
}
.cert__hint {
  margin: 0;
  font-size: 0.86rem;
  color: var(--p-text-muted-color);
}
.cert__issuer {
  display: inline-block;
  margin-inline-start: 0.35rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--cert-color);
  background: color-mix(in srgb, var(--cert-color) 12%, transparent);
}
.cert__error {
  margin: 0;
  max-height: 7rem;
  overflow: auto;
  padding: 0.5rem 0.65rem;
  border-radius: 10px;
  font-size: 0.74rem;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
  text-align: start;
}
.cert__tips {
  margin: 0;
  padding-inline-start: 1.1rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.cert .p-button {
  align-self: flex-start;
}
@keyframes cert-pop {
  from {
    transform: scale(0.6);
  }
  to {
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cert--ok .cert__icon {
    animation: none;
  }
}
</style>
