<template>
  <div class="flex flex-col gap-3 mb-5">
    <div class="flex flex-wrap justify-between items-center gap-3">
      <div class="flex items-center gap-2 flex-wrap">
        <Button icon="pi pi-arrow-left" text :label="t('common.back')" @click="router.push({ name: 'custom-proxy-list' })" />
        <h2 class="text-2xl font-semibold m-0">{{ isNew ? t('proxy.new') : form.name }}</h2>
        <SysBadge v-if="isBuiltin" :customized="Boolean(form.server_override || form.client_override)" />
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          v-if="isBuiltin"
          icon="pi pi-copy"
          :label="t('common.duplicate')"
          severity="secondary"
          @click="duplicateBuiltin"
        />
        <Button v-if="!structureLocked || form.server_override || form.client_override" icon="pi pi-upload" :label="t('proxy.import')" severity="secondary" @click="runImport" />
        <Button icon="pi pi-download" :label="t('proxy.export')" severity="secondary" @click="exportDialogVisible = true" />
        <Button icon="pi pi-check-circle" :label="t('common.validate')" severity="secondary" @click="runValidate" />
        <Button icon="pi pi-play" :label="t('proxy.generateExample')" severity="secondary" :disabled="!props.id" @click="exampleDialogVisible = true" />
        <Button icon="pi pi-save" :label="t('common.save')" :loading="saving" @click="save" />
      </div>
    </div>
  </div>

  <Message v-if="isBuiltin" severity="info" :closable="false" class="mb-3">
    {{ t('proxy.builtinDefaultHint') }}
  </Message>

  <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_19rem] gap-4 items-start">
    <div class="min-w-0">
      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="0">{{ t('proxy.tabGeneral') }}</Tab>
          <Tab value="1">{{ t('proxy.tabServer') }}</Tab>
          <Tab value="2">{{ t('proxy.tabClient') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="0">
            <Panel :header="t('proxy.tabGeneral')">
              <HorizontalField :label="t('common.enabled')" input-id="proxy-enable">
                <ToggleSwitch id="proxy-enable" v-model="form.enable!" />
              </HorizontalField>
              <HorizontalField :label="t('proxy.name')" input-id="proxy-name">
                <InputText id="proxy-name" v-model="form.name" class="w-full" @blur="onNameBlur" />
              </HorizontalField>
              <HorizontalField v-if="showCustomPath" :label="t('proxy.customPath')" input-id="proxy-path" :hint="t('proxy.customPathAuto')">
                <InputGroup>
                  <InputGroupAddon><i class="pi pi-link" /></InputGroupAddon>
                  <InputText id="proxy-path" v-model="form.custom_path" class="w-full" />
                  <Button icon="pi pi-refresh" severity="secondary" :aria-label="t('proxy.regeneratePath')" @click="regeneratePath" />
                </InputGroup>
              </HorizontalField>
              <HorizontalField :label="t('proxy.slug')" input-id="proxy-slug">
                <InputGroup>
                  <InputGroupAddon><i class="pi pi-tag" /></InputGroupAddon>
                  <InputText id="proxy-slug" v-model="form.slug" :readonly="structureLocked" />
                </InputGroup>
              </HorizontalField>
              <div :class="{ 'builtin-locked': structureLocked }">
              <HorizontalField :label="t('proxy.mode')" input-id="proxy-mode">
                <Select
                  id="proxy-mode"
                  v-model="form.mode"
                  :options="modeOptions"
                  option-label="label"
                  option-value="value"
                  class="w-full"
                  @change="onModeChange"
                />
              </HorizontalField>
              <HorizontalField v-if="isL7Gateway" :label="t('proxy.l7Proto')" input-id="proxy-l7-proto">
                <Select
                  id="proxy-l7-proto"
                  v-model="form.l7_proto"
                  :options="l7ProtoOptions"
                  option-label="label"
                  option-value="value"
                  class="w-full"
                />
              </HorizontalField>
              <HorizontalField v-if="isL7Gateway" :label="t('proxy.alpn')" input-id="proxy-alpn">
                <MultiSelect
                  id="proxy-alpn"
                  v-model="form.alpns!"
                  :options="alpnOptions"
                  display="chip"
                  filter
                  class="w-full"
                  @update:model-value="syncAlpn"
                />
              </HorizontalField>
              <HorizontalField
                v-if="isL7Gateway && isXhttpProxy"
                :label="t('proxy.downloadAlpns')"
                input-id="proxy-download-alpn"
                :hint="t('proxy.downloadAlpnsHint')"
              >
                <MultiSelect
                  id="proxy-download-alpn"
                  v-model="form.download_alpns!"
                  :options="downloadAlpnOptions"
                  display="chip"
                  filter
                  class="w-full"
                />
              </HorizontalField>
              <HorizontalField :label="t('proxy.tags')" input-id="proxy-tags" :hint="t('proxy.tagsHint')">
                <ProxyTagsMultiSelect
                  id="proxy-tags"
                  v-model="form.tags!"
                  :suggested-tags="meta?.suggested_tags ?? []"
                />
              </HorizontalField>
              <HorizontalField v-if="showDomains && showDomainModes" :label="t('proxy.domainModes')" input-id="proxy-modes">
                <MultiSelect id="proxy-modes" v-model="form.domain_modes" :options="domainModeOptions" display="chip" class="w-full" />
              </HorizontalField>
              <HorizontalField v-if="showDomains && isSniGateway" :label="t('proxy.faketlsDomains')" :hint="t('proxy.faketlsSpecialHint')">
                <FaketlsDomainSelect v-model="form.faketls_domains!" />
              </HorizontalField>
              <HorizontalField v-if="showDomains && showDomainPicker" :label="t('proxy.domainIds')" :hint="t('proxy.domainIdsEmptyAll')">
                <DomainMultiSelect v-model="form.domain_ids!" :domain-modes="form.domain_modes" />
              </HorizontalField>
              </div>
            </Panel>
          </TabPanel>

          <TabPanel value="1">
            <BuiltinStateBar
              v-if="isBuiltin"
              :override="Boolean(form.server_override)"
              :default-label="t('proxy.serverBuiltinDefault')"
              :customized-label="t('proxy.serverBuiltinCustomized')"
              show-toggle
              @update:override="onServerOverrideToggle"
            />
            <div :class="{ 'builtin-locked': serverLocked }">
            <Panel :header="t('proxy.tabServer')">
              <HorizontalField :label="t('proxy.serverCore')" input-id="server-core">
                <Select id="server-core" v-model="form.server_config!.core" :options="meta?.server_cores ?? []" class="w-full" />
              </HorizontalField>
              <HorizontalField v-if="showStaticPorts" :label="t('proxy.inboundTcpPorts')" input-id="server-tcp-ports" :hint="t('proxy.inboundTcpPortsHint')">
                <InputGroup>
                  <InputGroupAddon><i class="pi pi-hashtag" /></InputGroupAddon>
                  <InputText id="server-tcp-ports" v-model="tcpPortsText" class="w-full" placeholder="2080,2081" />
                </InputGroup>
              </HorizontalField>
              <HorizontalField v-if="showStaticPorts" :label="t('proxy.inboundUdpPorts')" input-id="server-udp-ports" :hint="t('proxy.inboundUdpPortsHint')">
                <InputGroup>
                  <InputGroupAddon><i class="pi pi-hashtag" /></InputGroupAddon>
                  <InputText id="server-udp-ports" v-model="udpPortsText" class="w-full" placeholder="2080,2081" />
                </InputGroup>
              </HorizontalField>
              <Message v-if="showAutoPortsHint" severity="info" :closable="false" class="w-full">
                {{ t('proxy.inboundPortAutoCalculated') }}
              </Message>
              <HorizontalField :label="t('proxy.directPortAccess')" input-id="server-direct-port" :hint="t('proxy.directPortAccessHint')">
                <Checkbox id="server-direct-port" v-model="form.server_config!.direct_port_access" binary />
              </HorizontalField>
            </Panel>
            </div>
              <HorizontalField :label="t('proxy.inboundTemplate')">
                <TemplatedEditor
                  v-model="form.server_config!.inbound_template!"
                  :variant="usesJsonTemplate(form.server_config!.core) ? 'json' : 'plain'"
                  :height="usesJsonTemplate(form.server_config!.core) ? '360px' : undefined"
                  :rows="16"
                  :core="form.server_config!.core"
                  category="server_inbound"
                  :explicit-slugs="serverTemplateSlugs"
                  :read-only="serverLocked"
                  @insert-template="onInsertTemplate"
                />
              </HorizontalField>
          </TabPanel>

          <TabPanel value="2">
            <BuiltinStateBar
              v-if="isBuiltin"
              :override="Boolean(form.client_override)"
              :default-label="t('proxy.clientBuiltinDefault')"
              :customized-label="t('proxy.clientBuiltinCustomized')"
              show-toggle
              @update:override="onClientOverrideToggle"
            />
            <div class="flex flex-wrap justify-between items-center gap-2 mb-3">
              <span class="font-medium">{{ t('proxy.clientCoreConfigs') }}</span>
              <Button
                v-if="canEditClientStructure"
                icon="pi pi-plus"
                :label="t('proxy.addClient')"
                size="small"
                @click="openAddClientDialog"
              />
            </div>
            <Tabs v-if="clientCoreTabs.length" v-model:value="activeClientCoreTab">
              <TabList>
                <Tab v-for="core in clientCoreTabs" :key="core" :value="core">{{ core }}</Tab>
              </TabList>
              <TabPanels>
                <TabPanel v-for="core in clientCoreTabs" :key="`panel-${core}`" :value="core">
                  <Accordion
                    :value="expandedClientPanel"
                    @update:value="onClientAccordionChange"
                  >
                    <AccordionPanel
                      v-for="item in clientConfigsForCore(core)"
                      :key="item.globalIndex"
                      :value="String(item.globalIndex)"
                    >
                      <AccordionHeader>{{ clientConfigLabel(item.globalIndex) }}</AccordionHeader>
                      <AccordionContent>
                        <div class="flex flex-col gap-3 pt-2">
                          <div :class="{ 'builtin-locked': clientLocked }">
                            <HorizontalField :label="t('proxy.core')" :input-id="`cc-core-${item.globalIndex}`">
                              <Select
                                :id="`cc-core-${item.globalIndex}`"
                                v-model="item.config.core"
                                :options="clientCoreOptions"
                                class="w-full"
                                @update:model-value="onClientCoreChange(item.globalIndex, $event)"
                              />
                            </HorizontalField>
                            <HorizontalField :label="t('proxy.version')" :input-id="`cc-ver-${item.globalIndex}`">
                              <InputGroup>
                                <InputGroupAddon>≥</InputGroupAddon>
                                <InputText
                                  :id="`cc-ver-${item.globalIndex}`"
                                  v-model="item.config.version"
                                  placeholder="1.10.20"
                                />
                              </InputGroup>
                            </HorizontalField>
                            <HorizontalField
                              v-if="isSublinkCore(item.config.core)"
                              :label="t('proxy.doBase64After')"
                              :input-id="`cc-b64-${item.globalIndex}`"
                            >
                              <Checkbox
                                :id="`cc-b64-${item.globalIndex}`"
                                v-model="item.config.do_base64_after"
                                binary
                              />
                            </HorizontalField>
                          </div>
                          <HorizontalField :label="outboundsTemplateLabel(item.config.core)">
                            <TemplatedEditor
                              v-model="item.config.outbounds_template!"
                              :variant="isSublinkCore(item.config.core) ? 'plain' : (usesJsonTemplate(item.config.core) ? 'json' : 'plain')"
                              :height="!isSublinkCore(item.config.core) && usesJsonTemplate(item.config.core) ? '240px' : undefined"
                              :rows="isSublinkCore(item.config.core) ? 4 : 12"
                              :core="item.config.core"
                              category="client_outbound"
                              :explicit-slugs="clientTemplateSlugs(item.globalIndex)"
                              :show-include="false"
                              :read-only="clientLocked"
                              @insert-template="onInsertTemplate"
                            />
                          </HorizontalField>
                          <Button
                            v-if="canEditClientStructure && (form.client_config!.core_configs?.length ?? 0) > 1"
                            icon="pi pi-trash"
                            :label="t('common.delete')"
                            text
                            severity="danger"
                            @click="removeCore(item.globalIndex)"
                          />
                        </div>
                      </AccordionContent>
                    </AccordionPanel>
                  </Accordion>
                  <Button
                    v-if="canEditClientStructure"
                    icon="pi pi-plus"
                    :label="t('proxy.addClientConfig')"
                    class="mt-3"
                    size="small"
                    text
                    @click="addClientConfigForCore(core)"
                  />
                </TabPanel>
              </TabPanels>
            </Tabs>
            <Message v-else severity="info" :closable="false">
              {{ t('proxy.noClientConfigs') }}
            </Message>
          </TabPanel>
        </TabPanels>
      </Tabs>

      <ValidationPanel :result="validation" />
    </div>

    <TemplateSidePanel
      v-if="showTemplatePanel"
      :core="templatePanelCore"
      :category="templatePanelCategory"
      :template-text="templatePanelText"
      :explicit-slugs="templatePanelSlugs"
      :section-label="templatePanelSectionLabel"
      :allow-create="templatePanelAllowCreate"
      :read-only="templatePanelReadOnly"
      @insert="onInsertTemplate"
      @cloned="onTemplateCloned"
    />
  </div>

  <BundleExportDialog v-model:visible="exportDialogVisible" @confirm="runExport" />
  <GenerateExampleDialog
    v-if="props.id"
    v-model:visible="exampleDialogVisible"
    :proxy-id="Number(props.id)"
    :meta="meta"
  />

  <Dialog
    v-model:visible="addClientDialogVisible"
    modal
    :header="t('proxy.addClient')"
    class="w-full max-w-md"
  >
    <HorizontalField :label="t('proxy.core')" input-id="add-client-core">
      <Select
        id="add-client-core"
        v-model="addClientSelectedCore"
        :options="addClientCoreOptions"
        option-label="label"
        option-value="value"
        class="w-full"
      />
    </HorizontalField>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="addClientDialogVisible = false" />
      <Button :label="t('common.add')" icon="pi pi-plus" @click="confirmAddClient" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Dialog from 'primevue/dialog'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import InputGroup from 'primevue/inputgroup'
import InputGroupAddon from 'primevue/inputgroupaddon'
import SysBadge from '@/shared/components/SysBadge.vue'
import BuiltinStateBar from '@/shared/components/BuiltinStateBar.vue'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import TemplatedEditor from '@/shared/components/TemplatedEditor.vue'
import ValidationPanel from '@/shared/components/ValidationPanel.vue'
import DomainMultiSelect from '@/shared/components/DomainMultiSelect.vue'
import ProxyTagsMultiSelect from '@/shared/components/ProxyTagsMultiSelect.vue'
import FaketlsDomainSelect from '@/shared/components/FaketlsDomainSelect.vue'
import TemplateSidePanel from '@/shared/components/TemplateSidePanel.vue'
import BundleExportDialog from '@/shared/components/BundleExportDialog.vue'
import GenerateExampleDialog from '@/features/custom-proxy/components/GenerateExampleDialog.vue'
import { generateCustomPath } from '@/shared/utils/custom-path'
import { buildIncludeSnippet } from '@/shared/utils/template-slug'
import { SUBLINK_CORE, isSublinkCore, usesJsonTemplate } from '@/shared/utils/core-template'
import { downloadJson, pickFile } from '@/shared/utils/custom-proxy-bundle'
import {
  customProxiesApi,
  type ClientCoreConfig,
  type CustomProxy,
  type CustomProxyMeta,
  type ProxyTemplate,
  type ValidationResult,
} from '@/core/api/generated'

const props = defineProps<{ id?: string }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const isNew = computed(() => route.name === 'custom-proxy-new' || !props.id)
const isBuiltin = computed(() => Boolean(form.is_builtin) && !isNew.value)
const structureLocked = computed(() => isBuiltin.value)
const serverLocked = computed(() => isBuiltin.value && !form.server_override)
const clientLocked = computed(() => isBuiltin.value && !form.client_override)
const meta = ref<CustomProxyMeta | null>(null)
const saving = ref(false)
const exportDialogVisible = ref(false)
const exampleDialogVisible = ref(false)
const validation = ref<ValidationResult | null>(null)
const activeTab = ref('0')
const activeClientIndex = ref(0)
const activeClientCoreTab = ref('')
const expandedClientPanel = ref<string | null>(null)
const addClientDialogVisible = ref(false)
const addClientSelectedCore = ref<string | null>(null)

const canEditClientStructure = computed(() => !structureLocked.value || Boolean(form.client_override))

const clientCoreTabs = computed(() => {
  ensureClientCores()
  const cores = new Set<string>()
  for (const cc of form.client_config?.core_configs ?? []) {
    if (cc.core) cores.add(cc.core)
  }
  const order = meta.value?.client_cores ?? []
  return [...cores].sort((a, b) => {
    const ai = order.indexOf(a)
    const bi = order.indexOf(b)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })
})

const addClientCoreOptions = computed(() =>
  (meta.value?.client_cores ?? []).map((core) => ({ label: core, value: core })),
)

function clientConfigsForCore(core: string) {
  ensureClientCores()
  const items: Array<{ config: ClientCoreConfig; globalIndex: number }> = []
  for (const [idx, cc] of (form.client_config?.core_configs ?? []).entries()) {
    if (cc.core === core) items.push({ config: cc, globalIndex: idx })
  }
  return items
}

function syncActiveClientCoreTab() {
  const tabs = clientCoreTabs.value
  if (!tabs.length) {
    activeClientCoreTab.value = ''
    return
  }
  if (!tabs.includes(activeClientCoreTab.value)) {
    activeClientCoreTab.value = tabs[0]!
  }
}

function outboundsTemplateLabel(core: string) {
  return isSublinkCore(core) ? t('proxy.linkTemplate') : t('proxy.outboundsTemplate')
}

function defaultSublinkCore(): ClientCoreConfig {
  return {
    core: SUBLINK_CORE,
    version: '',
    do_base64_after: false,
    outbounds_template: '',
    template_slugs: [
      'sublink/common/vless_uri',
      'sublink/common/encryption_none',
      'sublink/common/tls_params',
      'sublink/links/vless_tcp',
    ],
  }
}

function applyDefaultSublinkFromMeta() {
  const link = meta.value?.default_sublink_link
  if (!link) return
  ensureClientCores()
  const sub = form.client_config!.core_configs!.find((c) => isSublinkCore(c.core))
  if (sub && !sub.outbounds_template?.trim()) {
    sub.outbounds_template = link
  }
}

const defaultForm = (): CustomProxy => ({
  name: '',
  slug: '',
  enable: true,
  mode: 'domains_l7_gateway',
  l7_proto: 'h2',
  alpns: ['tls_h2'],
  download_alpns: [],
  tags: [],
  domain_modes: ['direct'],
  custom_path: generateCustomPath(),
  domain_ids: [],
  faketls_domains: [],
  server_override: false,
  client_override: false,
  server_config: {
    core: 'xray',
    inbound_tcp_ports: [],
    inbound_udp_ports: [],
    tag: 'tls_h2',
    direct_port_access: false,
    template_slugs: [],
    inbound_template:
      '{\n  "listen": "127.0.0.1",\n  "listen_port": {{ proxy.port }},\n  "tag": "{{ proxy.tag }}"\n}',
  },
  client_config: {
    core_configs: [defaultSublinkCore()],
  },
})

const clientCoreOptions = computed(() => meta.value?.client_cores ?? [])

function ensureClientCores() {
  if (!form.client_config!.core_configs?.length) {
    form.client_config!.core_configs = [defaultSublinkCore()]
  }
  for (const cc of form.client_config!.core_configs ?? []) {
    if (!cc.template_slugs) cc.template_slugs = []
    if (isSublinkCore(cc.core)) {
      if (cc.do_base64_after === undefined) cc.do_base64_after = false
      if (cc.outbounds_template === undefined) cc.outbounds_template = ''
    } else if (!cc.outbounds_template) {
      cc.outbounds_template = '[]'
    }
  }
}

const form = reactive<CustomProxy>(defaultForm())

const domainModeOptions = computed(() => {
  if (form.mode === 'domains_sni_gateway') return ['special']
  if (form.mode === 'domains_l7_gateway') {
    return (meta.value?.domain_modes ?? []).filter((m) => m !== 'special')
  }
  if (form.mode === 'ip') {
    return ['direct', 'relay']
  }
  if (form.mode === 'domains_auto_public_ports' || form.mode === 'domains_single_public_port') {
    return meta.value?.domain_modes ?? ['special']
  }
  return ['special']
})

const showDomains = computed(() => !isIpBased.value)

const isL7Gateway = computed(() => form.mode === 'domains_l7_gateway')
const isXhttpProxy = computed(() => {
  const tags = (form.tags ?? []).map((t) => String(t).toLowerCase())
  if (tags.includes('xhttp')) return true
  const name = `${form.name ?? ''} ${form.slug ?? ''}`.toLowerCase()
  return name.includes('xhttp')
})
const isSniGateway = computed(() => form.mode === 'domains_sni_gateway')
const isMultiDomainAuto = computed(() => form.mode === 'domains_auto_public_ports')
const isSingleDomainStatic = computed(() => form.mode === 'domains_single_public_port')
const isIpBased = computed(() => form.mode === 'ip')
const showStaticPorts = computed(() => isSingleDomainStatic.value || isIpBased.value)
const showAutoPortsHint = computed(
  () => isMultiDomainAuto.value || isL7Gateway.value || isSniGateway.value,
)

function parsePortList(text: string): number[] {
  return text
    .split(/[,;\s]+/)
    .map((part) => Number(part.trim()))
    .filter((port) => Number.isInteger(port) && port > 0)
}

function formatPortList(ports?: number[] | null): string {
  return (ports ?? []).filter((port) => port > 0).join(', ')
}

const tcpPortsText = computed({
  get: () => formatPortList(form.server_config?.inbound_tcp_ports),
  set: (value: string) => {
    if (!form.server_config) return
    form.server_config.inbound_tcp_ports = parsePortList(value)
  },
})

const udpPortsText = computed({
  get: () => formatPortList(form.server_config?.inbound_udp_ports),
  set: (value: string) => {
    if (!form.server_config) return
    const ports = parsePortList(value)
    form.server_config.inbound_udp_ports = ports.length ? ports : [...(form.server_config.inbound_tcp_ports ?? [])]
  },
})

const showCustomPath = computed(() => isL7Gateway.value)

const showDomainModes = computed(() => showDomains.value && isL7Gateway.value)

const showDomainPicker = computed(
  () => showDomains.value && (isL7Gateway.value || isSingleDomainStatic.value),
)

const modeOptions = computed(() =>
  (meta.value?.modes ?? []).map((m) => ({
    value: m,
    label: t(`proxy.modeLabels.${m}`, m),
  })),
)

const alpnOptions = computed(() => meta.value?.alpns ?? [])
const downloadAlpnOptions = computed(() =>
  (meta.value?.alpns ?? []).filter((a) => String(a).startsWith('tls_')),
)

const l7ProtoOptions = computed(() =>
  (meta.value?.l7_protos ?? ['h1', 'h2', 'h3']).map((p) => ({
    value: p,
    label: p.toUpperCase(),
  })),
)

const showClientTemplatePanel = computed(
  () => activeTab.value === '2' && expandedClientPanel.value != null && expandedClientPanel.value !== '',
)

const showTemplatePanel = computed(() => activeTab.value === '1' || showClientTemplatePanel.value)

const templatePanelReadOnly = computed(() => {
  if (!isBuiltin.value) return false
  return activeTab.value === '1' ? !form.server_override : !form.client_override
})

const templatePanelAllowCreate = computed(() => !templatePanelReadOnly.value)

function builtinServerConfig() {
  return form.server_config as NonNullable<CustomProxy['server_config']>
}

function builtinClientConfigs(): ClientCoreConfig[] {
  const client = form.builtin_client_config as { core_configs?: ClientCoreConfig[] } | undefined
  return client?.core_configs ?? []
}

function builtinClientCore(index: number, core?: string): ClientCoreConfig | undefined {
  const configs = builtinClientConfigs()
  if (!configs.length) return undefined
  const cc = clientCoreAt(index)
  const exact = configs.find(
    (c) => c.core === cc.core && (c.version || '') === (cc.version || ''),
  )
  if (exact) return exact
  if (core) {
    const sameCore = configs.filter((c) => c.core === core)
    const local = clientConfigsForCore(core).findIndex((item) => item.globalIndex === index)
    if (local >= 0 && sameCore[local]) return sameCore[local]
    const match = configs.find((c) => c.core === core)
    if (match) return match
  }
  return configs[index]
}

function serverTemplateSlugs(): string[] {
  const slugs = form.server_config?.template_slugs ?? []
  if (isBuiltin.value && !form.server_override) {
    const builtin = builtinServerConfig().template_slugs ?? []
    return builtin.length ? builtin : slugs
  }
  return slugs
}

function clientTemplateSlugs(index: number): string[] {
  const cc = clientCoreAt(index)
  const slugs = cc.template_slugs ?? []
  if (isBuiltin.value && !form.client_override) {
    const builtin = builtinClientCore(index, cc.core)?.template_slugs ?? []
    return builtin.length ? builtin : slugs
  }
  return slugs
}

function clientCoreAt(index: number): ClientCoreConfig {
  ensureClientCores()
  return form.client_config?.core_configs?.[index] ?? { core: SUBLINK_CORE }
}

function formatVersionLabel(version?: string | null): string {
  const ver = version?.trim()
  if (!ver) return ''
  const normalized = ver.replace(/^v/i, '').replace(/^[≥<]=\s*/, '').trim()
  return normalized ? ` ≥ ${normalized}` : ''
}

function clientCoreTitle(index: number) {
  const cc = clientCoreAt(index)
  const core = cc.core ?? ''
  return `${core}${formatVersionLabel(cc.version)}`
}

function clientConfigLabel(index: number) {
  const cc = clientCoreAt(index)
  const ver = cc.version?.trim()
  if (ver) return `${cc.core} ≥ ${ver.replace(/^v/i, '')}`
  const sameCore = clientConfigsForCore(cc.core)
  if (sameCore.length > 1) {
    const pos = sameCore.findIndex((item) => item.globalIndex === index) + 1
    return `${cc.core} #${pos}`
  }
  return cc.core || t('proxy.clientConfigDefault')
}

function defaultVersionForCore(core: string): string {
  ensureClientCores()
  const existing = (form.client_config!.core_configs ?? []).filter((c) => c.core === core)
  if (!existing.some((c) => !c.version?.trim())) return ''
  let n = 1
  while (existing.some((c) => c.version === String(n))) n += 1
  return String(n)
}

function defaultConfigForCore(core: string): ClientCoreConfig {
  if (isSublinkCore(core)) {
    const sub = defaultSublinkCore()
    sub.core = core
    sub.version = defaultVersionForCore(core)
    return sub
  }
  return {
    core,
    version: defaultVersionForCore(core),
    outbounds_template: usesJsonTemplate(core) ? '[]' : '',
    template_slugs: [],
  }
}

function focusClientConfig(globalIndex: number) {
  const cc = clientCoreAt(globalIndex)
  activeClientCoreTab.value = cc.core
  expandedClientPanel.value = String(globalIndex)
  activeClientIndex.value = globalIndex
}

function onClientAccordionChange(value: string | string[] | null | undefined) {
  const id = Array.isArray(value) ? value[0] : value
  expandedClientPanel.value = id ?? null
  if (id != null && id !== '') {
    const idx = Number(id)
    if (!Number.isNaN(idx)) activeClientIndex.value = idx
  }
}

function onClientCoreChange(globalIndex: number, core: string) {
  const cc = clientCoreAt(globalIndex)
  const prevCore = cc.core
  cc.core = core
  if (isSublinkCore(core) && !cc.outbounds_template) {
    const defaults = defaultSublinkCore()
    cc.outbounds_template = defaults.outbounds_template
    cc.template_slugs = defaults.template_slugs
    cc.do_base64_after = defaults.do_base64_after
  } else if (!isSublinkCore(core) && !cc.outbounds_template) {
    cc.outbounds_template = usesJsonTemplate(core) ? '[]' : ''
  }
  activeClientCoreTab.value = core
  expandedClientPanel.value = String(globalIndex)
  activeClientIndex.value = globalIndex
  if (prevCore !== core) syncActiveClientCoreTab()
}

function openAddClientDialog() {
  addClientSelectedCore.value = addClientCoreOptions.value[0]?.value ?? null
  addClientDialogVisible.value = true
}

function confirmAddClient() {
  const core = addClientSelectedCore.value
  if (!core) return
  addClientCore(core)
  addClientDialogVisible.value = false
}

function addClientCore(core: string) {
  ensureClientCores()
  const cfg = defaultConfigForCore(core)
  form.client_config!.core_configs!.push(cfg)
  focusClientConfig(form.client_config!.core_configs!.length - 1)
  syncActiveClientCoreTab()
}

function addClientConfigForCore(core: string) {
  ensureClientCores()
  const cfg = defaultConfigForCore(core)
  cfg.core = core
  form.client_config!.core_configs!.push(cfg)
  focusClientConfig(form.client_config!.core_configs!.length - 1)
}

const templatePanelCore = computed(() => {
  if (activeTab.value === '1') return form.server_config?.core
  return clientCoreAt(activeClientIndex.value).core
})

const templatePanelCategory = computed(() =>
  activeTab.value === '1' ? 'server_inbound' : 'client_outbound',
)

const templatePanelText = computed(() => {
  if (activeTab.value === '1') {
    const tpl = form.server_config?.inbound_template ?? ''
    if (isBuiltin.value && !form.server_override) {
      return builtinServerConfig().inbound_template ?? tpl
    }
    return tpl
  }
  const cc = clientCoreAt(activeClientIndex.value)
  const tpl = cc.outbounds_template ?? ''
  if (isBuiltin.value && !form.client_override) {
    const builtin = builtinClientCore(activeClientIndex.value, cc.core)
    if (builtin) {
      return builtin.outbounds_template ?? tpl
    }
  }
  return tpl
})

const templatePanelSlugs = computed(() => {
  if (activeTab.value === '1') return serverTemplateSlugs()
  return clientTemplateSlugs(activeClientIndex.value)
})

const templatePanelSectionLabel = computed(() => {
  if (activeTab.value === '1') return form.server_config?.core ?? ''
  return clientCoreTitle(activeClientIndex.value)
})

function slugifyName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function onNameBlur() {
  if (!form.slug?.trim() && form.name.trim()) {
    form.slug = slugifyName(form.name)
  }
}

function syncAlpn(alpn?: string[]) {
  const list = (alpn ?? []).filter(Boolean)
  form.alpns = list
  form.server_config!.tag = list[0] ?? ''
}

function regeneratePath() {
  form.custom_path = generateCustomPath()
}

function onModeChange() {
  if (form.mode === 'domains_l7_gateway') {
    if (!form.custom_path?.trim() || form.custom_path === '/random_auto') {
      form.custom_path = generateCustomPath()
    }
    if (!form.l7_proto) {
      form.l7_proto = 'h2'
    }
    if (!form.alpns?.length) {
      syncAlpn(['tls_h2'])
    }
  } else if (form.mode === 'domains_sni_gateway') {
    form.domain_modes = ['special']
    form.custom_path = ''
    form.l7_proto = null
    form.domain_ids = []
  } else if (form.mode === 'ip') {
    form.alpns = ['custom']
    form.custom_path = ''
    form.l7_proto = null
    form.domain_ids = []
    if (!form.domain_modes?.length) {
      form.domain_modes = ['direct']
    }
  } else if (form.mode === 'domains_auto_public_ports') {
    form.alpns = ['custom']
    form.custom_path = ''
    form.l7_proto = null
    form.domain_modes = ['special']
    form.server_config!.inbound_tcp_ports = []
    form.server_config!.inbound_udp_ports = []
  } else if (form.mode === 'domains_single_public_port') {
    form.alpns = ['custom']
    form.custom_path = ''
    form.l7_proto = null
    form.domain_modes = ['special']
  } else if (isL7Gateway.value || isSniGateway.value) {
    form.server_config!.inbound_tcp_ports = []
    form.server_config!.inbound_udp_ports = []
  }
}

function ensureTemplateSlug(slug: string) {
  const slugs = form.server_config!.template_slugs ?? []
  if (!slugs.includes(slug)) {
    form.server_config!.template_slugs = [...slugs, slug]
  }
}

function ensureClientTemplateSlug(idx: number, slug: string) {
  const cc = form.client_config!.core_configs?.[idx]
  if (!cc) return
  const slugs = cc.template_slugs ?? []
  if (!slugs.includes(slug)) {
    cc.template_slugs = [...slugs, slug]
  }
}

function appendInclude(target: 'server' | 'client', slug: string, coreIdx?: number) {
  const snippet = buildIncludeSnippet(slug)
  if (target === 'server') {
    ensureTemplateSlug(slug)
    const tpl = form.server_config!.inbound_template ?? ''
    if (!tpl.includes(snippet)) {
      form.server_config!.inbound_template = (tpl.trim() ? `${tpl}\n` : '') + snippet
    }
    return
  }
  const idx = coreIdx ?? activeClientIndex.value
  const cc = form.client_config!.core_configs?.[idx]
  if (!cc) return
  ensureClientTemplateSlug(idx, slug)
  const tpl = cc.outbounds_template ?? ''
  if (!tpl.includes(snippet)) {
    cc.outbounds_template = (tpl.trim() ? `${tpl}\n` : '') + snippet
  }
}

function onInsertTemplate(tpl: ProxyTemplate) {
  if (activeTab.value === '1') {
    appendInclude('server', tpl.slug)
  } else {
    appendInclude('client', tpl.slug, activeClientIndex.value)
  }
}

function onTemplateCloned() {
  // side panel reloads via TemplateSidePanel
}

async function runExport(excludeBuiltin: boolean) {
  ensureClientCores()
  try {
    const bundle = await customProxiesApi.exportBundle({
      ...form,
      id: props.id ? Number(props.id) : undefined,
      exclude_builtin_templates: excludeBuiltin,
    })
    const name = (form.slug || form.name || 'custom-proxy').replace(/[^a-z0-9_-]+/gi, '-')
    downloadJson(bundle, `${name}.json`)
  } catch {
    toast.add({ severity: 'error', summary: t('proxy.exportFailed'), life: 4000 })
  }
}

async function runImport() {
  const file = await pickFile()
  if (!file) return
  try {
    const bundle = JSON.parse(await file.text())
    const result = await customProxiesApi.importBundle(bundle)
    const proxy = result.proxy
    Object.assign(form, proxy)
    form.server_config = { ...defaultForm().server_config, ...proxy.server_config }
    form.client_config = {
      core_configs: proxy.client_config?.core_configs?.length
        ? proxy.client_config.core_configs
        : [defaultSublinkCore()],
    }
    ensureClientCores()
    syncActiveClientCoreTab()
    if (clientCoreTabs.value.length) {
      focusClientConfig(0)
    }
    toast.add({
      severity: 'success',
      summary: t('proxy.importSuccess', { count: result.templates_imported }),
      life: 4000,
    })
  } catch {
    toast.add({ severity: 'error', summary: t('proxy.importFailed'), life: 4000 })
  }
}

function removeCore(idx: number) {
  if ((form.client_config!.core_configs?.length ?? 0) <= 1) return
  const removedCore = clientCoreAt(idx).core
  form.client_config!.core_configs?.splice(idx, 1)
  ensureClientCores()
  syncActiveClientCoreTab()
  const remaining = clientConfigsForCore(removedCore)
  if (remaining.length) {
    focusClientConfig(remaining[0]!.globalIndex)
  } else if (form.client_config!.core_configs!.length) {
    focusClientConfig(0)
  } else {
    expandedClientPanel.value = null
  }
}

async function load() {
  try {
    meta.value = await customProxiesApi.meta()
    if (!isNew.value && props.id) {
      const data = await customProxiesApi.get(Number(props.id))
      Object.assign(form, data)
      form.server_config = { ...defaultForm().server_config, ...data.server_config }
      if (!form.server_config.inbound_tcp_ports?.length && data.server_config?.inbound_port) {
        form.server_config.inbound_tcp_ports = [data.server_config.inbound_port]
      }
      if (!form.server_config.inbound_udp_ports?.length && form.server_config.inbound_tcp_ports?.length) {
        form.server_config.inbound_udp_ports = [...form.server_config.inbound_tcp_ports]
      }
      if (!form.tags) form.tags = []
      syncAlpn(form.alpns)
      form.client_config = {
        core_configs: data.client_config?.core_configs?.length
          ? data.client_config.core_configs
          : [defaultSublinkCore()],
      }
      ensureClientCores()
      syncActiveClientCoreTab()
      if (clientCoreTabs.value.length) {
        focusClientConfig(0)
      }
      if (form.custom_path === '/random_auto') {
        form.custom_path = generateCustomPath()
      }
    } else {
      applyDefaultSublinkFromMeta()
      syncAlpn(form.alpns)
      ensureClientCores()
      syncActiveClientCoreTab()
      if (clientCoreTabs.value.length) {
        focusClientConfig(0)
      }
    }
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  }
}

async function runValidate() {
  syncAlpn(form.alpns)
  const payload = { ...form, id: props.id ? Number(props.id) : undefined }
  validation.value = props.id
    ? await customProxiesApi.validateById(Number(props.id), payload)
    : await customProxiesApi.validate(payload)
}

function resetServerFromBuiltin() {
  if (form.builtin_server_config) {
    form.server_config = {
      ...form.server_config,
      inbound_template: form.builtin_server_config,
    }
  }
}

function resetClientFromBuiltin() {
  const client = form.builtin_client_config as { core_configs?: ClientCoreConfig[] } | undefined
  if (client && typeof client === 'object') {
    form.client_config = {
      core_configs: client.core_configs?.length ? client.core_configs : [defaultSublinkCore()],
    }
    ensureClientCores()
    syncActiveClientCoreTab()
    if (clientCoreTabs.value.length) {
      focusClientConfig(0)
    }
  }
}

function onServerOverrideToggle(value: boolean) {
  if (!value) resetServerFromBuiltin()
  else if (!form.server_config?.inbound_template?.trim()) resetServerFromBuiltin()
  form.server_override = value
}

function onClientOverrideToggle(value: boolean) {
  if (!value) resetClientFromBuiltin()
  else if (!form.client_config?.core_configs?.length) resetClientFromBuiltin()
  form.client_override = value
}

function buildBuiltinPatch(): Partial<CustomProxy> {
  const patch: Partial<CustomProxy> = {
    name: form.name,
    enable: form.enable,
    tags: form.tags,
    custom_path: form.custom_path,
    server_override: form.server_override,
    client_override: form.client_override,
  }
  if (form.server_override) {
    patch.server_config = form.server_config
  }
  if (form.client_override) {
    patch.client_config = form.client_config
  }
  return patch
}

async function duplicateBuiltin() {
  if (!props.id) return
  const copy = await customProxiesApi.duplicate(Number(props.id))
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  router.push({ name: 'custom-proxy-edit', params: { id: copy.id } })
}

async function save() {
  const needsBodyValidation =
    !isBuiltin.value || form.server_override || form.client_override
  if (needsBodyValidation) {
    ensureClientCores()
    await runValidate()
    if (validation.value && !validation.value.ok) {
      toast.add({ severity: 'error', summary: t('common.validationFailed'), life: 4000 })
      return
    }
  }
  saving.value = true
  try {
    const payload = isBuiltin.value ? buildBuiltinPatch() : form
    if (isNew.value) {
      const created = await customProxiesApi.create(payload as CustomProxy)
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
      router.replace({ name: 'custom-proxy-edit', params: { id: created.id } })
    } else {
      const updated = await customProxiesApi.update(Number(props.id), payload)
      Object.assign(form, updated)
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    }
  } finally {
    saving.value = false
  }
}

watch(
  () => form.domain_ids?.length,
  (count) => {
    if (isSingleDomainStatic.value && (count ?? 0) > 1) {
      toast.add({
        severity: 'warn',
        summary: t('proxy.singleDomainStaticWarning'),
        life: 5000,
      })
    }
  },
)

watch(
  () => form.domain_modes,
  (modes) => {
    if (form.mode === 'domains_sni_gateway' && (!modes?.length || !modes.includes('special'))) {
      form.domain_modes = ['special']
    }
  },
  { deep: true },
)

watch(
  () => form.client_config?.core_configs?.length ?? 0,
  (count) => {
    syncActiveClientCoreTab()
    if (count > 0 && activeClientIndex.value >= count) {
      activeClientIndex.value = count - 1
    }
  },
)

watch(clientCoreTabs, () => {
  syncActiveClientCoreTab()
})

watch(activeTab, (tab) => {
  if (tab === '2') {
    syncActiveClientCoreTab()
    if (expandedClientPanel.value == null && clientCoreTabs.value.length) {
      focusClientConfig(Math.min(activeClientIndex.value, (form.client_config?.core_configs?.length ?? 1) - 1))
    }
  }
})

onMounted(load)
</script>

<style scoped>
.builtin-locked {
  opacity: 0.72;
  pointer-events: none;
}
.client-section-active :deep(.p-panel-header) {
  border-inline-start: 3px solid var(--primary-color);
}
.panel-title-toggle {
  min-height: 1.5rem;
}
</style>
