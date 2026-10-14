<template>
  <div class="rp">
    <header class="rp-head">
      <div class="rp-head__text">
        <b>{{ run.title }}</b>
        <code dir="ltr">{{ run.command }}</code>
      </div>
      <span class="rp-muted">{{ t('ssh.summary', counts) }}</span>
      <Button v-if="counts.running" :label="t('ssh.stopAll')" icon="pi pi-stop" severity="danger" text size="small" @click="emit('stop')" />
    </header>
    <ProgressBar :value="donePercent" :show-value="false" style="height: 4px" />

    <nav class="rp-tabs" role="tablist">
      <button v-for="r in run.results" :key="r.key" type="button" role="tab" class="rp-tab" :class="{ 'rp-tab--active': r.key === current?.key }" :aria-selected="r.key === current?.key" @click="picked = r.key">
        <i :class="stateIcon(r)" />
        <span dir="ltr">{{ r.title }}</span>
      </button>
    </nav>

    <div class="rp-body">
      <div v-for="r in run.results" v-show="r.key === current?.key" :key="r.key" class="rp-out">
        <div class="rp-status">
          <span :class="`rp-state rp-state--${r.state}`">{{ stateText(r) }}</span>
          <span v-if="r.message && r.status !== null" class="rp-muted">{{ r.message }}</span>
          <span class="rp-grow" />
          <Button v-if="r.tabId" :label="t('ssh.openTab')" icon="pi pi-external-link" text size="small" @click="emit('open-tab', r.tabId)" />
        </div>
        <OutputView :text="r.output" class="rp-term" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** A command run on several servers: one inner tab per server, each with its output live (colors and all) and its result. */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import OutputView from '@/features/ssh/components/OutputView.vue'

export type RunState = 'connecting' | 'running' | 'ok' | 'failed'
export interface RunResult {
  key: string
  /** The tab of the connection it runs in (0: none, it could not start). */
  tabId: number
  title: string
  state: RunState
  status: number | null
  message: string
  output: string
}
export interface Run {
  title: string
  command: string
  results: RunResult[]
}

const props = defineProps<{ run: Run }>()
const emit = defineEmits<{ stop: []; 'open-tab': [id: number] }>()
const { t } = useI18n()

const picked = ref('')
const current = computed(() => props.run.results.find((r) => r.key === picked.value) ?? props.run.results[0] ?? null)
const counts = computed(() => ({
  ok: props.run.results.filter((r) => r.state === 'ok').length,
  failed: props.run.results.filter((r) => r.state === 'failed').length,
  running: props.run.results.filter((r) => r.state === 'running' || r.state === 'connecting').length,
}))
const donePercent = computed(() => (props.run.results.length ? Math.round(((counts.value.ok + counts.value.failed) / props.run.results.length) * 100) : 0))

function stateIcon(r: RunResult): string {
  return {
    connecting: 'pi pi-spin pi-spinner',
    running: 'pi pi-spin pi-cog',
    ok: 'pi pi-check-circle rp-ok',
    failed: 'pi pi-times-circle rp-bad',
  }[r.state]
}

function stateText(r: RunResult): string {
  if (r.state === 'connecting') return t('ssh.stConnecting')
  if (r.state === 'running') return t('ssh.stRunning')
  if (r.status !== null) return t('ssh.stExit', { status: r.status })
  return r.message || t('ssh.stFailed')
}
</script>

<style scoped>
.rp {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 0.5rem;
}
.rp-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.rp-head__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.rp-head__text code {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rp-muted {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.rp-tabs {
  display: flex;
  gap: 0.25rem;
  overflow-x: auto;
  border-bottom: 1px solid var(--p-content-border-color);
}
.rp-tab {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--p-text-muted-color);
  padding: 0.45rem 0.7rem;
  cursor: pointer;
  white-space: nowrap;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.85rem;
}
.rp-tab--active {
  color: var(--p-text-color);
  border-bottom-color: var(--p-primary-color);
}
.rp-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.rp-out {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.rp-status {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
}
.rp-grow {
  flex: 1;
}
.rp-state--ok,
.rp-ok {
  color: #3fb950;
}
.rp-state--failed,
.rp-bad {
  color: #f47067;
}
.rp-term {
  flex: 1;
  min-height: 12rem;
  height: auto;
}
</style>
