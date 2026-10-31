<template>
  <PageHeader :title="t('configTester.title')" :subtitle="t('configTester.subtitle')" />
  <TesterRestoreBar />

  <!-- 1. What to test -->
  <Panel class="ct-form">
    <SelectButton v-model="mode" :options="MODES" option-label="key" option-value="key" :allow-empty="false" :disabled="busy" size="small" class="ct-mode" :aria-label="t('configTester.mode.label')">
      <template #option="{ option }"><i :class="option.icon" /> {{ t(`configTester.mode.${option.key}`) }}</template>
    </SelectButton>

    <!-- 1. What to test: a subscription link, or the contents themselves -->
    <div v-if="mode === 'link'" class="ct-field">
      <label for="ct-url" class="ct-label"><span class="ct-step">1</span>{{ t('configTester.url') }}</label>
      <div class="ct-urlrow">
        <UserLinkPicker v-model="url" input-id="ct-url" :disabled="busy" @enter="onUrlEnter" @pick="error = ''" />
        <Button v-if="!busy" icon="pi pi-play" :label="t('configTester.start')" :disabled="!canStart" @click="start" />
        <Button v-else icon="pi pi-stop" :label="t('configTester.stop')" severity="danger" @click="stop" />
      </div>
      <small class="text-muted-color">{{ t('configTester.findHint') }}</small>
    </div>
    <div v-else class="ct-field">
      <label for="ct-content" class="ct-label"><span class="ct-step">1</span>{{ t('configTester.contentLabel') }}</label>
      <!-- Once tested, the contents are shown as the subscription viewer; "Edit text" brings the text back -->
      <template v-if="showViewer">
        <div class="ct-inline-viewer"><SubscriptionViewer :raw="raw" :edited="edits" @edit="onLinkEdit" @test="testEdited" @json-edit="onJsonEdit" @test-all="testAllEdited" /></div>
      </template>
      <Textarea v-else id="ct-content" v-model="content" dir="ltr" class="ct-content font-mono" spellcheck="false" :rows="9" :auto-resize="false" :placeholder="t('configTester.contentPlaceholder')" :disabled="busy" />
      <div class="ct-urlrow ct-urlrow--end">
        <Button v-if="rows.length && !busy" :icon="showViewer ? 'pi pi-file-edit' : 'pi pi-eye'" :label="showViewer ? t('configTester.editText') : t('configTester.showViewer')" severity="secondary" outlined @click="editText = !editText" />
        <Button v-if="!busy" icon="pi pi-play" :label="t('configTester.start')" :disabled="!canStart" @click="start" />
        <Button v-else icon="pi pi-stop" :label="t('configTester.stop')" severity="danger" @click="stop" />
      </div>
    </div>

    <div class="ct-field">
      <label for="ct-app" class="ct-label"><span class="ct-step">2</span>{{ t('configTester.app') }}</label>
      <Select v-model="app" input-id="ct-app" :options="APPS" option-label="label" option-value="key" class="ct-ua" :disabled="busy" @change="onApp" />
      <small class="text-muted-color">{{ t('configTester.appHint') }}</small>
    </div>

    <button type="button" class="ct-adv" :aria-expanded="advanced" @click="advanced = !advanced">
      <i class="pi" :class="advanced ? 'pi-chevron-down' : 'pi-chevron-right'" />{{ t('configTester.advanced') }}
    </button>
    <div v-show="advanced" class="ct-adv-body">
      <div v-if="mode === 'link'" class="ct-field ct-field--wide">
        <label for="ct-ua" class="ct-label">{{ t('configTester.ua') }}</label>
        <InputText id="ct-ua" v-model="userAgent" dir="ltr" class="ct-ua font-mono" spellcheck="false" autocomplete="off" :disabled="busy" />
        <small class="text-muted-color">{{ t('configTester.uaHint') }}</small>
      </div>
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
        <span class="ct-recv__title">{{ fetched?.pasted ? t('configTester.pasted') : t('configTester.sub.received') }} <Tag :value="sourceLabel" severity="info" /></span>
        <span v-if="fetched?.pasted" class="ct-recv__meta">{{ t('configTester.pasted') }} · {{ fmtBytes(fetched.bytes) }} · {{ rows.length }} configs</span>
        <template v-else-if="fetched">
          <span class="ct-recv__meta" dir="ltr" :title="fetched.user_agent">HTTP {{ fetched.status }} · {{ fetched.content_type || '?' }} · {{ fmtBytes(fetched.bytes) }} · {{ rows.length }} configs</span>
          <span class="ct-recv__ua" dir="ltr">{{ fetched.user_agent }}</span>
        </template>
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
    <p v-if="reconnecting" class="ct-reconnect"><i class="pi pi-spin pi-spinner" /> {{ t('configTester.reconnecting') }}</p>
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

    <ProxyHealthCard :results="finishedResults" />

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
            <Tag :value="r.kind === 'xray' ? 'xray' : r.kind === 'clash' ? 'clash' : 'hiddify-core'" severity="secondary" class="ct-kind" />
            <Tag v-if="edits[r.index]" :value="t('configTester.sub.edited')" severity="warn" class="ct-kind" />
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
          <Button icon="pi pi-refresh" text rounded size="small" :disabled="(!r.run_config && !edits[r.index]) || r.state === 'waiting'" :aria-label="t('configTester.rerun')" v-tooltip.top="t('configTester.rerun')" @click="rerunMany([r])" />
          <Button icon="pi pi-search" text rounded size="small" :disabled="!r.run_config && !r.original" :aria-label="t('configTester.open')" v-tooltip.top="t('configTester.open')" @click="detail = r" />
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
        <TabPanel value="configs"><SubscriptionViewer :raw="raw" :edited="edits" @edit="onLinkEdit" @test="testEdited" @json-edit="onJsonEdit" @test-all="testAllEdited" /></TabPanel>
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
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref, shallowRef, type Ref } from 'vue'
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
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import Dialog from 'primevue/dialog'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import PageHeader from '@/shared/components/PageHeader.vue'
import { apiErrorMessage, getHttp } from '@/core/api/client'
import { liveRequest, liveStream, type Subscription } from '@/core/live/live'
import type { Fetched, Json, JobPage, JsonObject, Kind, ResultEvent, Source, TesterEvent } from '@/features/config-tester/types'
import SubscriptionViewer from '@/features/config-tester/components/SubscriptionViewer.vue'
import JsonTree from '@/features/config-tester/components/JsonTree.vue'
import UserLinkPicker from '@/features/config-tester/components/UserLinkPicker.vue'
import { unwrapSubscriptionText } from '@/shared/utils/sublink-pretty'
import CodeBlock from '@/features/config-tester/components/CodeBlock.vue'
import ProxyHealthCard from '@/features/config-tester/components/ProxyHealthCard.vue'
import TesterRestoreBar from '@/features/config-tester/components/TesterRestoreBar.vue'

const { t, locale } = useI18n()
const rtl = computed(() => ['fa', 'ar'].includes(locale.value))
const route = useRoute()
const router = useRouter()

/** The client the subscription is tested for: its user agent fetches the link, and a format it cannot read is an error. */
type App = 'hiddify' | 'xray' | 'clash'
const APPS: { key: App; label: string; ua: string }[] = [
  { key: 'hiddify', label: 'Hiddify v5.0.2', ua: 'HiddifyNext/5.0.2 (linux) like ClashMeta v2ray sing-box' },
  { key: 'xray', label: 'Xray v26.3.27', ua: 'xray/26.3.27' },
  { key: 'clash', label: 'Clash Mihomo 1.92.32', ua: 'clash.meta/1.92.32' },
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
  kind: Kind
  tag?: string
  state: State
  delay_ms?: number
  error?: string
  log?: string
  original?: Json
  run_config?: JsonObject
  /** Pings that worked out of those made in the last test, e.g. `2/3`. */
  passed?: string
  /** A single test run again replaces this history entry. */
  replaceAt?: number
  /** Every result of this config, oldest first (the first test and each test again). */
  history: { at: number; ok: boolean; delay_ms?: number; error?: string }[]
}

const DEFAULT_TEST_URL = 'https://www.gstatic.com/generate_204'
const MODES = [
  { key: 'link', icon: 'pi pi-link' },
  { key: 'content', icon: 'pi pi-file-edit' },
]
const mode = ref<'link' | 'content'>('link')
const content = ref('')
/** Pasted contents: show the text itself (not the viewer) even after a test. */
const editText = ref(true)
const showViewer = computed(() => mode.value === 'content' && rows.value.length > 0 && !editText.value)
const url = ref('')
const app = ref<App>('hiddify')
const userAgent = ref(APPS[0].ua)
const testUrl = ref(DEFAULT_TEST_URL)
const workers = ref(8)
const timeout = ref(10)
const repeats = ref(3)
const advanced = ref(false)
const error = ref('')
const source = ref<Source | ''>('')
// Typed by hand: Vue cannot work out the "unwrapped" type of a recursive JSON value (it never ends), so these are not inferred.
const rows = ref([]) as Ref<Row[]>
const raw = ref('')
/** Share links the admin edited in the viewer, by their place in the list: tested again, they are tested as edited. */
const edits = ref<Record<number, string>>({})
/** The JSON subscription as edited in the viewer (null: not edited); configs tested again are taken from it. */
const jsonEdited = ref<string | null>(null)
const parsed = shallowRef<JsonObject | null>(null)
const fetched = ref<Fetched | null>(null)
const filter = ref<'all' | 'ok' | 'failed'>('all')
const sort = ref<'delay' | 'order' | 'name'>('delay')
const detail = ref(null) as Ref<Row | null>
const historyRow = ref(null) as Ref<Row | null>
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

const controllers = new Map<AbortController, string>()
const active = ref(0)
const busy = computed(() => active.value > 0)
/** URL field text (never assume a string — the picker may briefly hold a user object). */
function urlText(): string {
  const v = url.value as unknown
  if (v && typeof v === 'object' && 'url' in (v as object)) return String((v as { url: string }).url || '')
  return typeof v === 'string' ? v.trim() : ''
}
const canStart = computed(() => (mode.value === 'link' ? !!urlText() : !!content.value.trim()))

const counts = computed(() => ({
  all: rows.value.length,
  ok: rows.value.filter((r) => r.state === 'ok').length,
  failed: rows.value.filter((r) => r.state === 'failed').length,
}))
const doneCount = computed(() => rows.value.filter((r) => r.state === 'ok' || r.state === 'failed' || r.state === 'idle').length)
const pending = computed(() => rows.value.some((r) => r.state === 'waiting'))
/** The results once every config has one (null while testing): the panel's own configs are judged from them. */
const finishedResults = computed(() => {
  if (pending.value || busy.value || !rows.value.length) return null
  const done = rows.value.filter((r) => r.state === 'ok' || r.state === 'failed')
  return done.length ? done.map((r) => ({ name: r.name, ok: r.state === 'ok' })) : null
})
const sourceLabel = computed(() =>
  t(
    `configTester.source${
      source.value === 'xray' ? 'Xray' : source.value === 'core' ? 'Core' : source.value === 'clash' ? 'Clash' : 'Parsed'
    }`,
  ),
)

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

/** Choosing a client puts its user agent in; it can be changed after. */
function onApp() {
  userAgent.value = APPS.find((a) => a.key === app.value)?.ua ?? userAgent.value
}

/** The client a user agent is from (a link opened with only `ua`). */
function appOfUa(ua: string): App {
  return XRAY_UA.test(ua) ? 'xray' : /^(clash|mihomo|stash)/i.test(ua) ? 'clash' : 'hiddify'
}

function onEvent(ev: TesterEvent) {
  if (ev.event === 'start') {
    source.value = ev.source
    raw.value = ev.raw
    if (mode.value === 'content' && !content.value) content.value = ev.raw
    edits.value = {}
    jsonEdited.value = null
    parsed.value = ev.parsed
    fetched.value = ev.fetched
    subTab.value = 'configs'
    rows.value = ev.items.map((i) => ({ ...i, state: 'waiting', history: [] }))
  } else if (ev.event === 'result') {
    onResult(ev)
  } else if (ev.event === 'error') {
    error.value = ev.error
  }
}

function onResult(ev: ResultEvent) {
  const row = rows.value[ev.index]
  if (!row) return
  // Every ping goes in the history. A single test run again takes the place of the one clicked.
  const pings = ev.pings ?? [{ ok: ev.ok, delay_ms: ev.delay_ms, error: ev.error }]
  const entries = pings.map((p) => ({ at: Date.now(), ok: p.ok, delay_ms: p.delay_ms, error: p.error }))
  if (row.replaceAt != null && row.history[row.replaceAt]) row.history[row.replaceAt] = entries[0]
  else row.history.push(...entries)
  row.replaceAt = undefined
  Object.assign(row, { log: ev.log, original: ev.original, run_config: ev.run_config, tag: ev.tag }, summary(row.history, ev.error))
}

/** The HTTP status of a failed call (none for a network error). */
function statusOf(e: unknown): number | undefined {
  return typeof e === 'object' && e !== null && 'response' in e ? (e as { response?: { status?: number } }).response?.status : undefined
}

/** What to tell about a failed call: signed out is said, never acted on by leaving this page. */
function failure(e: unknown): string {
  const status = statusOf(e)
  return status === 401 || status === 403 ? t('configTester.signedOut') : apiErrorMessage(e)
}

const reconnecting = ref(false)

/**
 * Start a test (a job on the server) and follow it. The test does not depend on this page: if the connection drops
 * or the page is reloaded it goes on, and the page picks it up again by its job (kept in the address).
 */
async function stream(body: Record<string, unknown>, remember = false) {
  const controller = new AbortController()
  controllers.set(controller, '')
  active.value++
  try {
    let job = ''
    try {
      const request = { app: app.value, test_url: testUrl.value, workers: workers.value, timeout: timeout.value, repeats: repeats.value, ...body }
      job = (await liveRequest<{ job: string }>('POST', 'config-tester/', { body: request, skipAuthRedirect: true })).job
    } catch (e) {
      if (!controller.signal.aborted) error.value = failure(e)
      return
    }
    if (controller.signal.aborted) return cancel(job) // stopped while it was starting
    controllers.set(controller, job)
    if (remember) rememberJob(job)
    await follow(job, controller)
  } finally {
    finish(controller)
  }
}

function finish(controller: AbortController) {
  controllers.delete(controller)
  active.value--
  reconnecting.value = false
  // What did not get a result (stopped, or the test ended early) is not "waiting" any more.
  if (!active.value) rows.value.forEach((r) => { if (r.state === 'waiting') r.state = r.history.length ? summary(r.history).state : 'idle' })
}

/**
 * Follow the events of a job until it is done: pushed over the live channel as the job adds them; while that is down,
 * read over HTTP (a dropped connection is just tried again, the test goes on without us).
 */
function follow(job: string, controller: AbortController, after = 0, resuming = false): Promise<boolean> {
  return new Promise((resolve) => {
    let seen = false
    let failures = 0
    let over = false
    let feed: Subscription | undefined
    const end = (followed = true) => {
      if (over) return
      over = true
      feed?.stop()
      controller.signal.removeEventListener('abort', onAbort)
      reconnecting.value = false
      resolve(followed)
    }
    const onAbort = () => end()
    const take = (data: JobPage) => {
      seen = true
      failures = 0
      reconnecting.value = false
      data.events.forEach(onEvent)
      after = data.next
      if (data.done) return end()
      if (data.lost) {
        error.value = t('configTester.lost')
        end()
      }
    }
    const refused = (status: number, message: string) => {
      if (status === 404 && resuming && !seen) return end(false) // gone (an hour passed, or the panel forgot it): the caller starts anew
      if (status === 404) error.value = t('configTester.gone')
      else if (status === 401 || status === 403) error.value = t('configTester.signedOut') // the test goes on in the panel; signing in again and reloading shows it
      else error.value = message
      end()
    }
    if (controller.signal.aborted) return end()
    controller.signal.addEventListener('abort', onAbort)
    feed = liveStream<JobPage>('config-tester', () => ({ job, after }), {
      onData: take,
      onError: (e) => {
        if (e.status === 404 || e.status === 401 || e.status === 403) return refused(e.status, e.message)
        if (!e.fallback) return // the server failed this time: the stream goes on over HTTP
        // The panel or the network is away for a moment: keep asking, the test goes on without us.
        failures++
        reconnecting.value = true
        if (failures > 90) refused(0, e.message)
      },
      onEnd: end,
      pauseWhenHidden: false,
      fallbackMs: (n) => (n ? Math.min(500 * n, 4000) : 700),
      fallback: async () => (await getHttp().get<JobPage>(`config-tester/${job}/`, { params: { after }, signal: controller.signal, skipAuthRedirect: true })).data,
    })
  })
}

/** The test is in the address: a reload shows it again (and goes on following it) instead of starting over. */
function rememberJob(job: string) {
  void router.replace({ query: { ...route.query, job } })
}

async function resume(job: string): Promise<boolean> {
  const controller = new AbortController()
  controllers.set(controller, job)
  active.value++
  try {
    return await follow(job, controller, 0, true)
  } finally {
    finish(controller)
  }
}

/** An xray client asks for xray JSON: the panel is told so (force_xray_json=1) even when that subscription is off in its settings. */
const XRAY_UA = /^(xray|v2rayNG|v2rayN|streisand)/i

function subLink(): string {
  const link = urlText()
  if (app.value !== 'xray' && !XRAY_UA.test(userAgent.value.trim())) return link
  try {
    const u = new URL(link)
    u.searchParams.set('force_xray_json', '1')
    return u.toString()
  } catch {
    return link + (link.includes('?') ? '&' : '?') + 'force_xray_json=1'
  }
}

/** Enter starts the test when the field is already a link. */
function onUrlEnter(event: KeyboardEvent) {
  if (!/^https?:\/\//i.test(urlText())) return
  event.preventDefault()
  void start()
}

async function start() {
  if (busy.value || !canStart.value) return
  error.value = ''
  rows.value = []
  detail.value = null
  historyRow.value = null
  filter.value = 'all'
  if (mode.value === 'content') {
    void router.replace({ query: { mode: 'content' } }) // the contents are not put in the address: only the test is
    editText.value = false
    await stream({ content: content.value }, true)
    return
  }
  syncLink()
  await stream({ url: subLink(), user_agent: userAgent.value }, true)
}

function onJsonEdit(text: string, original: string) {
  jsonEdited.value = text === original ? null : text
  if (mode.value === 'content') content.value = text
}

/** Everything tested again from the edited JSON. */
function testAllEdited() {
  subOpen.value = false
  void rerunMany(rows.value)
}

function onLinkEdit(index: number, text: string, original: string) {
  if (text === original) delete edits.value[index]
  else edits.value[index] = text
  if (mode.value === 'content') setContentLine(index, text)
}

/** The pasted contents follow the edits made in the viewer: the same line, changed (base64 contents become plain lines). */
function setContentLine(index: number, text: string) {
  const lines = unwrapSubscriptionText(content.value).text.split(/\r?\n/)
  let n = -1
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i].trim()
    if (!l || l.startsWith('#') || l.startsWith('//')) continue
    if (++n === index) {
      lines[i] = text
      content.value = lines.join('\n')
      return
    }
  }
}

/** "Test this" in the link editor: the edited link, tested now. */
function testEdited(index: number) {
  const row = rows.value.find((r) => r.index === index)
  if (!row) return
  subOpen.value = false
  void rerunMany([row])
}

/** The history dialog: three more tests of this config, or one test again (its own entry is replaced). */
const moreTests = (r: Row) => rerunMany([r], { repeats: 3 })
const oneTestAgain = (r: Row, i: number) => rerunMany([r], { repeats: 1, replaceAt: i })

async function rerunMany(list: Row[], opts: { repeats?: number; replaceAt?: number } = {}) {
  const todo = list.filter((r) => (r.run_config || edits.value[r.index]) && r.state !== 'waiting')
  if (!todo.length || busy.value) return
  error.value = ''
  // A share link edited in the viewer is sent as it is now, to be parsed again; otherwise the config it had.
  // Clash items expect {proxy: oneProxy}; run_config is the full mihomo doc (proxies: [...]).
  const items = todo.map((r) => {
    let config: JsonObject | undefined = r.run_config
    if (r.kind === 'clash') {
      const fromOriginal = r.original && typeof r.original === 'object' && !Array.isArray(r.original) ? (r.original as JsonObject) : undefined
      const fromRun = Array.isArray(r.run_config?.proxies) ? (r.run_config.proxies[0] as JsonObject | undefined) : undefined
      config = { proxy: fromOriginal ?? fromRun }
    }
    return { index: r.index, name: r.name, kind: r.kind, tag: r.tag, original: r.original, config, content: source.value === 'parsed' ? edits.value[r.index] : (jsonEdited.value ?? undefined) }
  })
  todo.forEach((r) => {
    r.state = 'waiting'
    r.replaceAt = opts.replaceAt
  })
  await stream(opts.repeats ? { items, repeats: opts.repeats } : { items })
}

/** Stop a test on the server (it stops by itself too when nobody follows it). */
function cancel(job: string) {
  void liveRequest('DELETE', `config-tester/${job}/`, { skipAuthRedirect: true }).catch(() => undefined)
}

function stop() {
  controllers.forEach((job, c) => {
    c.abort()
    if (job) cancel(job)
  })
}

/** The address carries what is being tested, so a refresh (or a shared link) runs the same test again. */
function syncLink() {
  const query: Record<string, string> = { url: urlText(), app: app.value, ua: userAgent.value, start: '1' }
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
  const job = str(q.job)
  if (q.mode === 'content') mode.value = 'content'
  if (!str(q.url) && !job) return
  url.value = str(q.url)
  app.value = APPS.some((a) => a.key === q.app) ? (q.app as App) : str(q.ua) ? appOfUa(str(q.ua)) : app.value
  userAgent.value = str(q.ua) || (APPS.find((a) => a.key === app.value)?.ua ?? userAgent.value)
  if (str(q.test)) testUrl.value = str(q.test)
  workers.value = num(q.workers, 1, 32) ?? workers.value
  timeout.value = num(q.timeout, 2, 60) ?? timeout.value
  repeats.value = num(q.repeats, 1, 10) ?? repeats.value
  void (async () => {
    // A test already running (or finished) for this address is shown again, not run again.
    if (job && (await resume(job))) {
      editText.value = false
      return
    }
    if (q.start === '1' && str(q.url)) void start()
  })()
})

// Whatever fails inside this page is shown here: nothing leaves the page, reloads it, or takes the panel down with it.
onErrorCaptured((err) => {
  console.error(err)
  error.value = err instanceof Error ? err.message : String(err)
  return false
})

// Leaving the page does not stop the test (it goes on in the panel, and the address brings it back).
onBeforeUnmount(() => controllers.forEach((_job, c) => c.abort()))
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
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: stretch;
}
.ct-urlrow--end {
  justify-content: flex-end;
}
@media (max-width: 640px) {
  .ct-urlrow > .p-button {
    width: 100%;
  }
}
.ct-mode {
  align-self: flex-start;
}
.ct-inline-viewer {
  max-height: 60vh;
  overflow: auto;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
}
.ct-content {
  width: 100%;
  font-size: 0.8rem;
  resize: vertical;
}
.ct-urlrow > :first-child {
  flex: 1;
  min-width: 0;
}
.ct-ua {
  width: 100%;
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
.ct-reconnect {
  margin: 0.6rem 0 0;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
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
