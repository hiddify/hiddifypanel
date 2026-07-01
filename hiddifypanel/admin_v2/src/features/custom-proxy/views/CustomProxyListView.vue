<template>
  <PageHeader :title="t('proxy.listTitle')" />
  <Panel>
    <DataTable
      :value="filteredProxies"
      :loading="loading"
      striped-rows
      paginator
      :rows="10"
      :rows-per-page-options="[10, 25, 50]"
      data-key="id"
    >
      <template #header>
        <div class="flex justify-between items-center flex-wrap gap-3">
          <Button icon="pi pi-refresh" severity="secondary" :aria-label="t('common.search')" @click="load" />
          <Button
            icon="pi pi-file-export"
            :label="t('proxy.generateBundle')"
            severity="secondary"
            @click="bundleDialogVisible = true"
          />
          <Button icon="pi pi-plus" :label="t('proxy.new')" @click="router.push({ name: 'custom-proxy-new' })" />
        </div>
      </template>

      <Column field="name" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.name') }}</span>
            <Button
              icon="pi pi-search"
              text
              rounded
              size="small"
              :severity="filterName ? 'primary' : 'secondary'"
              :aria-label="t('common.search')"
              @click="(e: Event) => namePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <span>{{ data.name }}</span>
        </template>
      </Column>
      <Column field="proto" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.protocol') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterProto ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => protoPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag v-if="data.proto" :value="String(data.proto).toUpperCase()" severity="info" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="mode" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.mode') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterMode ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => modePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          {{ modeLabel(data.mode ?? data.protocol) }}
        </template>
      </Column>
      <Column field="tags">
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.tags') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterTags.length ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => tagsPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag
            v-for="tag in data.tags || []"
            :key="tag"
            :value="tag"
            class="mr-1 mb-1"
            severity="secondary"
          />
          <span v-if="!(data.tags || []).length">—</span>
        </template>
      </Column>
      <Column field="server_core" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.serverCore') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterCore ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => corePopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag v-if="data.server_core" :value="data.server_core" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column >
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('proxy.clientCores') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterClientCore ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => clientPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <Tag v-for="c in data.client_cores || []" :key="c" :value="c" class="mr-1" />
          <span v-if="!(data.client_cores || []).length">—</span>
        </template>
      </Column>
      <Column field="enable" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('common.enabled') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterEnabled !== null ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => enabledPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.enable" @update:model-value="(v: boolean) => toggleEnable(data, v)" />
        </template>
      </Column>
      <Column header="" class="w-52 shrink-0">
        <template #body="{ data }">
          <SysBadge v-if="data.is_builtin" :customized="Boolean(data.server_override || data.client_override)" icon-only class="inline-flex mr-1" />
          <Button icon="pi pi-pencil" text rounded @click="router.push({ name: 'custom-proxy-edit', params: { id: data.id } })" />
          <Button icon="pi pi-copy" text rounded @click="duplicate(data.id)" />
          <Button
            v-if="!data.is_builtin"
            icon="pi pi-trash"
            text
            rounded
            severity="danger"
            @click="confirmDelete(data)"
          />
        </template>
      </Column>
    </DataTable>
  </Panel>

  <Popover ref="tagsPopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('proxy.tags') }}</label>
      <MultiSelect
        v-model="filterTags"
        :options="tagOptions"
        display="chip"
        filter
        show-clear
        class="w-full"
        :placeholder="t('proxy.tagsFilter')"
      />
    </div>
  </Popover>
  <Popover ref="namePopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('proxy.name') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterName" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="protoPopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('proxy.protocol') }}</label>
      <Select v-model="filterProto" :options="protoOptions" option-label="label" option-value="value" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="modePopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('proxy.mode') }}</label>
      <Select v-model="filterMode" :options="modeOptions" option-label="label" option-value="value" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="corePopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('proxy.serverCore') }}</label>
      <Select v-model="filterCore" :options="coreOptions" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="clientPopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('proxy.clientCores') }}</label>
      <Select v-model="filterClientCore" :options="clientCoreOptions" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="enabledPopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('common.enabled') }}</label>
      <Select
        v-model="filterEnabled"
        :options="enabledOptions"
        option-label="label"
        option-value="value"
        show-clear
        class="w-full"
      />
    </div>
  </Popover>

  <GenerateBundleDialog v-model:visible="bundleDialogVisible" :meta="meta" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Popover from 'primevue/popover'
import PageHeader from '@/shared/components/PageHeader.vue'
import SysBadge from '@/shared/components/SysBadge.vue'
import GenerateBundleDialog from '@/features/custom-proxy/components/GenerateBundleDialog.vue'
import { customProxiesApi, type CustomProxy, type CustomProxyMeta } from '@/core/api/generated'

const { t } = useI18n()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const proxies = ref<CustomProxy[]>([])
const meta = ref<CustomProxyMeta | null>(null)
const bundleDialogVisible = ref(false)
const loading = ref(false)
const modeOptions = ref<{ label: string; value: string }[]>([])
const protoOptions = ref<{ label: string; value: string }[]>([])
const coreOptions = ref<string[]>([])
const clientCoreOptions = ref<string[]>([])

const filterTags = ref<string[]>([])
const tagOptions = ref<string[]>([])

const filterName = ref('')
const filterProto = ref<string | null>(null)
const filterMode = ref<string | null>(null)
const filterCore = ref<string | null>(null)
const filterClientCore = ref<string | null>(null)
const filterEnabled = ref<boolean | null>(null)

const tagsPopover = ref()
const namePopover = ref()
const protoPopover = ref()
const modePopover = ref()
const corePopover = ref()
const clientPopover = ref()
const enabledPopover = ref()

const enabledOptions = [
  { label: t('common.enabled'), value: true },
  { label: 'Disabled', value: false },
]

function modeLabel(mode: string | undefined) {
  if (!mode) return '—'
  return t(`proxy.modeLabels.${mode}`, mode)
}

const filteredProxies = computed(() =>
  proxies.value.filter((p) => {
    const mode = p.mode ?? (p as { protocol?: string }).protocol
    const proto = p.proto ?? (p as { protocol?: string }).protocol
    const nameQ = filterName.value.trim().toLowerCase()
    if (nameQ && !(p.name || '').toLowerCase().includes(nameQ) && !(p.slug || '').toLowerCase().includes(nameQ)) {
      return false
    }
    if (filterProto.value && proto !== filterProto.value) return false
    if (filterMode.value && mode !== filterMode.value) return false
    if (filterCore.value && p.server_core !== filterCore.value) return false
    if (filterClientCore.value && !(p.client_cores || []).includes(filterClientCore.value)) return false
    if (filterTags.value.length && !filterTags.value.some((tag) => (p.tags || []).includes(tag))) return false
    if (filterEnabled.value !== null && Boolean(p.enable) !== filterEnabled.value) return false
    return true
  }),
)

async function load() {
  loading.value = true
  try {
    const [list, metaRes] = await Promise.all([customProxiesApi.list(), customProxiesApi.meta()])
    proxies.value = list
    meta.value = metaRes
    modeOptions.value = (metaRes.modes ?? []).map((m) => ({
      label: t(`proxy.modeLabels.${m}`, m),
      value: m,
    }))
    protoOptions.value = (metaRes.protos ?? []).map((p) => ({
      label: p.toUpperCase(),
      value: p,
    }))
    const cores = new Set<string>()
    const clientCores = new Set<string>(metaRes.client_cores ?? [])
    const tags = new Set<string>(metaRes.suggested_tags ?? [])
    for (const p of list) {
      if (p.server_core) cores.add(p.server_core)
      for (const c of p.client_cores ?? []) clientCores.add(c)
      for (const tag of p.tags ?? []) tags.add(tag)
    }
    for (const c of metaRes.server_cores ?? []) cores.add(c)
    coreOptions.value = [...cores].sort()
    clientCoreOptions.value = [...clientCores].sort()
    tagOptions.value = [...tags].sort()
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  } finally {
    loading.value = false
  }
}

async function toggleEnable(row: CustomProxy, enable: boolean) {
  if (!row.id) return
  await customProxiesApi.enable(row.id, enable)
  row.enable = enable
}

async function duplicate(id: number) {
  const copy = await customProxiesApi.duplicate(id)
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  router.push({ name: 'custom-proxy-edit', params: { id: copy.id } })
}

function confirmDelete(row: CustomProxy) {
  confirm.require({
    message: t('common.confirmDelete'),
    header: t('common.delete'),
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      if (!row.id) return
      await customProxiesApi.delete(row.id)
      toast.add({ severity: 'success', summary: t('common.deleted'), life: 3000 })
      await load()
    },
  })
}

onMounted(load)
</script>
