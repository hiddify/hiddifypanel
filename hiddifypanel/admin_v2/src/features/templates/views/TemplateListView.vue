<template>
  <PageHeader :title="t('template.listTitle')" />
  <Panel>
    <DataTable
      :value="filteredTemplates"
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
          <Button icon="pi pi-plus" :label="t('template.new')" @click="router.push({ name: 'template-new' })" />
        </div>
      </template>

      <Column field="description" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('template.description') }}</span>
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
      <Column field="slug" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('template.slug') }}</span>
            <Button
              icon="pi pi-search"
              text
              rounded
              size="small"
              :severity="filterSlug ? 'primary' : 'secondary'"
              :aria-label="t('common.search')"
              @click="(e: Event) => slugPopover.toggle(e)"
            />
          </div>
        </template>
        <template #body="{ data }">
          <span class="font-mono text-sm">{{ data.slug }}</span>
        </template>
      </Column>
      <Column field="core" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('template.core') }}</span>
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
      <Column field="category" sortable>
        <template #header>
          <div class="flex items-center gap-1">
            <span>{{ t('template.category') }}</span>
            <Button
              icon="pi pi-filter"
              text
              rounded
              size="small"
              :severity="filterCategory ? 'primary' : 'secondary'"
              :aria-label="t('common.filter')"
              @click="(e: Event) => categoryPopover.toggle(e)"
            />
          </div>
        </template>
      </Column>
      <Column header="" class="w-48 shrink-0">
        <template #body="{ data }">
          <SysBadge v-if="data.is_builtin" :customized="data.builtin_override" icon-only class="mr-1" />
          <Button icon="pi pi-pencil" text rounded @click="router.push({ name: 'template-edit', params: { id: data.id } })" />
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

  <Popover ref="descriptionPopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('template.description') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterDescription" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="slugPopover">
    <div class="flex flex-col gap-2 min-w-52">
      <label class="text-sm font-medium">{{ t('template.slug') }}</label>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filterSlug" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
  </Popover>
  <Popover ref="corePopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('template.core') }}</label>
      <Select v-model="filterCore" :options="coreOptions" show-clear class="w-full" />
    </div>
  </Popover>
  <Popover ref="categoryPopover">
    <div class="flex flex-col gap-2 min-w-44">
      <label class="text-sm font-medium">{{ t('template.category') }}</label>
      <Select v-model="filterCategory" :options="categoryOptions" show-clear class="w-full" />
    </div>
  </Popover>
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
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Popover from 'primevue/popover'
import PageHeader from '@/shared/components/PageHeader.vue'
import SysBadge from '@/shared/components/SysBadge.vue'
import { customProxiesApi, proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'

const { t } = useI18n()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const templates = ref<ProxyTemplate[]>([])
const loading = ref(false)
const coreOptions = ref<string[]>([])
const categoryOptions = ref<string[]>([])

const filterDescription = ref('')
const filterSlug = ref('')
const filterCore = ref<string | null>(null)
const filterCategory = ref<string | null>(null)

const descriptionPopover = ref()
const slugPopover = ref()
const corePopover = ref()
const categoryPopover = ref()

const filteredTemplates = computed(() =>
  templates.value.filter((tpl) => {
    const descQ = filterDescription.value.trim().toLowerCase()
    if (descQ && !(tpl.description || '').toLowerCase().includes(descQ)) return false
    const slugQ = filterSlug.value.trim().toLowerCase()
    if (slugQ && !(tpl.slug || '').toLowerCase().includes(slugQ)) return false
    if (filterCore.value && tpl.core !== filterCore.value) return false
    if (filterCategory.value && tpl.category !== filterCategory.value) return false
    return true
  }),
)

async function load() {
  loading.value = true
  try {
    const meta = await customProxiesApi.meta()
    coreOptions.value = [...new Set([...meta.server_cores, ...meta.client_cores])].sort()
    categoryOptions.value = meta.template_categories ?? []
    templates.value = await proxyTemplatesApi.list()
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  } finally {
    loading.value = false
  }
}

async function duplicate(id: number) {
  const copy = await proxyTemplatesApi.duplicate(id)
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  await router.push({ name: 'template-edit', params: { id: String(copy.id) } })
}

function confirmDelete(row: ProxyTemplate) {
  confirm.require({
    message: t('common.confirmDelete'),
    header: t('common.delete'),
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      if (!row.id) return
      await proxyTemplatesApi.delete(row.id)
      toast.add({ severity: 'success', summary: t('common.deleted'), life: 3000 })
      await load()
    },
  })
}

onMounted(load)
</script>
