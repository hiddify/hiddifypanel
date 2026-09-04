<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Fieldset from 'primevue/fieldset'
import ScrollPanel from 'primevue/scrollpanel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import LineNumberedCode from '@/shared/components/LineNumberedCode.vue'
import {
  customProxiesApi,
  domainsApi,
  type CustomProxyMeta,
  type DomainOption,
  type GeneratedSection,
  type GenerateBundleResult,
  type PanelUserOption,
  type RenderErrorDetail,
  type SublinkFormats,
  type ValidationIssue,
} from '@/core/api/generated'
import {
  formatSectionText,
  sectionSupportsFormatToggle,
  type ConfigFormatView,
} from '@/shared/utils/config-format'
import {
  detailFromIssue,
  detailFromSection,
} from '@/shared/utils/render-error-detail'
import RenderErrorDetailDialog from './RenderErrorDetailDialog.vue'
import SublinkEditor from '@/features/utils/components/SublinkEditor.vue'
import { parseSublinks, type PrettyLink } from '@/shared/utils/sublink-pretty'

const props = defineProps<{
  visible: boolean
  meta: CustomProxyMeta | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const { t } = useI18n()

const loading = ref(false)
const result = ref<GenerateBundleResult | null>(null)
const domains = ref<DomainOption[]>([])
const users = ref<PanelUserOption[]>([])

const domainMode = ref<'pick' | 'custom' | 'all'>('pick')
const userMode = ref<'pick' | 'sample'>('sample')
const uaMode = ref<'preset' | 'custom'>('preset')

const selectedDomainId = ref<number | null>(null)
const customDomain = ref('')
const selectedUserId = ref<number | null>(null)
const ip = ref('203.0.113.1')
const selectedUaId = ref<string | null>(null)
const customUa = ref('')

const activeResultGroup = ref<'servers' | 'clients'>('servers')
const activeDetailTab = ref('0')
const activeXrayConfigByTab = ref<Record<string, number>>({})
const sublinkView = ref<'decoded' | 'raw'>('decoded')
const configFormatView = ref<ConfigFormatView>('json')
const errorDetailVisible = ref(false)
const selectedErrorDetail = ref<RenderErrorDetail | null>(null)

const uaPresets = computed(() => props.meta?.example_user_agents ?? [])

const domainOptions = computed(() =>
  domains.value.map((d) => ({
    value: d.id,
    label: d.alias ? `${d.domain} (${d.alias})` : d.domain,
  })),
)

const userOptions = computed(() =>
  users.value.map((u) => ({
    value: u.id ?? null,
    label: u.name || u.uuid || String(u.id),
  })),
)

const uaOptions = computed(() =>
  uaPresets.value.map((ua) => ({
    value: ua.id,
    label: ua.label,
  })),
)

const sublinkViewOptions = computed(() => [
  { value: 'decoded', label: t('proxy.sublinkFormatDecoded') },
  { value: 'raw', label: t('proxy.sublinkFormatRaw') },
])

const configFormatOptions = computed(() => [
  { value: 'json' as const, label: t('proxy.clashFormatJson') },
  { value: 'yaml' as const, label: t('proxy.clashFormatYaml') },
])

const serverTabs = computed(() =>
  (result.value?.servers ?? []).map((server) => ({
    value: String(server.index ?? 0),
    label: server.label || server.core,
  })),
)

const clientTabs = computed(() =>
  (result.value?.clients ?? []).map((client) => ({
    value: String(client.index ?? 0),
    label: client.label || client.core,
  })),
)

const resultGroupTabs = computed(() => {
  const tabs: Array<{ value: 'servers' | 'clients'; label: string }> = []
  if (serverTabs.value.length) {
    tabs.push({ value: 'servers', label: t('proxy.tabServers') })
  }
  if (clientTabs.value.length) {
    tabs.push({ value: 'clients', label: t('proxy.tabClients') })
  }
  return tabs
})

function resolvedUserAgent(): string {
  if (uaMode.value === 'custom') {
    return customUa.value.trim()
  }
  const preset = uaPresets.value.find((ua) => ua.id === selectedUaId.value)
  return preset?.value ?? uaPresets.value[0]?.value ?? ''
}

function buildPayload() {
  const payload: Record<string, unknown> = {
    ip: ip.value.trim(),
    user_agent: resolvedUserAgent(),
  }
  if (domainMode.value === 'pick' && selectedDomainId.value) {
    payload.domain_id = selectedDomainId.value
    const picked = domains.value.find((d) => d.id === selectedDomainId.value)
    if (picked) payload.domain = picked.domain
  } else if (domainMode.value === 'custom' && customDomain.value.trim()) {
    payload.domain = customDomain.value.trim()
  }
  if (userMode.value === 'pick' && selectedUserId.value) {
    payload.user_id = selectedUserId.value
  }
  return payload
}

async function loadOptions() {
  try {
    const [domainList, userList] = await Promise.all([
      domainsApi.options(),
      customProxiesApi.listUsers().catch(() => []),
    ])
    domains.value = domainList
    users.value = userList
    if (domainList.length && selectedDomainId.value == null) {
      selectedDomainId.value = domainList[0].id
    }
    if (userList.length && selectedUserId.value == null) {
      selectedUserId.value = userList[0].id ?? null
    }
  } catch {
    domains.value = []
    users.value = []
  }
}

async function runGenerate() {
  loading.value = true
  result.value = null
  try {
    const payload = buildPayload()
    result.value = await customProxiesApi.generateBundle(payload)
    if (serverTabs.value.length) {
      activeResultGroup.value = 'servers'
      activeDetailTab.value = serverTabs.value[0]?.value ?? '0'
    } else if (clientTabs.value.length) {
      activeResultGroup.value = 'clients'
      activeDetailTab.value = clientTabs.value[0]?.value ?? '0'
    }
    sublinkView.value = 'decoded'
  } finally {
    loading.value = false
  }
}

function sectionForTab(group: 'servers' | 'clients', tab: string): GeneratedSection | null | undefined {
  if (!result.value) return null
  const idx = Number(tab)
  if (group === 'servers') {
    return result.value.servers.find((s) => s.index === idx) ?? null
  }
  return result.value.clients.find((c) => c.index === idx) ?? null
}

function isSublinkSection(section: GeneratedSection | null | undefined): section is GeneratedSection & {
  sublink_formats: SublinkFormats
} {
  return Boolean(section?.core === 'sublink' && section.sublink_formats)
}

function formatJsonValue(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function tryPrettyJson(text: string): string {
  const trimmed = text.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return text
  }
  try {
    return formatJsonValue(JSON.parse(trimmed))
  } catch {
    return text
  }
}

function isClashSection(section: GeneratedSection | null | undefined): boolean {
  return section?.core === 'clash'
}

function isXrayMultiConfig(section: GeneratedSection | null | undefined): boolean {
  return section?.core === 'xray' && Boolean(section.configs?.length && section.configs.length > 1)
}

function xrayConfigOptions(section: GeneratedSection | null | undefined) {
  return (section?.configs ?? []).map((cfg, idx) => ({
    value: idx,
    label: cfg.variant_label || cfg.label || `${section?.core ?? 'xray'} #${idx + 1}`,
  }))
}

function xrayConfigKey(group: 'servers' | 'clients', tab: string): string {
  return `${group}:${tab}`
}

function xrayConfigIndexForTab(key: string): number {
  return activeXrayConfigByTab.value[key] ?? 0
}

function setXrayConfigIndexForTab(key: string, index: number) {
  activeXrayConfigByTab.value = { ...activeXrayConfigByTab.value, [key]: index }
}

function activeSectionDisplay(
  section: GeneratedSection | null | undefined,
  tabKey: string,
): GeneratedSection | null | undefined {
  if (!section) return section
  if (isXrayMultiConfig(section)) {
    return section.configs?.[xrayConfigIndexForTab(tabKey)] ?? section
  }
  if (section.core === 'xray' && section.configs?.length === 1) {
    return section.configs[0]
  }
  return section
}

function clientSectionForTab(tab: string): GeneratedSection | null | undefined {
  return activeSectionDisplay(sectionForTab('clients', tab), xrayConfigKey('clients', tab))
}

function serverSectionForTab(tab: string): GeneratedSection | null | undefined {
  return activeSectionDisplay(
    sectionForTab('servers', tab),
    xrayConfigKey('servers', tab),
  )
}

function displayText(section: GeneratedSection | null | undefined): string {
  if (!section) return ''
  if (isSublinkSection(section)) {
    return section.sublink_formats.raw || section.rendered || ''
  }
  return formatSectionText(section, configFormatView.value, formatJsonValue, tryPrettyJson)
}

function openErrorDetail(detail: RenderErrorDetail | null | undefined) {
  if (!detail) return
  selectedErrorDetail.value = detail
  errorDetailVisible.value = true
}

function openIssueDetail(issue: ValidationIssue) {
  const section = sectionForIssue(issue)
  openErrorDetail(detailFromIssue(issue, section) ?? { message: issue.message })
}

function sectionForIssue(issue: ValidationIssue): GeneratedSection | null | undefined {
  if (!result.value) return null
  const colon = issue.message.indexOf(': ')
  const prefix = colon >= 0 ? issue.message.slice(0, colon) : ''
  if (!prefix) return null
  const server = result.value.servers.find((item) => item.label === prefix || item.core === prefix)
  if (server) return server
  return result.value.clients.find((item) => item.label === prefix || item.core === prefix) ?? null
}

function openSectionDetail(section: GeneratedSection | null | undefined) {
  if (!section?.error) return
  openErrorDetail(detailFromSection(section))
}

function issueHasDetail(issue: ValidationIssue): boolean {
  return Boolean(issue.message)
}

function sectionHasDetail(section: GeneratedSection | null | undefined): boolean {
  return Boolean(section?.error)
}

function parsedSublinkLinks(section: GeneratedSection | null | undefined): PrettyLink[] {
  if (!isSublinkSection(section)) return []
  return parseSublinks(section.sublink_formats.raw || section.rendered || '')
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    result.value = null
    activeXrayConfigByTab.value = {}
    if (!selectedUaId.value && uaPresets.value.length) {
      selectedUaId.value = uaPresets.value[0].id
    }
    void loadOptions()
  },
)

watch(uaPresets, (list) => {
  if (!selectedUaId.value && list.length) {
    selectedUaId.value = list[0].id
  }
})

watch(activeResultGroup, () => {
  const tabs = activeResultGroup.value === 'servers' ? serverTabs.value : clientTabs.value
  activeDetailTab.value = tabs[0]?.value ?? '0'
  sublinkView.value = 'decoded'
  configFormatView.value = 'json'
})

watch(activeDetailTab, () => {
  sublinkView.value = 'decoded'
  configFormatView.value = 'json'
})
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    class="w-full max-w-5xl"
    :header="t('proxy.generateBundle')"
    :close-on-escape="!errorDetailVisible"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <HorizontalField :label="t('proxy.exampleDomain')" input-id="bundle-domain-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="bundle-domain-mode"
            v-model="domainMode"
            :options="[
              { value: 'pick', label: t('proxy.exampleDomainPick') },
              { value: 'custom', label: t('proxy.exampleDomainCustom') },
              { value: 'all', label: t('proxy.exampleDomainAll') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="domainMode === 'pick'"
            v-model="selectedDomainId"
            :options="domainOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('proxy.exampleDomainPick')"
            class="w-full"
          />
          <InputText
            v-else-if="domainMode === 'custom'"
            v-model="customDomain"
            :placeholder="t('proxy.exampleDomainCustom')"
            class="w-full"
          />
          <Message v-else severity="secondary" :closable="false" class="w-full">
            {{ t('proxy.exampleDomainAllHint') }}
          </Message>
        </div>
      </HorizontalField>

      <HorizontalField :label="t('proxy.exampleUser')" input-id="bundle-user-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="bundle-user-mode"
            v-model="userMode"
            :options="[
              { value: 'sample', label: t('proxy.exampleUserSample') },
              { value: 'pick', label: t('proxy.exampleUserPick') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="userMode === 'pick'"
            v-model="selectedUserId"
            :options="userOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('proxy.exampleUserPick')"
            class="w-full"
          />
        </div>
      </HorizontalField>

      <HorizontalField :label="t('proxy.exampleIp')" input-id="bundle-ip">
        <InputText id="bundle-ip" v-model="ip" class="w-full" />
      </HorizontalField>

      <HorizontalField :label="t('proxy.exampleUserAgent')" input-id="bundle-ua-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="bundle-ua-mode"
            v-model="uaMode"
            :options="[
              { value: 'preset', label: t('proxy.exampleUaPreset') },
              { value: 'custom', label: t('proxy.exampleUaCustom') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="uaMode === 'preset'"
            v-model="selectedUaId"
            :options="uaOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <InputText v-else v-model="customUa" :placeholder="t('proxy.exampleUaCustom')" class="w-full" />
        </div>
      </HorizontalField>

      <div class="flex justify-end gap-2">
        <Button :label="t('proxy.generateBundle')" icon="pi pi-play" :loading="loading" @click="runGenerate" />
      </div>

      <template v-if="result">
        <Message v-if="result.ok" severity="success">{{ t('proxy.generateBundleOk') }}</Message>
        <Message v-else severity="warn">{{ t('proxy.generateBundlePartial') }}</Message>

        <Fieldset v-if="result.context" :legend="t('proxy.exampleContext')">
          <ul class="m-0 pl-4 text-sm">
            <li>{{ t('proxy.bundleContextProxyCount') }}: {{ result.context.proxy_count }}</li>
            <li>{{ t('proxy.exampleContextDomain') }}: {{ result.context.domain }}</li>
            <li>{{ t('proxy.exampleContextUser') }}: {{ result.context.user }}</li>
            <li>{{ t('proxy.exampleContextIp') }}: {{ result.context.ip }}</li>
            <li>{{ t('proxy.exampleContextUa') }}: {{ result.context.user_agent }}</li>
          </ul>
        </Fieldset>

        <Fieldset v-if="result.warnings?.length" :legend="t('validation.warnings')">
          <ul class="m-0 pl-4">
            <li v-for="(w, i) in result.warnings" :key="'warn-' + i">{{ w.message }}</li>
          </ul>
        </Fieldset>

        <Fieldset v-if="result.errors?.length" :legend="t('validation.errors')">
          <ul class="m-0 pl-4">
            <li
              v-for="(e, i) in result.errors"
              :key="'err-' + i"
              :class="{ 'render-error-link': issueHasDetail(e) }"
              @click="openIssueDetail(e)"
            >
              {{ e.message }}
              <span v-if="issueHasDetail(e)" class="render-error-link__hint">
                {{ t('proxy.renderErrorClickHint') }}
              </span>
            </li>
          </ul>
        </Fieldset>

        <Tabs v-if="resultGroupTabs.length" v-model:value="activeResultGroup">
          <TabList>
            <Tab v-for="tab in resultGroupTabs" :key="tab.value" :value="tab.value">{{ tab.label }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="servers">
              <Tabs v-if="serverTabs.length" v-model:value="activeDetailTab">
                <TabList>
                  <Tab v-for="tab in serverTabs" :key="tab.value" :value="tab.value">{{ tab.label }}</Tab>
                </TabList>
                <TabPanels>
                  <TabPanel v-for="tab in serverTabs" :key="tab.value" :value="tab.value">
                    <Message
                      v-if="sectionForTab('servers', tab.value)?.skipped"
                      severity="info"
                      :closable="false"
                      class="mb-2"
                    >
                      SKIP
                    </Message>
                    <Message
                      v-else-if="sectionForTab('servers', tab.value)?.error"
                      severity="error"
                      :closable="false"
                      class="mb-2"
                      :class="{ 'render-error-banner': sectionHasDetail(sectionForTab('servers', tab.value)) }"
                      @click="openSectionDetail(sectionForTab('servers', tab.value))"
                    >
                      {{ sectionForTab('servers', tab.value)?.error }}
                      <span
                        v-if="sectionHasDetail(sectionForTab('servers', tab.value))"
                        class="render-error-link__hint"
                      >
                        {{ t('proxy.renderErrorClickHint') }}
                      </span>
                    </Message>
                    <div v-if="isXrayMultiConfig(sectionForTab('servers', tab.value))" class="mb-3">
                      <Select
                        :model-value="xrayConfigIndexForTab(xrayConfigKey('servers', tab.value))"
                        :options="xrayConfigOptions(sectionForTab('servers', tab.value))"
                        option-label="label"
                        option-value="value"
                        class="w-full"
                        @update:model-value="setXrayConfigIndexForTab(xrayConfigKey('servers', tab.value), $event)"
                      />
                    </div>
                    <div
                      v-if="sectionSupportsFormatToggle(serverSectionForTab(tab.value))"
                      class="mb-3"
                    >
                      <Select
                        v-model="configFormatView"
                        :options="configFormatOptions"
                        option-label="label"
                        option-value="value"
                        class="w-full max-w-xs"
                      />
                    </div>
                    <ScrollPanel class="config-scroll-panel" :style="{ width: '100%', height: '320px' }">
                      <LineNumberedCode :text="displayText(serverSectionForTab(tab.value))" />
                    </ScrollPanel>
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </TabPanel>
            <TabPanel value="clients">
              <Tabs v-if="clientTabs.length" v-model:value="activeDetailTab">
                <TabList>
                  <Tab v-for="tab in clientTabs" :key="tab.value" :value="tab.value">{{ tab.label }}</Tab>
                </TabList>
                <TabPanels>
                  <TabPanel v-for="tab in clientTabs" :key="tab.value" :value="tab.value">
                    <Message
                      v-if="clientSectionForTab(tab.value)?.skipped"
                      severity="info"
                      :closable="false"
                      class="mb-2"
                    >
                      SKIP
                    </Message>
                    <Message
                      v-else-if="clientSectionForTab(tab.value)?.error"
                      severity="error"
                      :closable="false"
                      class="mb-2"
                      :class="{ 'render-error-banner': sectionHasDetail(clientSectionForTab(tab.value)) }"
                      @click="openSectionDetail(clientSectionForTab(tab.value))"
                    >
                      {{ clientSectionForTab(tab.value)?.error }}
                      <span
                        v-if="sectionHasDetail(clientSectionForTab(tab.value))"
                        class="render-error-link__hint"
                      >
                        {{ t('proxy.renderErrorClickHint') }}
                      </span>
                    </Message>
                    <Message
                      v-else-if="isSublinkSection(clientSectionForTab(tab.value)) && clientSectionForTab(tab.value)?.sublink_formats?.parse_error"
                      severity="warn"
                      :closable="false"
                      class="mb-2"
                    >
                      {{ clientSectionForTab(tab.value)?.sublink_formats?.parse_error }}
                    </Message>
                    <div v-if="isXrayMultiConfig(sectionForTab('clients', tab.value))" class="mb-3">
                      <Select
                        :model-value="xrayConfigIndexForTab(xrayConfigKey('clients', tab.value))"
                        :options="xrayConfigOptions(sectionForTab('clients', tab.value))"
                        option-label="label"
                        option-value="value"
                        class="w-full"
                        @update:model-value="setXrayConfigIndexForTab(xrayConfigKey('clients', tab.value), $event)"
                      />
                    </div>
                    <div v-if="isSublinkSection(clientSectionForTab(tab.value))" class="mb-3">
                      <Select
                        v-model="sublinkView"
                        :options="sublinkViewOptions"
                        option-label="label"
                        option-value="value"
                        class="w-full max-w-xs"
                      />
                    </div>
                    <div
                      v-else-if="sectionSupportsFormatToggle(clientSectionForTab(tab.value))"
                      class="mb-3"
                    >
                      <Select
                        v-model="configFormatView"
                        :options="configFormatOptions"
                        option-label="label"
                        option-value="value"
                        class="w-full max-w-xs"
                      />
                    </div>
                    <SublinkEditor
                      v-if="isSublinkSection(clientSectionForTab(tab.value)) && sublinkView === 'decoded'"
                      :links="parsedSublinkLinks(clientSectionForTab(tab.value))"
                      :id-prefix="`bundle-${tab.value}-`"
                      readonly
                    />
                    <ScrollPanel v-else class="config-scroll-panel" :style="{ width: '100%', height: '320px' }">
                      <LineNumberedCode :text="displayText(clientSectionForTab(tab.value))" />
                    </ScrollPanel>
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>
    </div>
  </Dialog>

  <RenderErrorDetailDialog v-model:visible="errorDetailVisible" :detail="selectedErrorDetail" />
</template>

<style scoped>
.config-scroll-panel :deep(.p-scrollpanel-content) {
  user-select: text;
}

.render-error-link {
  cursor: pointer;
}

.render-error-link:hover {
  text-decoration: underline;
}

.render-error-link__hint {
  margin-left: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.8;
}

.render-error-banner {
  cursor: pointer;
}
</style>
