<template>
  <div class="ap-page">
    <PageHeader :title="t('apply.title')" :subtitle="t('apply.subtitle')" />

    <div v-if="loading" class="ap-cards"><Skeleton v-for="i in 4" :key="i" height="11rem" border-radius="18px" /></div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <!-- The run in progress (or just finished) -->
      <Transition name="ap-run">
        <RunPanel v-if="run" :key="run.started" class="ap-run" :action="run.action" :file="run.log" :started="run.started" :sources="run" @finished="onFinished" @close="run = null" />
      </Transition>

      <Message v-if="!run && busyOutside" severity="info" :closable="false" class="ap-busy">
        <span class="ap-busy__row"><i class="pi pi-spin pi-cog" />{{ t('apply.busyOutside') }}<Button :label="t('apply.watch')" size="small" text @click="watchRunning" /></span>
      </Message>

      <!-- Actions -->
      <div class="ap-cards">
        <article v-for="a in cards" :key="a.key" class="ap-card" :class="[`ap-card--${a.key}`, { 'ap-card--main': a.key === 'apply', 'ap-card--busy': a.running }]" :style="{ '--ap-color': a.meta.color }">
          <header class="ap-card__head">
            <span class="ap-card__icon"><i :class="a.running ? 'pi pi-spin pi-cog' : a.meta.icon" /></span>
            <div class="ap-card__titles">
              <h3 class="ap-card__title">{{ t(`apply.action.${a.key}.title`) }}</h3>
              <span v-if="a.key === 'apply'" class="ap-card__tag"><i class="pi pi-star-fill" />{{ t('apply.recommended') }}</span>
            </div>
            <span class="ap-card__time" v-tooltip.top="t('apply.takes')"><i class="pi pi-stopwatch" />{{ t('apply.minutes', { n: a.meta.minutes }) }}</span>
          </header>
          <p class="ap-card__desc">{{ t(`apply.action.${a.key}.desc`) }}</p>
          <p v-if="a.when" class="ap-card__last"><i class="pi" :class="a.last?.finished ? 'pi-check-circle ap-ok' : 'pi-info-circle'" />{{ t('apply.lastRun', { when: a.when }) }}</p>
          <Button
            :label="t(`apply.action.${a.key}.button`)"
            :icon="a.meta.icon"
            :severity="a.meta.danger ? 'danger' : undefined"
            :outlined="a.key !== 'apply'"
            :loading="starting === a.key"
            :disabled="blocked"
            class="ap-card__btn"
            @click="ask(a.key)"
          />
        </article>
      </div>

      <!-- Tools -->
      <section class="ap-tools">
        <Button :label="t('actions.resetCache')" icon="pi pi-eraser" severity="secondary" outlined size="small" :loading="resetting" @click="resetCache" />
        <Button :label="t('actions.ports.title')" icon="pi pi-sitemap" severity="secondary" outlined size="small" @click="portsVisible = true" />
      </section>

      <!-- Logs -->
      <section class="ap-logs">
        <header class="ap-logs__head">
          <span class="ap-logs__icon"><i class="pi pi-history" /></span>
          <div>
            <h3 class="ap-logs__title">{{ t('apply.logs.title') }}</h3>
            <p class="ap-logs__sub">{{ t('apply.logs.sub') }}</p>
          </div>
          <Button icon="pi pi-refresh" text rounded severity="secondary" class="ap-logs__refresh" :aria-label="t('legacy.refresh')" v-tooltip.top="t('legacy.refresh')" @click="refresh()" />
        </header>
        <ul class="ap-files">
          <li v-for="f in files" :key="f.name" class="ap-file">
            <span class="ap-file__icon"><i :class="LOG_ICON[f.name] ?? 'pi pi-file'" /></span>
            <button type="button" class="ap-file__body" @click="openLog(f)">
              <b dir="ltr">{{ f.name }}</b>
              <small>{{ ago(f.mtime) }} · {{ formatSize(f.size) }}</small>
            </button>
            <Button icon="pi pi-eye" text rounded size="small" :aria-label="t('apply.logs.view')" v-tooltip.top="t('apply.logs.view')" @click="openLog(f)" />
            <a :href="applyApi.downloadUrl(f.name)" download :aria-label="t('apply.log.download')"><Button icon="pi pi-download" text rounded size="small" severity="secondary" v-tooltip.top="t('apply.log.download')" /></a>
          </li>
          <li v-if="!files.length" class="ap-empty"><i class="pi pi-inbox" />{{ t('apply.logs.empty') }}</li>
        </ul>
      </section>
    </template>

    <LogViewerDialog v-model:visible="logVisible" :file="logFile" />
    <PublicPortsDialog v-model:visible="portsVisible" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage, getHttp } from '@/core/api/client'
import LogViewerDialog from '@/features/apply/components/LogViewerDialog.vue'
import RunPanel from '@/features/apply/components/RunPanel.vue'
import PublicPortsDialog from '@/features/actions/components/PublicPortsDialog.vue'
import { ACTIONS, ACTION_LOG, ACTION_META, LOG_ICON, applyApi, formatSize, type ApplyAction, type ApplyState, type LogFile, type StartedRun } from '@/features/apply/api'

const { t, locale } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const dangerConfirm = useDangerConfirm()

const state = ref<ApplyState | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const run = ref<StartedRun | null>(null)
const starting = ref<ApplyAction | null>(null)
const resetting = ref(false)
const portsVisible = ref(false)
const logVisible = ref(false)
const logFile = ref<LogFile | null>(null)
let timer: number | undefined

const files = computed(() => state.value?.files ?? [])
const busyOutside = computed(() => !!state.value?.running.length)
const cards = computed(() =>
  ACTIONS.map((key) => {
    const last = state.value?.last[key]
    return { key, meta: ACTION_META[key], last, when: last ? ago(last.mtime) : '', running: !!state.value?.running.includes(key) }
  }),
)

/** Only one action at a time. */
const runDone = ref(false)
const blocked = computed(() => !!starting.value || (!!run.value && !runDone.value) || busyOutside.value)

function ago(seconds: number): string {
  const diff = seconds - Date.now() / 1000
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const [unit, size] = units.find(([, s]) => Math.abs(diff) >= s) ?? ['minute', 60]
  return rtf.format(Math.round(diff / size), unit)
}

async function refresh(quiet = false) {
  try {
    state.value = await applyApi.state()
    loadError.value = null
  } catch (err) {
    if (!quiet) loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

function ask(key: ApplyAction) {
  if (!ACTION_META[key].confirm) return void start(key)
  dangerConfirm({
    header: t(`apply.action.${key}.title`),
    message: t(`apply.action.${key}.confirm`),
    acceptLabel: t(`apply.action.${key}.button`),
    accept: () => void start(key),
  })
}

async function start(key: ApplyAction) {
  starting.value = key
  try {
    run.value = await applyApi.start(key)
    runDone.value = false
    state.value = run.value
  } catch (err) {
    toast.add({ severity: 'warn', summary: t('apply.notStarted'), detail: apiErrorMessage(err), life: 7000 })
  } finally {
    starting.value = null
  }
}

/** Something started outside this page (console, cron): follow its log. */
function watchRunning() {
  const key = state.value?.running[0]
  if (!key) return
  run.value = { ...(state.value as ApplyState), action: key, log: ACTION_LOG[key], started: 0 }
  runDone.value = false
}

function onFinished() {
  runDone.value = true
  void refresh(true)
}

function openLog(f: LogFile) {
  logFile.value = f
  logVisible.value = true
}

async function resetCache() {
  resetting.value = true
  try {
    await getHttp().post('reset-cache/')
    toast.add({ severity: 'success', summary: t('actions.resetCacheDone'), life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('actions.resetCacheFailed'), detail: apiErrorMessage(err), life: 5000 })
  } finally {
    resetting.value = false
  }
}

onMounted(async () => {
  await refresh()
  // Sent here by "Apply" notices elsewhere: ?run=apply asks for it right away.
  const wanted = String(route.query.run ?? '') as ApplyAction
  if (ACTIONS.includes(wanted) && !busyOutside.value) {
    void router.replace({ query: {} })
    ask(wanted)
  }
  timer = window.setInterval(() => !run.value && void refresh(true), 10_000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<style scoped>
.ap-run {
  margin-bottom: 1.25rem;
}
.ap-busy {
  margin-bottom: 1rem;
}
.ap-busy__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}
.ap-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.ap-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 1.1rem 1.2rem;
  border-radius: 18px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-top: 3px solid var(--ap-color);
  animation: ap-in 0.4s ease both;
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease;
}
.ap-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.07);
}
.ap-card--main {
  grid-column: span 2;
  background: linear-gradient(135deg, color-mix(in srgb, var(--ap-color) 9%, transparent), transparent 70%), var(--p-content-background);
}
.ap-card__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.ap-card__icon {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--ap-color);
  background: color-mix(in srgb, var(--ap-color) 14%, transparent);
}
.ap-card__titles {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem 0.5rem;
  min-width: 0;
}
.ap-card__title {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 700;
}
.ap-card__tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0 0.5rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--ap-color);
  background: color-mix(in srgb, var(--ap-color) 13%, transparent);
}
.ap-card__tag i {
  font-size: 0.6rem;
}
.ap-card__time {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.ap-card__desc {
  margin: 0;
  flex: 1;
  font-size: 0.86rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
}
.ap-card__last {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
}
.ap-ok {
  color: var(--p-green-500, #22c55e);
}
.ap-card__btn {
  align-self: flex-start;
}
.ap-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.ap-logs {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1.1rem 1.2rem;
  border-radius: 18px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.ap-logs__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.ap-logs__head > div {
  flex: 1;
}
.ap-logs__icon {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.ap-logs__title {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 700;
}
.ap-logs__sub {
  margin: 0.1rem 0 0;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.ap-files {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr));
  gap: 0 1.2rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ap-file {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.2rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.ap-file a {
  text-decoration: none;
}
.ap-file__icon {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.ap-file__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.ap-file__body b {
  font-size: 0.86rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap-file__body small {
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
}
.ap-empty {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  color: var(--p-text-muted-color);
}
.ap-run-enter-active,
.ap-run-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.ap-run-enter-from,
.ap-run-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
@keyframes ap-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (max-width: 700px) {
  .ap-card--main {
    grid-column: auto;
  }
  .ap-card__btn {
    width: 100%;
  }
  .ap-files {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ap-card {
    animation: none;
  }
}
</style>
