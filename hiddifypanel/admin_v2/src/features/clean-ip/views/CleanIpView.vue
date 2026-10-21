<template>
  <PageHeader :title="t('cleanIp.title')" :subtitle="t('cleanIp.subtitle')" />

  <div class="cip">
    <!-- the network this browser is on -->
    <div class="card cip__net">
      <div class="cip__net-main">
        <span class="cip__net-icon"><i class="pi pi-wifi" /></span>
        <div class="min-w-0">
          <div class="cip__label">{{ t('cleanIp.yourNetwork') }}</div>
          <div v-if="net" class="cip__net-name">
            <b>{{ net.short_name !== 'unknown' ? net.short_name : t('cleanIp.unknownIsp') }}</b>
            <span class="text-muted-color ltr"> · AS{{ net.asn }} · {{ net.org }} · {{ net.country.toUpperCase() }}</span>
          </div>
          <div v-else class="text-muted-color">{{ t('cleanIp.loading') }}</div>
        </div>
        <Button icon="pi pi-refresh" text rounded :aria-label="t('cleanIp.refreshNetwork')" v-tooltip.bottom="t('cleanIp.refreshNetwork')" @click="loadNetwork" />
      </div>
      <Message v-if="vpnWarning" severity="warn" :closable="false" class="mt-3">{{ t('cleanIp.vpnWarning') }}</Message>
      <p class="text-muted-color text-sm mt-3 mb-0">{{ t('cleanIp.howItWorks') }}</p>
    </div>

    <div class="cip__grid">
      <!-- scan -->
      <div class="card">
        <h3 class="cip__h">{{ t('cleanIp.scan') }}</h3>
        <div class="cip__fields">
          <label class="cip__field">
            <span>{{ t('cleanIp.perRange') }}</span>
            <InputNumber v-model="perRange" :min="1" :max="64" show-buttons fluid />
          </label>
          <label class="cip__field">
            <span>{{ t('cleanIp.timeout') }}</span>
            <InputNumber v-model="timeoutSec" :min="1" :max="15" show-buttons suffix=" s" fluid />
          </label>
        </div>
        <p class="text-muted-color text-sm">{{ t('cleanIp.estimate', { count: perRange * CLOUDFLARE_RANGES.length, ranges: CLOUDFLARE_RANGES.length }) }}</p>
        <div class="flex gap-2 flex-wrap">
          <Button :label="t('cleanIp.start')" icon="pi pi-play" :disabled="running" @click="start" />
          <Button :label="t('cleanIp.stop')" icon="pi pi-stop" severity="secondary" :disabled="!running" @click="stopping = true" />
        </div>
        <ProgressBar v-if="total" :value="Math.round((done / total) * 100)" class="mt-3" style="height: 6px" :show-value="false" />
        <div v-if="total" class="cip__stats">
          <span>{{ t('cleanIp.tested', { done, total }) }}</span>
          <span class="cip__ok">{{ t('cleanIp.passed', { count: passed.length }) }}</span>
          <span v-if="passed.length">{{ t('cleanIp.best', { ms: passed[0].ms }) }}</span>
        </div>

        <div class="cip__table">
          <table v-if="passed.length">
            <thead>
              <tr>
                <th>{{ t('cleanIp.ip') }}</th>
                <th>{{ t('cleanIp.latency') }}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in passed.slice(0, 200)" :key="row.ip">
                <td class="ltr font-mono">{{ row.ip }}</td>
                <td><span class="cip__ms">{{ row.ms }} ms</span></td>
                <td class="text-end">
                  <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="copy(row.ip)" />
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="cip__empty">{{ total ? (running ? t('cleanIp.scanning') : t('cleanIp.noneFound')) : t('cleanIp.notYet') }}</div>
        </div>
        <Button v-if="passed.length" :label="t('cleanIp.copyAll')" icon="pi pi-copy" text size="small" class="mt-2" @click="copy(passed.map((row) => row.ip).join('\n'))" />
      </div>

      <!-- save to a CDN domain -->
      <div class="card">
        <h3 class="cip__h">{{ t('cleanIp.saveTitle') }}</h3>
        <p class="text-muted-color text-sm mt-0">{{ t('cleanIp.saveHint') }}</p>
        <Message v-if="loaded && !cdnDomains.length" severity="info" :closable="false">{{ t('cleanIp.noCdnDomain') }}</Message>
        <template v-else>
          <div class="cip__fields">
            <label class="cip__field cip__field--wide">
              <span>{{ t('cleanIp.domain') }}</span>
              <Select v-model="domainId" :options="cdnDomains" option-label="domain" option-value="id" fluid />
            </label>
            <label class="cip__field">
              <span>{{ t('cleanIp.isp') }}</span>
              <Select v-model="isp" :options="net?.short_names ?? []" :placeholder="t('cleanIp.pickIsp')" fluid />
            </label>
            <label class="cip__field">
              <span>{{ t('cleanIp.perIsp') }}</span>
              <InputNumber v-model="perIsp" :min="1" :max="20" show-buttons fluid />
            </label>
          </div>
          <label class="cip__field cip__field--wide mt-2">
            <span>{{ t('cleanIp.preview') }}</span>
            <Textarea v-model="preview" rows="7" class="font-mono text-sm" dir="ltr" :auto-resize="false" fluid spellcheck="false" />
          </label>
          <p v-if="note" class="text-muted-color text-sm">{{ note }}</p>
          <div class="flex gap-2 flex-wrap mt-2">
            <Button :label="t('cleanIp.rebuild')" icon="pi pi-sync" severity="secondary" :disabled="!passed.length || !isp" @click="rebuild" />
            <Button :label="t('cleanIp.save')" icon="pi pi-cloud-upload" :loading="saving" :disabled="!domainId || !preview.trim()" @click="save" />
          </div>
        </template>
      </div>
    </div>

    <!-- the full test, with an upload: a command run on another device -->
    <div class="card">
      <h3 class="cip__h"><i class="pi pi-upload" /> {{ t('cleanIp.fullTitle') }}</h3>
      <p class="text-muted-color text-sm mt-0">{{ t('cleanIp.fullHint') }}</p>
      <div class="cip__fields">
        <label class="cip__field">
          <span>{{ t('cleanIp.uploadSize') }}</span>
          <InputNumber v-model="uploadKb" :min="1" :max="64" show-buttons suffix=" KB" fluid />
        </label>
        <label class="cip__field">
          <span>{{ t('cleanIp.perRange') }}</span>
          <InputNumber v-model="fullPerRange" :min="1" :max="64" show-buttons fluid />
        </label>
        <label class="cip__field">
          <span>{{ t('cleanIp.domain') }}</span>
          <Select v-model="domainId" :options="cdnDomains" option-label="domain" option-value="id" fluid />
        </label>
      </div>
      <Button :label="t('cleanIp.makeCommand')" icon="pi pi-code" class="mt-3" :loading="making" :disabled="!domainId" @click="makeCommand" />

      <template v-if="command">
        <div class="cip__cmd">
          <div class="cip__label">{{ t('cleanIp.cmdUnix') }}</div>
          <div class="cip__cmd-row">
            <code class="ltr">{{ command.commands.unix }}</code>
            <Button icon="pi pi-copy" text rounded :aria-label="t('common.copy')" @click="copy(command.commands.unix)" />
          </div>
          <div class="cip__label mt-2">{{ t('cleanIp.cmdWindows') }}</div>
          <div class="cip__cmd-row">
            <code class="ltr">{{ command.commands.windows }}</code>
            <Button icon="pi pi-copy" text rounded :aria-label="t('common.copy')" @click="copy(command.commands.windows)" />
          </div>
          <p class="text-muted-color text-sm mb-0">{{ t('cleanIp.cmdNote') }}</p>
        </div>
        <h4 class="cip__h mt-4">{{ t('cleanIp.received') }}</h4>
        <div v-if="!reports.length" class="cip__empty"><i class="pi pi-spin pi-spinner" /> {{ t('cleanIp.waiting') }}</div>
        <div v-for="report in [...reports].reverse()" :key="report.at" class="cip__report">
          <div class="cip__report-head">
            <b>{{ report.short_name !== 'unknown' ? report.short_name : t('cleanIp.unknownIsp') }}</b>
            <span class="text-muted-color ltr">AS{{ report.asn }} · {{ report.org }} · {{ report.country.toUpperCase() }}</span>
            <span class="text-muted-color">{{ t('cleanIp.reportLine', { tested: report.tested, found: report.ips.length, kb: Math.round(report.size / 1000) }) }}</span>
          </div>
          <div v-if="report.saved.length" class="cip__ok text-sm">✓ {{ t('cleanIp.reportSaved', { count: report.saved.length, isp: report.short_name }) }} <span class="ltr font-mono">{{ report.saved.join(', ') }}</span></div>
          <div v-else-if="report.ips.length" class="text-sm">
            {{ t('cleanIp.reportNotSaved') }}
            <Button :label="t('cleanIp.useThese')" size="small" text @click="useReport(report)" />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import PageHeader from '@/shared/components/PageHeader.vue'
import { apiErrorMessage } from '@/core/api/client'
import { domainsApi, type DomainRow } from '@/features/domains/api'
import { CLOUDFLARE_RANGES, cleanIpApi, mergeCdnIp, probeIp, randomIps, type CleanIpCommand, type CleanIpNetwork, type CleanIpReport } from '../api'

const { t } = useI18n()
const toast = useToast()

const net = ref<CleanIpNetwork | null>(null)
const perRange = ref(4)
const timeoutSec = ref(4)
const running = ref(false)
const stopping = ref(false)
const done = ref(0)
const total = ref(0)
const passed = ref<{ ip: string; ms: number }[]>([])

const domains = ref<DomainRow[]>([])
const loaded = ref(false)
const domainId = ref<number | null>(null)
const isp = ref<string | null>(null)
const perIsp = ref(3)
const preview = ref('')
const note = ref('')
const saving = ref(false)

// the full test: a command for another device, and what its runs sent back
const uploadKb = ref(5)
const fullPerRange = ref(8)
const making = ref(false)
const command = ref<CleanIpCommand | null>(null)
const reports = ref<CleanIpReport[]>([])
let pollTimer = 0

const cdnDomains = computed(() => domains.value.filter((d) => d.mode === 'cdn' || d.mode === 'worker'))
// Another country than the panel's: a VPN is on, so the scan would test the VPN, not the users' ISP
const vpnWarning = computed(() => !!net.value && !!net.value.panel_country && net.value.country !== 'unknown' && net.value.country !== net.value.panel_country)

async function loadNetwork() {
  try {
    net.value = await cleanIpApi.network()
    if (net.value.short_name !== 'unknown') isp.value = net.value.short_name
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 4000 })
  }
}

async function loadDomains() {
  try {
    domains.value = (await domainsApi.list()).domains
    if (!domainId.value && cdnDomains.value.length) domainId.value = cdnDomains.value[0].id
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 4000 })
  } finally {
    loaded.value = true
  }
}

async function start() {
  const ips = CLOUDFLARE_RANGES.flatMap((range) => randomIps(range, perRange.value))
  for (let i = ips.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[ips[i], ips[j]] = [ips[j], ips[i]]
  }
  passed.value = []
  done.value = 0
  total.value = ips.length
  running.value = true
  stopping.value = false
  let next = 0
  const worker = async () => {
    while (next < ips.length && !stopping.value) {
      const ip = ips[next++]
      const result = await probeIp(ip, timeoutSec.value * 1000)
      done.value++
      if (result.ok) {
        passed.value.push({ ip, ms: result.ms })
        passed.value.sort((a, b) => a.ms - b.ms)
      }
    }
  }
  // A dozen at a time: more makes the latencies of a slow phone connection meaningless
  await Promise.all(Array.from({ length: 12 }, worker))
  running.value = false
  rebuild()
}

function rebuild() {
  const domain = domains.value.find((d) => d.id === domainId.value)
  if (!domain) return
  if (!isp.value || !passed.value.length) {
    preview.value = domain.cdn_ip || ''
    note.value = passed.value.length ? t('cleanIp.pickIspFirst') : ''
    return
  }
  const ips = passed.value.slice(0, perIsp.value).map((row) => row.ip)
  const merged = mergeCdnIp(domain.cdn_ip, isp.value, ips, net.value?.short_names ?? [])
  preview.value = merged.text
  note.value =
    t('cleanIp.built', { count: ips.length, isp: isp.value }) +
    (merged.kept ? ' ' + t('cleanIp.kept', { count: merged.kept }) : '') +
    (merged.dropped ? ' ' + t('cleanIp.dropped') : '')
}

async function save() {
  if (!domainId.value) return
  saving.value = true
  try {
    const state = await domainsApi.update(domainId.value, { cdn_ip: preview.value.trim() })
    domains.value = state.domains
    const domain = domains.value.find((d) => d.id === domainId.value)
    toast.add({ severity: 'success', summary: t('cleanIp.saved', { domain: domain?.domain ?? '' }), life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
  } finally {
    saving.value = false
  }
}

async function makeCommand() {
  if (!domainId.value) return
  making.value = true
  try {
    command.value = await cleanIpApi.command({ domain_id: domainId.value, size: uploadKb.value * 1000, per_range: fullPerRange.value, per_isp: perIsp.value })
    reports.value = []
    window.clearInterval(pollTimer)
    pollTimer = window.setInterval(poll, 5000)
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
  } finally {
    making.value = false
  }
}

async function poll() {
  if (!command.value) return
  try {
    const list = await cleanIpApi.reports(command.value.token)
    if (list.length !== reports.value.length) {
      reports.value = list
      // a run saved IPs on the server: show the domain's new value
      if (list.some((report) => report.saved.length)) await loadDomains()
      rebuild()
    }
  } catch {
    window.clearInterval(pollTimer)
  }
}

/** A run from an ISP Hiddify has no name for: its IPs go to the table above, to save under the ISP picked there. */
function useReport(report: CleanIpReport) {
  passed.value = report.ips.map((row) => ({ ip: row.ip, ms: row.ms }))
  total.value = report.tested
  done.value = report.tested
  rebuild()
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    toast.add({ severity: 'warn', summary: text, life: 4000 })
  }
}

watch([domainId, isp, perIsp], () => rebuild())
onMounted(() => {
  loadNetwork()
  loadDomains()
})
onBeforeUnmount(() => {
  stopping.value = true
  window.clearInterval(pollTimer)
})
</script>

<style scoped>
.cip {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.cip .card {
  margin-bottom: 0;
  padding: 1.25rem;
}
.cip__net-main {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.cip__net-main > .min-w-0 {
  flex: 1;
}
.cip__net-icon {
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.cip__label {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.cip__net-name {
  font-size: 1.05rem;
  overflow-wrap: anywhere;
}
.cip__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
}
@media (min-width: 1100px) {
  .cip__grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
.cip__h {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
}
.cip__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}
.cip__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  min-width: 0;
}
.cip__field--wide {
  grid-column: 1 / -1;
}
.cip__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin-top: 0.6rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.cip__ok {
  color: var(--p-green-500);
  font-weight: 600;
}
.cip__table {
  margin-top: 0.75rem;
  max-height: 26rem;
  overflow: auto;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
}
.cip__table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.cip__table th,
.cip__table td {
  padding: 0.45rem 0.75rem;
  text-align: start;
  border-bottom: 1px solid var(--p-content-border-color);
}
.cip__table th {
  position: sticky;
  top: 0;
  background: var(--p-content-background);
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  font-weight: 600;
}
.cip__ms {
  color: var(--p-green-500);
  font-variant-numeric: tabular-nums;
}
.cip__empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}
.cip__cmd {
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, transparent);
}
.cip__cmd-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.cip__cmd-row code {
  flex: 1;
  min-width: 0;
  font-size: 0.8rem;
  padding: 0.5rem 0.65rem;
  border-radius: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  overflow-wrap: anywhere;
}
.cip__report {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
}
.cip__report-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.85rem;
  align-items: baseline;
}
.ltr {
  direction: ltr;
  unicode-bidi: isolate;
}
</style>
