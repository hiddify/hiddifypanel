<script setup lang="ts">
/**
 * One run, live: a progress bar with the step in words, the elapsed time, the log as a terminal and, at the
 * end, whether it worked. The log is pushed over the live channel; while the panel restarts (installs restart it at the
 * end) it is read over HTTP from whatever address still answers.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { ACTION_META, adminDomainChanged, LogReader, type AdminLink, type ApplyAction, type LogChunk, type LogSources } from '@/features/apply/api'
import { liveStream, type Subscription } from '@/core/live/live'
import TerminalView from '@/features/apply/components/TerminalView.vue'
import { AnsiParser, type AnsiSpan } from '@/shared/utils/ansi'

const props = defineProps<{ action: ApplyAction; file: string; started: number; sources: LogSources }>()
const emit = defineEmits<{ finished: [ok: boolean]; close: [] }>()
const { t } = useI18n()
const toast = useToast()

type Phase = 'starting' | 'running' | 'done' | 'stalled'
const phase = ref<Phase>('starting')
const spans = ref<AnsiSpan[]>([])
const progress = ref<LogChunk['progress']>(null)
const elapsed = ref(0)
const reconnecting = ref(false)
const showLog = ref(false) // the log opens only when asked

const parser = new AnsiParser()
const MAX_SPANS = 6000
// Without "Finished!" in their logs: done when the log goes quiet.
const QUIET_ACTIONS: ApplyAction[] = ['restart', 'status']
const QUIET_SECONDS = 6
const STALL_SECONDS = 15 * 60
// The stream can be left half-open by a panel restart (no data, no error, no end): after this long without a chunk the
// log is read once over HTTP, and when that finds lines the stream missed, the stream is replaced.
const WATCHDOG_MS = 8000

let offset = 0
const reader = new LogReader(props.file, props.sources)
let feed: Subscription | null = null
let clock: number | undefined
let startedAt = Date.now()
let lastGrowth = Date.now()
let stopped = false
let lastChunk = Date.now() // the last answer of any kind (stream or HTTP)
let checking = false

const meta = computed(() => ACTION_META[props.action])
const quiet = computed(() => QUIET_ACTIONS.includes(props.action))
const percent = computed(() => (phase.value === 'done' ? 100 : (progress.value?.percent ?? 0)))
const indeterminate = computed(() => phase.value !== 'done' && (quiet.value || !progress.value))
const clockText = computed(() => {
  const s = Math.floor(elapsed.value)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})
const step = computed(() => {
  const p = progress.value
  if (!p) return t(phase.value === 'starting' ? 'apply.run.starting' : 'apply.run.working')
  return [p.title, p.text].filter((x) => x && x !== '...').join(' · ')
})

function append(text: string) {
  if (!text) return
  const next = parser.parse(text)
  spans.value = spans.value.concat(next)
  if (spans.value.length > MAX_SPANS) spans.value = spans.value.slice(-MAX_SPANS)
  lastGrowth = Date.now()
}

function finish(ok: boolean) {
  if (stopped) return
  phase.value = 'done'
  stopped = true
  feed?.stop()
  window.clearInterval(clock)
  emit('finished', ok)
}

/** A piece of the log, from the live stream or (while it is down) from the reader. */
function take(chunk: LogChunk) {
  if (stopped) return
  lastChunk = Date.now()
  reconnecting.value = false
  if (!chunk.started) {
    phase.value = 'starting'
    return
  }
  if (phase.value === 'starting') phase.value = 'running'
  if (chunk.reset) {
    spans.value = []
    offset = 0
  }
  if (chunk.offset > offset) append(chunk.text)
  offset = chunk.offset
  if (chunk.progress) progress.value = chunk.progress
  if (chunk.finished) finish(true)
}

/** Every half second: the quiet end of restart/status, and a run that stopped writing. */
function checkClock() {
  elapsed.value = (Date.now() - startedAt) / 1000
  if (stopped) return
  if (phase.value !== 'starting' && quiet.value && Date.now() - lastGrowth > QUIET_SECONDS * 1000 && spans.value.length) return finish(true)
  if (Date.now() - lastGrowth > STALL_SECONDS * 1000) phase.value = 'stalled'
  if (!checking && Date.now() - lastChunk > WATCHDOG_MS) void checkOverHttp()
}

/** The stream has been silent: is it the run (a quiet step) or the stream (dead after a restart)? */
async function checkOverHttp() {
  checking = true
  const before = offset
  try {
    const chunk = await reader.read({ offset, since: props.started })
    take(chunk)
    if (!stopped && chunk.offset > before) restartFeed() // the stream missed lines: it is gone
  } catch {
    reconnecting.value = true // nothing answers (the panel is restarting): the clock tries again
  } finally {
    checking = false
  }
}

function restartFeed() {
  feed?.stop()
  feed = null
  follow()
}

function follow() {
  // Pushed over the live channel. While it is down (the panel restarts during most runs), or if it refuses the stream (the
  // session is gone after a domain change), read over HTTP every second on whatever address still answers.
  feed = liveStream<LogChunk>('apply.log', () => ({ file: props.file, offset, since: props.started || undefined }), {
    onData: take,
    fallbackMs: 1000,
    fallback: () => reader.read({ offset, since: props.started }),
    // Ended without "Finished!" (the panel went away mid-run): follow again in a moment, from the same offset.
    onEnd: () => {
      if (!stopped) window.setTimeout(() => !stopped && follow(), 1000)
    },
    pauseWhenHidden: false,
  })
}

function reload() {
  window.location.reload()
}

/** Domains changed under the run: reload would stay on the old (often broken) origin — show the new links instead. */
const domainChanged = computed(() => adminDomainChanged(props.sources.admin_links ?? []))
const showReload = computed(
  () => phase.value === 'done' && !domainChanged.value && (props.action === 'install' || props.action === 'update' || props.action === 'apply'),
)
const showLinks = computed(
  () => phase.value === 'done' && (props.sources.admin_links?.length ?? 0) > 0 && props.action !== 'status' && props.action !== 'restart',
)

function linkLabel(link: AdminLink): string {
  return link.url.replace(/^https?:\/\//, '')
}

async function copyLink(link: AdminLink) {
  try {
    await navigator.clipboard.writeText(link.url)
    toast.add({ severity: 'success', summary: t('apply.run.linkCopied'), life: 2500 })
  } catch {
    toast.add({ severity: 'warn', summary: t('common.copy'), detail: link.url, life: 5000 })
  }
}

onMounted(() => {
  startedAt = Date.now()
  lastGrowth = Date.now()
  clock = window.setInterval(checkClock, 500)
  follow()
})
onBeforeUnmount(() => {
  stopped = true
  feed?.stop()
  window.clearInterval(clock)
})
</script>

<template>
  <section class="run" :class="[`run--${phase}`]" :style="{ '--run-color': meta.color }" role="status" aria-live="polite">
    <header class="run__head">
      <span class="run__icon">
        <i v-if="phase === 'done'" class="pi pi-check" />
        <i v-else-if="phase === 'stalled'" class="pi pi-exclamation-triangle" />
        <i v-else class="pi pi-spin pi-cog" />
      </span>
      <div class="run__titles">
        <h3 class="run__title">{{ t(`apply.action.${action}.running`) }}</h3>
        <p class="run__step">{{ phase === 'done' ? t(`apply.action.${action}.done`) : step }}</p>
      </div>
      <span class="run__clock" dir="ltr"><i class="pi pi-clock" />{{ clockText }}</span>
      <Button v-if="phase === 'done'" icon="pi pi-times" text rounded severity="secondary" :aria-label="t('donation.close')" @click="emit('close')" />
    </header>

    <ProgressBar :value="indeterminate ? undefined : percent" :mode="indeterminate ? 'indeterminate' : 'determinate'" :show-value="false" class="run__bar" />
    <div class="run__meta">
      <span v-if="!indeterminate" class="run__percent">{{ percent }}%</span>
      <span v-if="reconnecting" class="run__reconnect"><i class="pi pi-spin pi-spinner" />{{ t('apply.run.reconnecting') }}</span>
      <span v-else-if="phase === 'stalled'" class="run__warn">{{ t('apply.run.stalled') }}</span>
      <span v-else-if="phase === 'starting'" class="run__hint">{{ t('apply.run.waitingStart') }}</span>
      <span v-else-if="action === 'install' || action === 'update'" class="run__hint">{{ t('apply.run.dontClose') }}</span>
    </div>

    <p v-if="showReload" class="run__after">
      <i class="pi pi-info-circle" />{{ t('apply.run.reload') }}
      <Button :label="t('apply.run.reloadBtn')" icon="pi pi-refresh" size="small" text @click="reload" />
    </p>

    <div v-if="showLinks" class="run__links">
      <span class="run__links-title"><i class="pi pi-link" />{{ t('apply.run.links') }}</span>
      <div class="run__link-list">
        <div
          v-for="l in sources.admin_links"
          :key="l.url"
          class="run__link-chip"
          :class="l.secure ? 'run__link-chip--secure' : 'run__link-chip--insecure'"
        >
          <span class="run__link-chip__flag" :title="l.secure ? t('apply.run.secure') : t('apply.run.insecure')">
            <i :class="l.secure ? 'pi pi-lock' : 'pi pi-lock-open'" />
            {{ l.secure ? t('apply.run.secure') : t('apply.run.insecure') }}
          </span>
          <a class="run__link-chip__url" :href="l.url" target="_blank" rel="noopener" dir="ltr">{{ linkLabel(l) }}</a>
          <Button
            type="button"
            icon="pi pi-copy"
            text
            rounded
            size="small"
            severity="secondary"
            :aria-label="t('common.copy')"
            v-tooltip.top="t('common.copy')"
            @click="copyLink(l)"
          />
        </div>
      </div>
    </div>

    <Button class="run__toggle" :label="showLog ? t('apply.log.hide') : t('apply.log.show')" :icon="showLog ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" text size="small" severity="secondary" @click="showLog = !showLog" />
    <TerminalView v-show="showLog" :spans="spans" :height="phase === 'done' ? '18rem' : '22rem'" />
  </section>
</template>

<style scoped>
.run {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 1.1rem 1.2rem;
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--run-color) 40%, var(--p-content-border-color));
  background: linear-gradient(135deg, color-mix(in srgb, var(--run-color) 9%, transparent), transparent 65%), var(--p-content-background);
  animation: run-in 0.35s ease both;
}
.run--done {
  --run-color: var(--p-green-500, #22c55e);
}
.run--stalled {
  --run-color: var(--p-amber-500, #f59e0b);
}
.run__head {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.run__icon {
  flex-shrink: 0;
  width: 2.8rem;
  height: 2.8rem;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 1.2rem;
  color: var(--run-color);
  background: color-mix(in srgb, var(--run-color) 15%, transparent);
}
.run--done .run__icon {
  animation: run-pop 0.45s cubic-bezier(0.3, 1.6, 0.5, 1) both;
}
.run__titles {
  flex: 1;
  min-width: 0;
}
.run__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.run__step {
  margin: 0.1rem 0 0;
  font-size: 0.86rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run__clock {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-variant-numeric: tabular-nums;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.run__bar {
  height: 0.65rem;
  border-radius: 999px;
}
.run__bar :deep(.p-progressbar-value) {
  background: linear-gradient(90deg, color-mix(in srgb, var(--run-color) 70%, #fff), var(--run-color));
  transition: width 0.5s ease;
}
.run__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.9rem;
  min-height: 1.2rem;
  font-size: 0.8rem;
}
.run__percent {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--run-color);
}
.run__hint {
  color: var(--p-text-muted-color);
}
.run__reconnect {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--p-amber-600, #d97706);
}
.run__warn {
  color: var(--p-amber-700, #b45309);
  font-weight: 600;
}
.run__after {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.84rem;
  color: var(--p-text-muted-color);
}
.run__links {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
  font-size: 0.8rem;
}
.run__links-title {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}
.run__link-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.run__link-chip {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.35rem 0.35rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  min-width: 0;
}
.run__link-chip--secure {
  border-color: color-mix(in srgb, var(--p-green-500, #22c55e) 45%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 8%, var(--p-content-background));
}
.run__link-chip--insecure {
  border-color: color-mix(in srgb, var(--p-red-500, #ef4444) 45%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 8%, var(--p-content-background));
}
.run__link-chip__flag {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  white-space: nowrap;
}
.run__link-chip--secure .run__link-chip__flag {
  color: var(--p-green-600, #16a34a);
}
.run__link-chip--insecure .run__link-chip__flag {
  color: var(--p-red-600, #dc2626);
}
.run__link-chip__url {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--p-text-color);
  text-align: start;
  text-decoration: none;
}
.run__link-chip__url:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}
.run__toggle {
  align-self: flex-start;
}
@keyframes run-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes run-pop {
  from {
    transform: scale(0.5);
  }
  to {
    transform: none;
  }
}
@media (max-width: 560px) {
  .run {
    padding: 0.9rem;
    border-radius: 16px;
  }
  .run__clock {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .run,
  .run--done .run__icon {
    animation: none;
  }
}
</style>
