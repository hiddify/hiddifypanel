<script setup lang="ts">
/**
 * One run, live: a progress bar with the step in words, the elapsed time, the log as a terminal and, at the
 * end, whether it worked. Keeps asking while the panel restarts (installs restart it at the end).
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { ACTION_META, LogReader, type ApplyAction, type LogChunk, type LogSources } from '@/features/apply/api'
import TerminalView from '@/features/apply/components/TerminalView.vue'
import { AnsiParser, type AnsiSpan } from '@/shared/utils/ansi'

const props = defineProps<{ action: ApplyAction; file: string; started: number; sources: LogSources }>()
const emit = defineEmits<{ finished: [ok: boolean]; close: [] }>()
const { t } = useI18n()

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

let offset = 0
const reader = new LogReader(props.file, props.sources)
let timer: number | undefined
let clock: number | undefined
let startedAt = Date.now()
let lastGrowth = Date.now()
let stopped = false
let failures = 0

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
  phase.value = 'done'
  stopped = true
  window.clearTimeout(timer)
  window.clearInterval(clock)
  emit('finished', ok)
}

async function poll() {
  if (stopped) return
  try {
    const chunk = await reader.read({ offset, since: props.started })
    failures = 0
    reconnecting.value = false
    if (!chunk.started) {
      phase.value = 'starting'
    } else {
      if (phase.value === 'starting') phase.value = 'running'
      if (chunk.reset) {
        spans.value = []
        offset = 0
      }
      if (chunk.offset > offset) append(chunk.text)
      offset = chunk.offset
      if (chunk.progress) progress.value = chunk.progress
      if (chunk.finished) return finish(true)
      if (quiet.value && Date.now() - lastGrowth > QUIET_SECONDS * 1000 && spans.value.length) return finish(true)
    }
  } catch {
    // The panel restarts at the end of an install: keep trying.
    failures++
    reconnecting.value = failures >= 2
  }
  if (phase.value !== 'done' && Date.now() - lastGrowth > STALL_SECONDS * 1000) phase.value = 'stalled'
  timer = window.setTimeout(poll, 1000)
}

function reload() {
  window.location.reload()
}

onMounted(() => {
  startedAt = Date.now()
  lastGrowth = Date.now()
  clock = window.setInterval(() => (elapsed.value = (Date.now() - startedAt) / 1000), 500)
  void poll()
})
onBeforeUnmount(() => {
  stopped = true
  window.clearTimeout(timer)
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

    <p v-if="phase === 'done' && (action === 'install' || action === 'update' || action === 'apply')" class="run__after">
      <i class="pi pi-info-circle" />{{ t('apply.run.reload') }}
      <Button :label="t('apply.run.reloadBtn')" icon="pi pi-refresh" size="small" text @click="reload" />
    </p>

    <div v-if="phase === 'done' && sources.admin_links.length && action !== 'status' && action !== 'restart'" class="run__links">
      <span class="run__links-title"><i class="pi pi-link" />{{ t('apply.run.links') }}</span>
      <a v-for="l in sources.admin_links" :key="l" :href="l" target="_blank" rel="noopener" dir="ltr">{{ l.replace(/^https?:\/\//, '') }}</a>
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
  gap: 0.25rem;
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
.run__links a {
  color: var(--p-primary-color);
  overflow-wrap: anywhere;
  text-align: start;
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
