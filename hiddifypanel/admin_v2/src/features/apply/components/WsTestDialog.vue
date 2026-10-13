<template>
  <Dialog :visible="visible" modal :header="t('wsTest.title')" :style="{ width: '64rem' }" :breakpoints="{ '960px': '96vw' }" @update:visible="emit('update:visible', $event)">
    <p class="text-muted-color mt-0">{{ t('wsTest.subtitle') }}</p>

    <div class="flex flex-wrap items-center gap-3">
      <Tag :value="t(`wsTest.state.${liveState}`)" :severity="stateSeverity" />
      <Tag v-if="liveTransport" :value="t(`wsTest.transport.${liveTransport}`)" severity="secondary" />
      <Tag v-if="liveProtocol" :value="liveProtocol" :severity="liveProtocol === 'h3' ? 'success' : liveProtocol === 'h2' ? 'info' : 'warn'" />
      <SelectButton v-model="transportChoice" :options="transportOptions" option-label="label" option-value="value" :allow-empty="false" size="small" />
      <Button icon="pi pi-refresh" :label="t('wsTest.reconnect')" severity="secondary" size="small" outlined @click="reconnect" />
      <span v-if="hello" class="text-muted-color text-sm">{{ t('wsTest.server', { pid: hello.pid, threads: hello.threads, protocol: hello.protocol, skew }) }}</span>
    </div>
    <Message v-if="error" severity="error" class="mt-3" :closable="false">{{ error }}</Message>
    <Message v-if="liveIssue" severity="warn" class="mt-3" :closable="false">{{ t('wsTest.issue', { issue: liveIssue }) }}</Message>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
      <section class="wt-box">
        <h4>{{ t('wsTest.latency') }}</h4>
        <div class="flex flex-wrap items-center gap-3">
          <Button icon="pi pi-send" :label="t('wsTest.ping')" size="small" @click="ping" />
          <label class="flex items-center gap-2"><ToggleSwitch v-model="autoPing" />{{ t('wsTest.autoPing') }}</label>
        </div>
        <div class="wt-facts mt-3">
          <div><span>{{ t('wsTest.last') }}</span><b>{{ ms(rtts.at(-1)) }}</b></div>
          <div><span>{{ t('wsTest.avg') }}</span><b>{{ ms(avg(rtts)) }}</b></div>
          <div><span>{{ t('wsTest.min') }}</span><b>{{ ms(rtts.length ? Math.min(...rtts) : undefined) }}</b></div>
          <div><span>{{ t('wsTest.max') }}</span><b>{{ ms(rtts.length ? Math.max(...rtts) : undefined) }}</b></div>
        </div>
      </section>

      <section class="wt-box">
        <h4>{{ t('wsTest.throughput') }}</h4>
        <div class="flex flex-wrap items-center gap-3">
          <InputNumber v-model="echoKb" :min="1" :max="8192" suffix=" KB" input-class="w-28" />
          <Button icon="pi pi-download" :label="t('wsTest.echo')" size="small" :loading="echoing" @click="echo" />
        </div>
        <p v-if="echoResult" class="mb-0">{{ t('wsTest.echoResult', echoResult) }}</p>
      </section>

      <section class="wt-box">
        <h4>{{ t('wsTest.serverPush') }}</h4>
        <p class="text-muted-color mt-0">{{ t('wsTest.serverPushHint') }}</p>
        <Button icon="pi pi-play" :label="t('wsTest.startPush')" size="small" :loading="pushing" @click="startTicks" />
        <div v-if="ticks.length" class="wt-facts mt-3">
          <div><span>{{ t('wsTest.received') }}</span><b>{{ ticks.length }} / {{ TICK_COUNT }}</b></div>
          <div><span>{{ t('wsTest.gapAvg') }}</span><b>{{ ms(avg(gaps)) }}</b></div>
          <div><span>{{ t('wsTest.jitter') }}</span><b>{{ ms(gaps.length ? Math.max(...gaps) - Math.min(...gaps) : undefined) }}</b></div>
        </div>
        <Message v-if="pushVerdict" :severity="pushVerdict === 'ok' ? 'success' : 'warn'" class="mt-3" :closable="false">{{ t(`wsTest.pushVerdict.${pushVerdict}`) }}</Message>
      </section>

      <section class="wt-box">
        <h4>{{ t('wsTest.push') }}</h4>
        <p class="text-muted-color mt-0">{{ t('wsTest.pushHint') }}</p>
        <Button icon="pi pi-bolt" :label="t('wsTest.publish')" size="small" @click="publish" />
        <p v-if="pushMs !== null" class="mb-0">{{ t('wsTest.pushResult', { ms: pushMs.toFixed(1) }) }}</p>
        <Message v-if="pushTimedOut" severity="warn" class="mt-3" :closable="false">{{ t('wsTest.pushTimeout') }}</Message>
      </section>

      <section class="wt-box">
        <h4>{{ t('wsTest.feed') }}</h4>
        <p class="text-muted-color mt-0">{{ t('wsTest.feedHint') }}</p>
        <div class="flex flex-wrap items-center gap-3">
          <InputNumber v-model="feedLimit" :min="1" :max="5000" input-class="w-28" />
          <Button icon="pi pi-database" :label="t('wsTest.preview')" size="small" @click="loadFeed" />
        </div>
        <div v-if="feed" class="wt-facts mt-3">
          <div><span>{{ t('wsTest.admins') }}</span><b>{{ feed.admins }}</b></div>
          <div><span>{{ t('wsTest.users') }}</span><b>{{ feed.users }}{{ feed.more ? '+' : '' }}</b></div>
          <div><span>{{ t('wsTest.jsonSize') }}</span><b>{{ bytes(feed.json_bytes) }}</b></div>
          <div><span>{{ t('wsTest.wireSize') }}</span><b>{{ bytes(feed.wire_bytes) }} ({{ ratio }}×)</b></div>
          <div><span>{{ t('wsTest.buildTime') }}</span><b>{{ feed.build_ms }} ms</b></div>
        </div>
      </section>
    </div>

    <section class="wt-box mt-4">
      <div class="flex items-center justify-between gap-2">
        <h4 class="m-0">{{ t('wsTest.nodes') }}</h4>
        <Button icon="pi pi-refresh" :label="t('wsTest.refresh')" text size="small" @click="loadStatus" />
      </div>
      <template v-if="status">
        <div v-if="status.parent" class="wt-facts mt-3">
          <div><span>{{ t('wsTest.toParent') }}</span><b><Tag :value="status.parent.connected ? t('wsTest.connected') : t('wsTest.notConnected')" :severity="status.parent.connected ? 'success' : 'warn'" /></b></div>
          <div><span>{{ t('wsTest.parentHost') }}</span><b>{{ status.parent.host || '—' }}</b></div>
          <div><span>{{ t('wsTest.rows') }}</span><b>{{ status.parent.rows }}</b></div>
          <div><span>{{ t('wsTest.lastBatch') }}</span><b>{{ when(status.parent.last_batch_at) }}</b></div>
          <div><span>{{ t('wsTest.lastError') }}</span><b>{{ status.parent.last_error || '—' }}</b></div>
        </div>
        <DataTable v-if="status.nodes.length" :value="status.nodes" size="small" class="mt-3">
          <Column field="name" :header="t('wsTest.node')" />
          <Column :header="t('wsTest.websocket')">
            <template #body="{ data }">
              <Tag :value="data.websocket ? t('wsTest.connected') : t('wsTest.notConnected')" :severity="data.websocket ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column :header="t('wsTest.lastSeen')">
            <template #body="{ data }">{{ data.last_seen ? new Date(data.last_seen).toLocaleString() : '—' }}</template>
          </Column>
        </DataTable>
        <p v-else-if="!status.parent" class="text-muted-color mb-0">{{ t('wsTest.noNodes') }}</p>
      </template>
    </section>

    <section class="wt-box mt-4">
      <div class="flex items-center justify-between gap-2">
        <h4 class="m-0">{{ t('wsTest.log') }}</h4>
        <Button icon="pi pi-trash" :label="t('wsTest.clear')" text size="small" @click="log = []" />
      </div>
      <div class="wt-log font-mono text-sm mt-2" dir="ltr">
        <div v-for="(entry, i) in log" :key="i"><span class="text-muted-color">{{ entry.time }}</span> {{ entry.text }}</div>
        <div v-if="!log.length" class="text-muted-color">{{ t('wsTest.empty') }}</div>
      </div>
    </section>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SelectButton from 'primevue/selectbutton'
import { liveCall, liveChoose, liveIssue, liveProtocol, liveReconnect, liveState, liveStream, liveTransport, type LiveChoice, type Subscription } from '@/core/live/live'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()
const { t } = useI18n()

interface Hello {
  pid: number
  threads: number
  protocol: number
  server_time: number
}
interface Feed {
  admins: number
  users: number
  more: boolean
  json_bytes: number
  wire_bytes: number
  build_ms: number
}
interface Status {
  nodes: { name: string; websocket: boolean; last_seen: string | null }[]
  parent: { connected: boolean; host: string; rows: number; last_batch_at: number | null; last_error: string } | null
}

const PUSH_TIMEOUT_MS = 5000
const LOG_SIZE = 200

const error = ref('')
const hello = ref<Hello | null>(null)
const skew = ref('—')
const rtts = ref<number[]>([])
const autoPing = ref(false)
const echoKb = ref(256)
const echoing = ref(false)
const echoResult = ref<{ size: string; ms: string; speed: string } | null>(null)
const pushMs = ref<number | null>(null)
const pushTimedOut = ref(false)
const feedLimit = ref(100)
const feed = ref<Feed | null>(null)
const status = ref<Status | null>(null)
const log = ref<{ time: string; text: string }[]>([])

/** Which way the channel goes: automatic (HTTP/3, then HTTP/2, then a WebSocket), or only one of them. */
const transportChoice = ref<LiveChoice>('auto')
const transportOptions = computed(() => [
  { label: t('wsTest.choice.auto'), value: 'auto' },
  { label: 'HTTP/3', value: 'h3' },
  { label: 'HTTP/2', value: 'h2' },
  { label: 'WebSocket', value: 'ws' },
])
watch(transportChoice, (next) => {
  note(`way: ${next}`)
  liveChoose(next)
})
watch(liveProtocol, (protocol) => protocol && note(`riding ${protocol} (${liveTransport.value})`))

/** Server push: the server sends TICK_COUNT messages on its own; the page asks nothing in between. */
const TICK_COUNT = 5
const TICK_MS = 1000
const ticks = ref<number[]>([])
const gaps = computed(() => ticks.value.slice(1).map((at, i) => at - ticks.value[i]!))
const pushing = ref(false)
const pushVerdict = ref<'ok' | 'missing' | null>(null)
let tickFeed: Subscription | null = null

function startTicks() {
  tickFeed?.stop()
  ticks.value = []
  pushVerdict.value = null
  pushing.value = true
  tickFeed = liveStream<{ n: number }>('ticks', () => ({ count: TICK_COUNT, interval_ms: TICK_MS }), {
    pauseWhenHidden: false,
    onData: (data) => {
      ticks.value = [...ticks.value, performance.now()]
      note(`push ${data.n}/${TICK_COUNT}`)
    },
    onError: (e) => note(`push ✗ ${e.status} ${e.message}`),
    onEnd: () => {
      pushing.value = false
      pushVerdict.value = ticks.value.length === TICK_COUNT ? 'ok' : 'missing'
    },
  })
}

let pingTimer: number | undefined
let pushTimer: number | undefined
let pushStarted: number | null = null
let changes: Subscription | null = null

const stateSeverity = computed(() => ({ idle: 'secondary', connecting: 'info', open: 'success', offline: 'warn' })[liveState.value])
const ratio = computed(() => (feed.value?.wire_bytes ? (feed.value.json_bytes / feed.value.wire_bytes).toFixed(1) : '—'))

function note(text: string) {
  log.value.unshift({ time: new Date().toLocaleTimeString(), text: text.length > 300 ? `${text.slice(0, 300)}…` : text })
  if (log.value.length > LOG_SIZE) log.value.length = LOG_SIZE
}
function ms(value: number | undefined): string {
  return value === undefined ? '—' : `${value.toFixed(1)} ms`
}
function avg(values: number[]): number | undefined {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : undefined
}
function bytes(n: number): string {
  return n >= 1048576 ? `${(n / 1048576).toFixed(2)} MB` : n >= 1024 ? `${(n / 1024).toFixed(1)} KB` : `${n} B`
}
function when(epoch: number | null): string {
  return epoch ? new Date(epoch * 1000).toLocaleTimeString() : '—'
}

async function call<T>(method: string, params: Record<string, unknown> = {}): Promise<T | null> {
  try {
    const result = await liveCall<T>(method, params)
    error.value = ''
    note(`${method} ✓`)
    return result
  } catch (e) {
    error.value = (e as Error).message
    note(`${method} ✗ ${(e as Error).message}`)
    return null
  }
}

async function loadHello() {
  const result = await call<Hello>('hello')
  if (!result) return
  hello.value = result
  skew.value = `${(result.server_time * 1000 - Date.now()).toFixed(0)} ms`
}

async function ping() {
  const started = performance.now()
  if (await call('ping', { t: started })) rtts.value = [...rtts.value.slice(-19), performance.now() - started]
}

async function echo() {
  echoing.value = true
  const started = performance.now()
  const result = await call<{ size: number; data: string }>('echo', { size: echoKb.value * 1024 })
  echoing.value = false
  if (!result) return
  const took = performance.now() - started
  echoResult.value = { size: bytes(result.data.length), ms: took.toFixed(0), speed: `${bytes((result.data.length / took) * 1000)}/s` }
}

async function publish() {
  pushMs.value = null
  pushTimedOut.value = false
  pushStarted = performance.now()
  window.clearTimeout(pushTimer)
  pushTimer = window.setTimeout(() => {
    if (pushStarted !== null) pushTimedOut.value = true
    pushStarted = null
  }, PUSH_TIMEOUT_MS)
  await call('publish')
}

async function loadFeed() {
  feed.value = await call<Feed>('feed', { limit: feedLimit.value })
}

async function loadStatus() {
  status.value = await call<Status>('status')
}

function reconnect() {
  note('reconnect')
  liveReconnect()
}

function open() {
  changes = liveStream<{ tags: string[] }>('changes', () => ({ tags: ['debug', 'user', 'admin_user'] }), {
    onData: (data) => {
      note(`change ${data.tags.join(', ')}`)
      if (pushStarted !== null && data.tags.includes('debug')) {
        pushMs.value = performance.now() - pushStarted
        pushStarted = null
        window.clearTimeout(pushTimer)
      }
    },
    onError: (e) => note(`changes ✗ ${e.status} ${e.message}`),
  })
  void loadHello()
  void loadStatus()
}

function close() {
  if (transportChoice.value !== 'auto') transportChoice.value = 'auto' // the rest of the panel goes back to the usual order
  tickFeed?.stop()
  pushing.value = false
  changes?.stop()
  changes = null
  autoPing.value = false
  window.clearTimeout(pushTimer)
}

watch(() => props.visible, (shown) => (shown ? open() : close()), { immediate: true })
watch(liveState, (state) => note(`connection: ${state}`))
watch(autoPing, (on) => {
  window.clearInterval(pingTimer)
  if (on) pingTimer = window.setInterval(() => liveState.value === 'open' && void ping(), 1000)
})
onBeforeUnmount(() => {
  close()
  window.clearInterval(pingTimer)
})
</script>

<style scoped>
.wt-box {
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  padding: 1rem;
}
.wt-box h4 {
  margin: 0 0 0.75rem;
}
.wt-facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: 0.5rem 1rem;
}
.wt-facts > div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.wt-facts span {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.wt-log {
  max-height: 16rem;
  overflow: auto;
  word-break: break-all;
}
</style>
