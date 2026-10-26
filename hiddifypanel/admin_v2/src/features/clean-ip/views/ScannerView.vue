<script setup lang="ts">
/** Scanner: Cloudflare IPs that work on the admin's internet (per operator), and the REALITY SNIs' health. */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import { apiErrorMessage } from '@/core/api/client'
import { isSuperAdmin } from '@/core/panelShell'
import { domainsApi, type DomainRow } from '@/features/domains/api'
import PageHeader from '@/shared/components/PageHeader.vue'
import { cleanIpApi, type CleanIpNetwork, type IpReport } from '../api'
import FullTestCard from '../components/FullTestCard.vue'
import FragmentPanel from '../components/FragmentPanel.vue'
import NetworkCard from '../components/NetworkCard.vue'
import RealitySniPanel from '../components/RealitySniPanel.vue'
import IpFlow from '../components/IpFlow.vue'
import { useIpScan, type ScanResult } from '../composables/useIpScan'

type ScannerTab = 'ip' | 'reality' | 'fragment'

const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const scan = useIpScan()

const net = ref<CleanIpNetwork | null>(null)
const netError = ref('')
const domains = ref<DomainRow[]>([])
const loaded = ref(false)
// ?domain=<id> (the domain dialog's scanner link) picks that domain in step 1
const domainId = ref<number | null>(Number(route.query.domain) || null)
const perIsp = ref(3)
const fullOpen = ref(false)

// The tab is in the URL (?tab=reality|fragment): a reload or a shared link opens the same one.
const tab = computed<ScannerTab>({
  get: () => {
    const q = route.query.tab
    if (q === 'fragment') return 'fragment'
    if (q === 'reality' && isSuperAdmin.value) return 'reality'
    return 'ip'
  },
  set: (value) => router.replace({ query: { ...route.query, tab: value === 'ip' ? undefined : value } }),
})

async function loadNetwork() {
  net.value = null
  netError.value = ''
  try {
    net.value = await cleanIpApi.network()
  } catch (e) {
    netError.value = apiErrorMessage(e)
  }
}

async function loadDomains() {
  try {
    const state = await domainsApi.list()
    domains.value = state.domains
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 4000 })
  } finally {
    loaded.value = true
  }
}

function onDomainsSaved(list: DomainRow[]) {
  domains.value = list
}

async function onReports(list: IpReport[]) {
  // a run saved IPs on the server: the domain's field changed
  if (list.some((report) => report.saved.length)) await loadDomains()
}

/** A run from an operator Hiddify has no name for: its IPs go to step 1's list, to save under the operator picked. */
function useReport(results: ScanResult[], tested: number) {
  scan.setResults(results, tested)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    toast.add({ severity: 'warn', summary: text, life: 4000 })
  }
}

onMounted(() => {
  loadNetwork()
  loadDomains()
})
</script>

<template>
  <PageHeader :title="t('cleanIp.title')" :subtitle="t('cleanIp.subtitle')" />

  <div class="scanner">
    <NetworkCard :net="net" :error="netError" @refresh="loadNetwork" />

    <Tabs v-model:value="tab" class="scanner__tabs">
      <TabList>
        <Tab value="ip"><i class="pi pi-bolt" /> {{ t('cleanIp.tabIp') }}</Tab>
        <Tab value="fragment"><i class="pi pi-objects-column" /> {{ t('cleanIp.tabFragment') }}</Tab>
        <Tab v-if="isSuperAdmin" value="reality"><i class="pi pi-shield" /> {{ t('cleanIp.tabReality') }}</Tab>
      </TabList>
    </Tabs>

    <!-- v-show, not v-if: a scan or a full test keeps running while the other tab is open -->
    <div v-show="tab === 'ip'" class="scanner__panel">
      <IpFlow
        v-model:domain-id="domainId"
        v-model:per-isp="perIsp"
        :scan="scan"
        :net="net"
        :domains="domains"
        :loaded="loaded"
        @saved="onDomainsSaved"
        @copy="copy"
      />

      <button type="button" class="scanner__advanced" :class="{ 'scanner__advanced--open': fullOpen }" :aria-expanded="fullOpen" @click="fullOpen = !fullOpen">
        <span class="scanner__advanced-icon"><i class="pi pi-upload" /></span>
        <span class="scanner__advanced-text">
          <b>{{ t('cleanIp.advanced') }}</b>
          <small>{{ t('cleanIp.advancedHint') }}</small>
        </span>
        <span class="scanner__advanced-tag">{{ t('cleanIp.advancedTag') }}</span>
        <i class="pi pi-chevron-down scanner__advanced-chevron" />
      </button>
      <FullTestCard v-show="fullOpen" v-model:domain-id="domainId" :domains="domains" :per-isp="perIsp" :ranges="scan.ranges.value" v-model:ranges-text="scan.rangesText.value" @copy="copy" @reports="onReports" @use="useReport" />
    </div>

    <div v-show="tab === 'fragment'" class="scanner__panel">
      <FragmentPanel v-model:domain-id="domainId" :domains="domains" :loaded="loaded" @saved="onDomainsSaved" />
    </div>

    <div v-if="isSuperAdmin" v-show="tab === 'reality'" class="scanner__panel">
      <RealitySniPanel @copy="copy" />
    </div>
  </div>
</template>

<style scoped>
.scanner {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.scanner__tabs :deep(.p-tablist-tab-list) {
  background: transparent;
}
.scanner__tabs :deep(.p-tab) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.scanner__panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.scanner__advanced {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  inline-size: 100%;
  padding: 1rem 1.25rem;
  font: inherit;
  text-align: start;
  color: inherit;
  cursor: pointer;
  border: 1px dashed color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  border-radius: var(--content-border-radius, 12px);
  background: var(--p-content-background);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}
.scanner__advanced:hover,
.scanner__advanced--open {
  border-style: solid;
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-content-background));
}
.scanner__advanced:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.scanner__advanced-icon {
  inline-size: 2.5rem;
  block-size: 2.5rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.scanner__advanced-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.scanner__advanced-text b {
  font-size: 1rem;
}
.scanner__advanced-text small {
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.scanner__advanced-tag {
  flex: none;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
}
.scanner__advanced-chevron {
  flex: none;
  color: var(--p-text-muted-color);
  transition: transform 0.2s ease;
}
.scanner__advanced--open .scanner__advanced-chevron {
  transform: rotate(180deg);
}
@media (max-width: 575px) {
  .scanner__advanced-tag {
    display: none;
  }
}
</style>
