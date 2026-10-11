<template>
  <PageHeader :title="t('configTester.title')" :subtitle="t('configTester.subtitle')" />

  <!-- 1. What to test -->
  <Panel class="ct-form">
    <div class="ct-field">
      <label for="ct-url" class="ct-label"><span class="ct-step">1</span>{{ t('configTester.url') }}</label>
      <div class="ct-urlrow">
        <InputText id="ct-url" v-model="url" dir="ltr" class="ct-url font-mono" spellcheck="false" autocomplete="off" :placeholder="t('configTester.urlPlaceholder')" :disabled="busy" @keydown.enter="start" />
        <Button v-if="!busy" icon="pi pi-play" :label="t('configTester.start')" :disabled="!url.trim()" @click="start" />
        <Button v-else icon="pi pi-stop" :label="t('configTester.stop')" severity="danger" @click="stop" />
      </div>
    </div>

    <div class="ct-field">
      <label for="ct-ua" class="ct-label"><span class="ct-step">2</span>{{ t('configTester.ua') }}</label>
      <Select id="ct-ua" ref="uaSelect" v-model="userAgent" :options="UA_PRESETS" option-label="value" option-value="value" editable dir="ltr" overlay-class="ct-ua-overlay" :pt="{ overlay: { dir: 'ltr' } }" class="ct-ua font-mono" :disabled="busy" @click="openUa" @focus="openUa">
        <template #option="{ option }">
          <div class="flex flex-col min-w-0" dir="ltr">
            <span class="font-medium">{{ option.label }}</span>
            <span class="text-xs text-muted-color font-mono ct-wrap">{{ option.value }}</span>
          </div>
        </template>
      </Select>
      <small class="text-muted-color">{{ t('configTester.uaHint') }}</small>
    </div>

    <button type="button" class="ct-adv" :aria-expanded="advanced" @click="advanced = !advanced">
      <i class="pi" :class="advanced ? 'pi-chevron-down' : 'pi-chevron-right'" />{{ t('configTester.advanced') }}
    </button>
    <div v-show="advanced" class="ct-adv-body">
      <div class="ct-field ct-field--wide">
        <label for="ct-test" class="ct-label">{{ t('configTester.testUrl') }}</label>
        <InputText id="ct-test" v-model="testUrl" dir="ltr" class="font-mono" spellcheck="false" :disabled="busy" />
      </div>
      <div class="ct-field">
        <label for="ct-workers" class="ct-label">{{ t('configTester.workers') }}</label>
        <InputNumber v-model="workers" input-id="ct-workers" :min="1" :max="32" show-buttons fluid :disabled="busy" />
      </div>
      <div class="ct-field">
        <label for="ct-repeats" class="ct-label">{{ t('configTester.repeats') }}</label>
        <InputNumber v-model="repeats" input-id="ct-repeats" :min="1" :max="10" show-buttons fluid :disabled="busy" />
      </div>
      <div class="ct-field">
        <label for="ct-timeout" class="ct-label">{{ t('configTester.timeout') }}</label>
        <InputNumber v-model="timeout" input-id="ct-timeout" :min="2" :max="60" show-buttons fluid :disabled="busy" />
      </div>
    </div>
    <Message v-if="error" severity="error" class="mt-3" :closable="false">{{ error }}</Message>
  </Panel>

  <!-- 2. Results -->
  <Panel v-if="rows.length" class="mt-4 ct-results">
    <!-- What the panel answered: prominent, opens the subscription viewer -->
    <button type="button" class="ct-recv" @click="subOpen = true">
      <span class="ct-recv__ico"><i class="pi pi-cloud-download" /></span>
      <span class="ct-recv__txt">
        <span class="ct-recv__title">{{ t('configTester.sub.received') }} <Tag :value="sourceLabel" severity="info" /></span>
        <span v-if="fetched" class="ct-recv__meta" dir="ltr" :title="fetched.user_agent">HTTP {{ fetched.status }} · {{ fetched.content_type || '?' }} · {{ fmtBytes(fetched.bytes) }} · {{ rows.length }} configs</span>
        <span v-if="fetched" class="ct-recv__ua" dir="ltr">{{ fetched.user_agent }}</span>
      </span>
      <span class="ct-recv__go">{{ t('configTester.sub.view') }}<i class="pi" :class="rtl ? 'pi-arrow-left' : 'pi-arrow-right'" /></span>
    </button>

    <!-- Counters double as filters -->
    <div class="ct-stats" role="tablist">
      <button v-for="f in FILTERS" :key="f.key" type="button" role="tab" class="ct-stat" :class="[`ct-stat--${f.key}`, { 'is-active': filter === f.key }]" :aria-selected="filter === f.key" @click="filter = f.key">
        <i :class="f.icon" />
        <span class="ct-stat__n">{{ counts[f.key] }}</span>
        <span class="ct-stat__l">{{ t(`configTester.filter.${f.key}`) }}</span>
      </button>
    </div>
    <ProgressBar v-if="pending" :value="Math.round((doneCount * 100) / rows.length)" :show-value="false" class="ct-progress" />

    <div class="ct-toolbar">
      <div class="ct-sort">
        <label for="ct-sort" class="text-sm text-muted-color">{{ t('configTester.sort.label') }}</label>
        <Select v-model="sort" input-id="ct-sort" :options="SORTS" option-value="key" size="small">
          <template #value="{ value }">{{ t(`configTester.sort.${value}`) }}</template>
          <template #option="{ option }">{{ t(`configTester.sort.${option.key}`) }}</template>
        </Select>
      </div>
      <div class="ct-toolbar__btns">
        <Button icon="pi pi-refresh" :label="t('configTester.rerunFailed')" size="small" severity="secondary" outlined :disabled="busy || !counts.failed" @click="rerunMany(rows.filter((r) => r.state === 'failed'))" />
        <Button icon="pi pi-replay" :label="t('configTester.rerunAll')" size="small" severity="secondary" outlined :disabled="busy" @click="rerunMany(rows)" />
      </div>
    </div>

    <ul class="ct-list">
      <li v-for="r in shown" :key="r.index" class="ct-row" :class="`ct-row--${r.state}`">
        <span class="ct-ico" :aria-label="t(`configTester.state.${r.state}`)">
          <i v-if="r.state === 'ok'" class="pi pi-check-circle" />
          <i v-else-if="r.state === 'failed'" class="pi pi-times-circle" />
          <i v-else-if="r.state === 'waiting'" class="pi pi-spin pi-spinner" />
          <i v-else class="pi pi-minus-circle" />
        </span>
        <div class="ct-main">
          <div class="ct-name" dir="ltr">{{ r.name }}</div>
          <div class="ct-sub">
            <Tag :value="r.kind === 'xray' ? 'xray' : 'hiddify-core'" severity="secondary" class="ct-kind" />
            <span v-if="r.state === 'ok'" class="text-muted-color">{{ t('configTester.state.ok') }}<template v-if="r.passed"> · {{ r.passed }}</template></span>
            <span v-else class="text-muted-color">{{ t(`configTester.state.${r.state}`) }}</span>
          </div>
        </div>
        <button v-if="r.history.length && r.state !== 'waiting'" type="button" class="ct-delay" :class="r.state === 'ok' ? `ct-delay--${speed(r.delay_ms ?? 0)}` : 'ct-delay--slow'" dir="ltr" :aria-label="t('configTester.history.title')" v-tooltip.top="t('configTester.history.title')" @click="historyRow = r">
          <template v-if="r.state === 'ok'">{{ r.delay_ms }}<small>ms</small></template>
          <i v-else class="pi pi-times" />
          <span v-if="r.history.length > 1" class="ct-delay__n">×{{ r.history.length }}</span>
        </button>
        <div class="ct-acts">
          <Button icon="pi pi-refresh" text rounded size="small" :disabled="!r.run_config || r.state === 'waiting'" :aria-label="t('configTester.rerun')" v-tooltip.top="t('configTester.rerun')" @click="rerunMany([r])" />
          <Button icon="pi pi-search" text rounded size="small" :disabled="!r.run_config" :aria-label="t('configTester.open')" v-tooltip.top="t('configTester.open')" @click="detail = r" />
        </div>
      </li>
      <li v-if="!shown.length" class="ct-empty">{{ t('configTester.noMatch') }}</li>
    </ul>
  </Panel>

  <Dialog v-model:visible="detailOpen" modal :header="detail?.name" :style="{ width: '60rem', maxWidth: '96vw' }" :breakpoints="{ '640px': '100vw' }" dismissable-mask>
    <Tabs v-if="detail" v-model:value="detailTab" scrollable>
      <TabList>
        <Tab value="log">{{ t('configTester.log') }}</Tab>
        <Tab value="original">{{ t('configTester.original') }}</Tab>
        <Tab value="run">{{ t('configTester.runConfig') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="log"><CodeBlock :text="detail.log || t('configTester.empty')" /></TabPanel>
        <TabPanel value="original"><CodeBlock :text="pretty(detail.original)" /></TabPanel>
        <TabPanel value="run"><CodeBlock :text="pretty(detail.run_config)" /></TabPanel>
      </TabPanels>
    </Tabs>
  </Dialog>

  <Dialog v-model:visible="historyOpen" modal :header="t('configTester.history.header', { name: historyRow?.name ?? '' })" :style="{ width: '34rem', maxWidth: '96vw' }" :breakpoints="{ '640px': '100vw' }" dismissable-mask>
    <template v-if="historyRow">
      <div v-if="historyStats" class="ct-hstats">
        <span><small>{{ t('configTester.history.min') }}</small><b dir="ltr">{{ historyStats.min }} ms</b></span>
        <span><small>{{ t('configTester.history.avg') }}</small><b dir="ltr">{{ historyStats.avg }} ms</b></span>
        <span><small>{{ t('configTester.history.max') }}</small><b dir="ltr">{{ historyStats.max }} ms</b></span>
        <span><small>{{ t('configTester.history.success') }}</small><b dir="ltr">{{ historyStats.okCount }}/{{ historyRow.history.length }}</b></span>
      </div>
      <div class="ct-hist__top">
        <Button icon="pi pi-refresh" :label="t('configTester.history.more')" size="small" :loading="historyRow.state === 'waiting'" :disabled="busy && historyRow.state !== 'waiting'" @click="moreTests(historyRow)" />
      </div>
      <ul class="ct-hist">
        <li v-for="e in historyList" :key="e.index" :class="e.h.ok ? 'is-ok' : 'is-fail'">
          <i class="pi" :class="e.h.ok ? 'pi-check-circle' : 'pi-times-circle'" />
          <span class="ct-hist__time" dir="ltr">{{ new Date(e.h.at).toLocaleTimeString() }}</span>
          <span v-if="e.h.ok" class="ct-hist__ms" dir="ltr">{{ e.h.delay_ms }} ms</span>
          <span v-else class="ct-err ct-hist__err" dir="ltr">{{ e.h.error || t('configTester.state.failed') }}</span>
          <Button icon="pi pi-refresh" text rounded size="small" class="ct-hist__again" :disabled="busy" :aria-label="t('configTester.history.again')" v-tooltip.top="t('configTester.history.again')" @click="oneTestAgain(historyRow, e.index)" />
        </li>
      </ul>
    </template>
  </Dialog>

  <Dialog v-model:visible="subOpen" modal :header="t('configTester.sub.received')" :style="{ width: '64rem', maxWidth: '96vw' }" :breakpoints="{ '640px': '100vw' }" dismissable-mask>
    <Tabs v-model:value="subTab" scrollable>
      <TabList>
        <Tab value="configs">{{ t('configTester.sub.configs') }}</Tab>
        <Tab v-if="parsed" value="parsed">{{ t('configTester.parsed') }}</Tab>
        <Tab value="text">{{ t('configTester.sub.text') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="configs"><SubscriptionViewer :raw="raw" /></TabPanel>
        <TabPanel v-if="parsed" value="parsed">
          <p class="text-sm text-muted-color mt-0">{{ t('configTester.sub.parsedHint') }}</p>
          <div class="ct-treebox"><JsonTree :value="parsed" :open-depth="2" /></div>
        </TabPanel>
        <TabPanel value="text"><CodeBlock :text="raw" /></TabPanel>
      </TabPanels>
    </Tabs>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import PageHeader from '@/shared/components/PageHeader.vue'
import { getApiBase } from '@/core/api/client'
import SubscriptionViewer from '@/features/config-tester/components/SubscriptionViewer.vue'
import JsonTree from '@/features/config-tester/components/JsonTree.vue'
import CodeBlock from '@/features/config-tester/components/CodeBlock.vue'

const { t, locale } = useI18n()
const rtl = computed(() => ['fa', 'ar'].includes(locale.value))
const route = useRoute()
const router = useRouter()

const UA_PRESETS = [
  { label: 'Hiddify (hiddify-core)', value: 'HiddifyNext/5.0.0 (linux) like ClashMeta v2ray sing-box' },
  { label: 'sing-box', value: 'SFA/1.13.0 (sing-box 1.13.0)' },
  { label: 'xray JSON (v2rayNG)', value: 'v2rayNG/1.9.0' },
  { label: 'xray JSON (xray)', value: 'xray/26.3.27' },
  { label: 'Clash Meta', value: 'clash.meta/1.18.0' },
  { label: 'Links (plain)', value: 'Hiddify/2.0 (links)' },
]
const FILTERS = [
  { key: 'all', icon: 'pi pi-list' },
  { key: 'ok', icon: 'pi pi-check-circle' },
  { key: 'failed', icon: 'pi pi-times-circle' },
] as const
const SORTS = [{ key: 'delay' }, { key: 'order' }, { key: 'name' }]

type State = 'waiting' | 'ok' | 'failed' | 'idle'
interface Row {
  index: number
  name: string
  kind: 'xray' | 'core'
  tag?: string
  state: State
  delay_ms?: number
  error?: string
  log?: string
  original?: unknown
  run_config?: unknown
  /** Pings that worked out of those made in the last test, e.g. `2/3`. */
  passed?: string
  /** A single test run again replaces this history entry. */
  replaceAt?: number
  /** Every result of this config, oldest first (the first test and each test again). */
  history: { at: number; ok: boolean; delay_ms?: number; error?: string }[]
}

const DEFAULT_TEST_URL = 'https://www.gstatic.com/generate_204'
const url = ref('')
const userAgent = ref(UA_PRESETS[0].value)
const testUrl = ref(DEFAULT_TEST_URL)
const workers = ref(8)
const timeout = ref(10)
const repeats = ref(3)
const advanced = ref(false)
const error = ref('')
const source = ref('')
const rows = ref<Row[]>([])
const raw = ref('')
const parsed = ref<unknown>(null)
const fetched = ref<{ user_agent: string; status: number; content_type: string; bytes: number } | null>(null)
const filter = ref<'all' | 'ok' | 'failed'>('all')
const sort = ref<'delay' | 'order' | 'name'>('delay')
const detail = ref<Row | null>(null)
const historyRow = ref<Row | null>(null)
const historyOpen = computed({ get: () => !!historyRow.value, set: (v) => { if (!v) historyRow.value = null } })
/** Newest first, with each entry's place in the history. */
const historyList = computed(() => (historyRow.value?.history ?? []).map((h, index) => ({ h, index })).reverse())
const historyStats = computed(() => {
  const ms = (historyRow.value?.history ?? []).filter((h) => h.ok && h.delay_ms != null).map((h) => h.delay_ms as number)
  if (!ms.length) return null
  return { min: Math.min(...ms), max: Math.max(...ms), avg: Math.round(ms.reduce((a, b) => a + b, 0) / ms.length), okCount: ms.length }
})
const detailTab = ref('log')
const subOpen = ref(false)
const subTab = ref('configs')
const detailOpen = computed({ get: () => !!detail.value, set: (v) => { if (!v) detail.value = null } })

const controllers = new Set<AbortController>()
const active = ref(0)
const busy = computed(() => active.value > 0)

const counts = computed(() => ({
  all: rows.value.length,
  ok: rows.value.filter((r) => r.state === 'ok').length,
  failed: rows.value.filter((r) => r.state === 'failed').length,
}))
const doneCount = computed(() => rows.value.filter((r) => r.state === 'ok' || r.state === 'failed' || r.state === 'idle').length)
const pending = computed(() => rows.value.some((r) => r.state === 'waiting'))
const sourceLabel = computed(() => t(`configTester.source${source.value === 'xray' ? 'Xray' : source.value === 'core' ? 'Core' : 'Parsed'}`))

const shown = computed(() => {
  const list = rows.value.filter((r) => filter.value === 'all' || r.state === filter.value)
  const by = sort.value
  if (by === 'order') return list
  if (by === 'name') return [...list].sort((a, b) => a.name.localeCompare(b.name))
  // fastest first; untested and failed ones after
  const rank = (r: Row) => (r.state === 'ok' ? (r.delay_ms ?? 1e9) : r.state === 'waiting' ? 2e9 : 3e9)
  return [...list].sort((a, b) => rank(a) - rank(b))
})

/** State, average delay and "2/3" from all the pings of a config. */
function summary(history: Row['history'], lastError?: string): Pick<Row, 'state' | 'delay_ms' | 'passed' | 'error'> {
  const good = history.filter((h) => h.ok && h.delay_ms != null)
  if (!good.length) return { state: 'failed', delay_ms: undefined, passed: `0/${history.length}`, error: lastError ?? history[history.length - 1]?.error }
  return { state: 'ok', delay_ms: Math.round(good.reduce((a, h) => a + (h.delay_ms as number), 0) / good.length), passed: `${good.length}/${history.length}`, error: undefined }
}

function speed(ms: number): 'fast' | 'mid' | 'slow' {
  return ms < 600 ? 'fast' : ms < 1800 ? 'mid' : 'slow'
}

function fmtBytes(n: number): string {
  return n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`
}

function pretty(value: unknown): string {
  return value == null ? '' : JSON.stringify(value, null, 2)
}

const uaSelect = ref<{ show: () => void; overlayVisible?: boolean } | null>(null)

/** The list opens when the text box is clicked or focused, not only from its arrow. */
function openUa(event?: Event) {
  const el = event?.target as HTMLElement | undefined
  if ((!el || el.tagName === 'INPUT') && !uaSelect.value?.overlayVisible) uaSelect.value?.show()
}

function onEvent(ev: Record<string, any>) {
  if (ev.event === 'start') {
    source.value = ev.source
    raw.value = ev.raw ?? ''
    parsed.value = ev.parsed ?? null
    fetched.value = ev.fetched ?? null
    subTab.value = 'configs'
    rows.value = ev.items.map((i: any) => ({ ...i, state: 'waiting', history: [] }))
  } else if (ev.event === 'result') {
    const row = rows.value[ev.index]
    if (!row) return
    // Every ping goes in the history (old servers send none: then the result itself is one). A single test run again takes the place of the one clicked.
    const pings: { ok: boolean; delay_ms?: number; error?: string }[] = ev.pings ?? [{ ok: !!ev.ok, delay_ms: ev.delay_ms, error: ev.error }]
    const entries = pings.map((p) => ({ at: Date.now(), ok: !!p.ok, delay_ms: p.delay_ms, error: p.error }))
    if (row.replaceAt != null && row.history[row.replaceAt]) row.history[row.replaceAt] = entries[0]
    else row.history.push(...entries)
    row.replaceAt = undefined
    Object.assign(row, { log: ev.log, original: ev.original, run_config: ev.run_config, tag: ev.tag }, summary(row.history, ev.error))
  } else if (ev.event === 'error') {
    error.value = ev.error
  }
}

/** POST and read the NDJSON answer line by line. */
async function stream(body: Record<string, unknown>) {
  const controller = new AbortController()
  controllers.add(controller)
  active.value++
  try {
    const res = await fetch(`${getApiBase()}config-tester/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ test_url: testUrl.value, workers: workers.value, timeout: timeout.value, repeats: repeats.value, ...body }),
    })
    if (!res.ok || !res.body) {
      const data = await res.json().catch(() => null)
      throw new Error(data?.message || data?.detail || `HTTP ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let nl: number
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim()
        buffer = buffer.slice(nl + 1)
        if (line) onEvent(JSON.parse(line))
      }
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') error.value = e?.message || String(e)
  } finally {
    controllers.delete(controller)
    active.value--
    // What did not get a result (stopped, or the request failed) is not "waiting" any more.
    if (!active.value) rows.value.forEach((r) => { if (r.state === 'waiting') r.state = r.history.length ? summary(r.history).state : 'idle' })
  }
}

/** An xray client asks for xray JSON: the panel is told so (force_xray_json=1) even when that subscription is off in its settings. */
const XRAY_UA = /^(xray|v2rayNG|v2rayN|streisand)/i

function subLink(): string {
  const link = url.value.trim()
  if (!XRAY_UA.test(userAgent.value.trim())) return link
  try {
    const u = new URL(link)
    u.searchParams.set('force_xray_json', '1')
    return u.toString()
  } catch {
    return link + (link.includes('?') ? '&' : '?') + 'force_xray_json=1'
  }
}

async function start() {
  if (busy.value || !url.value.trim()) return
  error.value = ''
  rows.value = []
  detail.value = null
  historyRow.value = null
  filter.value = 'all'
  syncLink()
  await stream({ url: subLink(), user_agent: userAgent.value })
}

/** The history dialog: three more tests of this config, or one test again (its own entry is replaced). */
const moreTests = (r: Row) => rerunMany([r], { repeats: 3 })
const oneTestAgain = (r: Row, i: number) => rerunMany([r], { repeats: 1, replaceAt: i })

async function rerunMany(list: Row[], opts: { repeats?: number; replaceAt?: number } = {}) {
  const todo = list.filter((r) => r.run_config && r.state !== 'waiting')
  if (!todo.length || busy.value) return
  error.value = ''
  const items = todo.map((r) => ({ index: r.index, name: r.name, kind: r.kind, tag: r.tag, original: r.original, config: r.run_config }))
  todo.forEach((r) => {
    r.state = 'waiting'
    r.replaceAt = opts.replaceAt
  })
  await stream(opts.repeats ? { items, repeats: opts.repeats } : { items })
}

function stop() {
  controllers.forEach((c) => c.abort())
}

/** The address carries what is being tested, so a refresh (or a shared link) runs the same test again. */
function syncLink() {
  const query: Record<string, string> = { url: url.value.trim(), ua: userAgent.value, start: '1' }
  if (testUrl.value !== DEFAULT_TEST_URL) query.test = testUrl.value
  if (workers.value !== 8) query.workers = String(workers.value)
  if (timeout.value !== 10) query.timeout = String(timeout.value)
  if (repeats.value !== 3) query.repeats = String(repeats.value)
  void router.replace({ query })
}

// Opened from a user's link dialog or by the address: fill the form in, and test when asked.
onMounted(() => {
  const q = route.query
  const str = (v: unknown) => (typeof v === 'string' && v ? v : '')
  const num = (v: unknown, min: number, max: number) => {
    const n = Number(str(v))
    return Number.isFinite(n) && n >= min && n <= max ? n : null
  }
  if (!str(q.url)) return
  url.value = str(q.url)
  if (str(q.ua)) userAgent.value = str(q.ua)
  if (str(q.test)) testUrl.value = str(q.test)
  workers.value = num(q.workers, 1, 32) ?? workers.value
  timeout.value = num(q.timeout, 2, 60) ?? timeout.value
  repeats.value = num(q.repeats, 1, 10) ?? repeats.value
  if (q.start === '1') void start()
})

onBeforeUnmount(stop)
</script>

<style scoped>
.ct-form :deep(.p-panel-content) {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}
.ct-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.ct-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}
.ct-step {
  display: inline-grid;
  place-items: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
}
.ct-urlrow {
  display: flex;
  gap: 0.5rem;
}
.ct-url {
  flex: 1;
  min-width: 0;
}
.ct-ua {
  width: 100%;
}
/* The menu is teleported onto the page, so it would otherwise follow the page direction. */
:global(.ct-ua-overlay) {
  direction: ltr;
  text-align: left;
}
.ct-wrap {
  overflow-wrap: anywhere;
  white-space: normal;
}
.ct-adv {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-primary-color);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.ct-adv-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}
.ct-field--wide {
  grid-column: 1 / -1;
}
.ct-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.9rem;
}
.ct-fetched {
  flex: 1 1 14rem;
  min-width: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.ct-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
}
.ct-stat {
  --tone: var(--p-primary-color);
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas: 'i n' 'i l';
  align-items: center;
  column-gap: 0.6rem;
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.ct-stat--ok {
  --tone: var(--p-green-500, #22c55e);
}
.ct-stat--failed {
  --tone: var(--p-red-500, #ef4444);
}
.ct-stat > i {
  grid-area: i;
  font-size: 1.4rem;
  color: var(--tone);
}
.ct-stat__n {
  grid-area: n;
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.1;
}
.ct-stat__l {
  grid-area: l;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.ct-stat.is-active {
  border-color: var(--tone);
  background: color-mix(in srgb, var(--tone) 10%, var(--p-content-background));
}
.ct-progress {
  height: 0.35rem;
  margin-top: 0.7rem;
}
.ct-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin: 0.9rem 0 0.5rem;
}
.ct-sort,
.ct-toolbar__btns {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.ct-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
  gap: 0.6rem;
}
.ct-row {
  --tone: var(--p-text-muted-color);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  grid-template-areas: 'ico main delay' 'ico sub acts';
  align-items: center;
  gap: 0.15rem 0.7rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 4px solid var(--tone);
  border-radius: 12px;
  background: var(--p-content-background);
  transition: box-shadow 0.15s, transform 0.15s;
}
.ct-row:hover {
  box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--tone) 55%, transparent);
}
.ct-row--ok {
  --tone: var(--p-green-500, #22c55e);
}
.ct-row--failed {
  --tone: var(--p-red-500, #ef4444);
}
.ct-row--waiting {
  --tone: var(--p-primary-color);
}
.ct-ico {
  grid-area: ico;
  align-self: start;
  font-size: 1.3rem;
  color: var(--tone);
  flex-shrink: 0;
}
.ct-main {
  display: contents;
}
.ct-name {
  grid-area: main;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.ct-sub {
  grid-area: sub;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem 0.5rem;
  font-size: 0.78rem;
}
.ct-kind {
  font-size: 0.65rem;
}
.ct-err {
  color: var(--p-red-500, #ef4444);
  overflow-wrap: anywhere;
}
.ct-delay {
  grid-area: delay;
  border: 0;
  font: inherit;
  cursor: pointer;
  justify-self: end;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  background: color-mix(in srgb, var(--d) 16%, transparent);
  color: var(--d);
}
.ct-delay small {
  margin-inline-start: 0.15rem;
  font-weight: 500;
}
.ct-delay--fast {
  --d: var(--p-green-600, #16a34a);
}
.ct-delay--mid {
  --d: var(--p-amber-600, #d97706);
}
.ct-delay--slow {
  --d: var(--p-red-500, #ef4444);
}
.ct-acts {
  grid-area: acts;
  display: flex;
  justify-self: end;
}
.ct-empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--p-text-muted-color);
}
@media (max-width: 640px) {
  .ct-urlrow {
    flex-direction: column;
  }
  .ct-adv-body {
    grid-template-columns: 1fr;
  }
  .ct-stat {
    grid-template-columns: 1fr;
    grid-template-areas: 'n' 'l';
    justify-items: center;
    text-align: center;
    padding: 0.5rem 0.3rem;
  }
  .ct-stat > i {
    display: none;
  }
  .ct-toolbar__btns > * {
    flex: 1 1 auto;
  }
}
.ct-delay__n {
  margin-inline-start: 0.35rem;
  font-size: 0.68rem;
  font-weight: 500;
  opacity: 0.75;
}
.ct-hist__top {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.6rem;
}
.ct-hstats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(6rem, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}
.ct-hstats span {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0.7rem;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.ct-hstats small {
  color: var(--p-text-muted-color);
}
.ct-hist {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 50vh;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.ct-hist li {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.4rem 0.6rem;
  border-inline-start: 4px solid var(--c);
  border-radius: 8px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.08));
}
.ct-hist li.is-ok {
  --c: var(--p-green-500, #22c55e);
}
.ct-hist li.is-fail {
  --c: var(--p-red-500, #ef4444);
}
.ct-hist li > i {
  color: var(--c);
  align-self: center;
}
.ct-hist__time {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.ct-hist__again {
  margin-inline-start: auto;
  align-self: center;
  flex-shrink: 0;
}
.ct-hist__ms {
  margin-inline-start: auto;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.ct-hist__err {
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}
.ct-recv {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  width: 100%;
  margin-bottom: 0.9rem;
  padding: 0.8rem 0.95rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  border-radius: 14px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--p-primary-color) 12%, var(--p-content-background)), var(--p-content-background));
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
}
.ct-recv:hover {
  box-shadow: 0 6px 18px -8px var(--p-primary-color);
  transform: translateY(-1px);
}
.ct-recv__ico {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  font-size: 1.3rem;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
}
.ct-recv__txt {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.ct-recv__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
}
.ct-recv__meta,
.ct-recv__ua {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.ct-recv__ua {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.72rem;
}
.ct-recv__go {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
  font-weight: 600;
  color: var(--p-primary-color);
}
.ct-recv__go i {
  font-size: 0.8rem;
}
.ct-treebox {
  max-height: 60vh;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
@media (max-width: 640px) {
  .ct-recv__go span,
  .ct-recv__go {
    font-size: 0;
  }
  .ct-recv__go i {
    font-size: 1rem;
  }
}
</style>
