<template>
  <PageHeader :title="t('baseConfig.listTitle')" />
  <Panel>
    <DataTable
      :value="filteredConfigs"
      :loading="loading"
      striped-rows
      paginator
      :rows="15"
      :rows-per-page-options="[10, 25, 50]"
      data-key="id"
    >
      <template #header>
        <div class="flex justify-between items-center flex-wrap gap-3">
          <Button icon="pi pi-refresh" severity="secondary" :aria-label="t('common.search')" @click="load" />
          <Button icon="pi pi-plus" :label="t('baseConfig.new')" @click="router.push({ name: 'base-config-new' })" />
        </div>
      </template>

      <Column field="name" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('baseConfig.name') }}</span>
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
      </Column>
      <Column field="description" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('baseConfig.description') }}</span>
            <Button
              icon="pi pi-search"
              text
              rounded
              size="small"
              :severity="filterDescription ? 'primary' : 'secondary'"
              :aria-label="t('common.search')"
              @click="(e: Event) => descriptionPopover.toggle(e)"
            />
          </div>
        </template>
      </Column>
      <Column field="side" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('baseConfig.side') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterSide ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => sidePopover.toggle(e)"
            />
          </div>
        </template>
      </Column>
      <Column field="core" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('baseConfig.core') }}</span>
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
          <Tag :value="data.core" />
        </template>
      </Column>
      <Column field="version" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('baseConfig.version') }}</span>
            <Button
              icon="pi pi-search"
              text
              rounded
              size="small"
              :severity="filterVersion ? 'primary' : 'secondary'"
              :aria-label="t('common.search')"
              @click="(e: Event) => versionPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <span v-if="data.version">≥ {{ data.version }}</span>
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
          <ToggleSwitch :model-value="data.enable !== false" @update:model-value="(v: boolean) => toggleEnable(data, v)" />
        </template>
      </Column>
      <Column header="" class="w-48 shrink-0">
        <template #body="{ data }">
          <SysBadge v-if="data.is_builtin" :customized="data.builtin_override" icon-only class="mr-1" />
          <Button icon="pi pi-pencil" text rounded @click="router.push({ name: 'base-config-edit', params: { id: data.id } })" />
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

  <Popover ref="namePopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('baseConfig.name') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterName" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="descriptionPopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('baseConfig.description') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterDescription" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="sidePopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('baseConfig.side') }}</label>
      <Select v-model="filterSide" :options="sideOptions" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="corePopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('baseConfig.core') }}</label>
      <Select v-model="filterCore" :options="coreFilterOptions" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="versionPopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('baseConfig.version') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterVersion" :placeholder="t('common.search')" class="w-full" />
      </IconField>
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
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Popover from 'primevue/popover'
import PageHeader from '@/shared/components/PageHeader.vue'
import SysBadge from '@/shared/components/SysBadge.vue'
import { proxyBaseConfigsApi, type ProxyBaseConfig, type ProxyBaseConfigMeta } from '@/core/api/generated'

const { t } = useI18n()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const configs = ref<ProxyBaseConfig[]>([])
const meta = ref<ProxyBaseConfigMeta | null>(null)
const loading = ref(false)

const filterName = ref('')
const filterDescription = ref('')
const filterSide = ref<string | null>(null)
const filterCore = ref<string | null>(null)
const filterVersion = ref('')
const filterEnabled = ref<boolean | null>(null)

const namePopover = ref()
const descriptionPopover = ref()
const sidePopover = ref()
const corePopover = ref()
const versionPopover = ref()
const enabledPopover = ref()

const sideOptions = computed(() => meta.value?.sides ?? [])
const coreFilterOptions = computed(() => {
  const set = new Set<string>()
  if (filterSide.value && meta.value) {
    for (const c of meta.value.cores_by_side[filterSide.value] ?? []) set.add(c)
  }
  for (const row of configs.value) {
    if (filterSide.value && row.side !== filterSide.value) continue
    if (row.core) set.add(row.core)
  }
  return [...set].sort()
})

const enabledOptions = [
  { label: t('common.enabled'), value: true },
  { label: 'Disabled', value: false },
]

const filteredConfigs = computed(() =>
  configs.value.filter((row) => {
    const nameQ = filterName.value.trim().toLowerCase()
    if (nameQ && !(row.name || '').toLowerCase().includes(nameQ)) return false
    const descQ = filterDescription.value.trim().toLowerCase()
    if (descQ && !(row.description || '').toLowerCase().includes(descQ)) return false
    if (filterSide.value && row.side !== filterSide.value) return false
    if (filterCore.value && row.core !== filterCore.value) return false
    const verQ = filterVersion.value.trim().toLowerCase()
    if (verQ && !(row.version || '').toLowerCase().includes(verQ)) return false
    if (filterEnabled.value !== null && (row.enable !== false) !== filterEnabled.value) return false
    return true
  }),
)

async function load() {
  loading.value = true
  try {
    meta.value = await proxyBaseConfigsApi.meta()
    configs.value = await proxyBaseConfigsApi.list()
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  } finally {
    loading.value = false
  }
}

async function toggleEnable(row: ProxyBaseConfig, enable: boolean) {
  if (!row.id) return
  await proxyBaseConfigsApi.enable(row.id, enable)
  row.enable = enable
}

async function duplicate(id: number) {
  const dup = await proxyBaseConfigsApi.duplicate(id)
  toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
  router.push({ name: 'base-config-edit', params: { id: dup.id } })
}

function confirmDelete(row: ProxyBaseConfig) {
  confirm.require({
    message: t('common.confirmDelete'),
    header: t('common.delete'),
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      await proxyBaseConfigsApi.delete(row.id!)
      await load()
    },
  })
}

onMounted(load)
</script>
