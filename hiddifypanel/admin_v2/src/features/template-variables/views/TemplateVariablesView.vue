<template>
  <PageHeader :title="t('templateVariables.listTitle')" />
  <Panel>
    <DataTable
      v-model:filters="filters"
      :value="variables"
      :loading="loading"
      striped-rows
      paginator
      :rows="25"
      :rows-per-page-options="[25, 50, 100]"
      :global-filter-fields="['access', 'value', 'label', 'description', 'category_label']"
      filter-display="row"
      data-key="access"
    >
      <template #header>
        <div class="flex flex-wrap justify-between items-center gap-3">
          <div class="flex flex-wrap gap-2 items-center">
            <IconField>
              <InputIcon class="pi pi-search" />
              <InputText v-model="filters.global.value" :placeholder="t('common.search')" />
            </IconField>
            <Select
              v-model="filterCategory"
              :options="categoryOptions"
              option-label="label"
              option-value="id"
              show-clear
              :placeholder="t('templateVariables.group')"
              class="min-w-48"
            />
          </div>
          <Button icon="pi pi-refresh" severity="secondary" :aria-label="t('common.search')" @click="load" />
        </div>
      </template>

      <Column :header="t('templateVariables.access')" sortable field="access" :show-filter-menu="false">
        <template #body="{ data }">
          <code class="font-mono text-sm break-all">{{ data.access }}</code>
        </template>
      </Column>
      <Column :header="t('templateVariables.currentValue')" sortable field="value" :show-filter-menu="false">
        <template #body="{ data }">
          <span class="text-sm break-all">{{ formatValue(data.value) }}</span>
        </template>
      </Column>
      <Column field="label" :header="t('templateVariables.label')" sortable :show-filter-menu="false" />
      <Column field="description" :header="t('templateVariables.description')" :show-filter-menu="false">
        <template #body="{ data }">
          <div class="text-sm text-muted-color variable-desc-html" v-html="data.description" />
        </template>
      </Column>
    </DataTable>
  </Panel>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { FilterMatchMode } from '@primevue/core/api'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import PageHeader from '@/shared/components/PageHeader.vue'
import { templateVariablesApi, type TemplateVariable, type TemplateVariableGroup } from '@/core/api/generated'
import { flattenTemplateVariableGroups } from '@/shared/utils/template-variables'

const { t } = useI18n()

const loading = ref(false)
const groups = ref<TemplateVariableGroup[]>([])
const variables = ref<TemplateVariable[]>([])
const filterCategory = ref<string | null>(null)

const filters = ref({
  global: { value: null as string | null, matchMode: FilterMatchMode.CONTAINS },
})

const categoryOptions = computed(() => groups.value)

function applyFlatFromGroups() {
  variables.value = flattenTemplateVariableGroups(groups.value)
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  try {
    const text = JSON.stringify(value)
    return text.length > 120 ? `${text.slice(0, 120)}…` : text
  } catch {
    return String(value)
  }
}

function mergeValuesFromGroups(valueGroups: TemplateVariableGroup[]) {
  const byAccess = new Map<string, unknown>()
  for (const g of valueGroups) {
    const existing = groups.value.find((x) => x.id === g.id)
    if (existing && g.label) existing.label = g.label
    for (const v of g.variables ?? []) {
      if (v.value !== undefined) byAccess.set(v.access, v.value)
    }
  }
  for (const g of groups.value) {
    for (const v of g.variables ?? []) {
      if (byAccess.has(v.access)) v.value = byAccess.get(v.access)
    }
  }
  applyFlatFromGroups()
}

async function load() {
  loading.value = true
  try {
    const data = await templateVariablesApi.list()
    groups.value = data.groups
    applyFlatFromGroups()
    void templateVariablesApi.list({ values: true }).then((withValues) => {
      mergeValuesFromGroups(withValues.groups)
    })
  } finally {
    loading.value = false
  }
}

watch(filterCategory, (categoryId) => {
  if (!categoryId) {
    applyFlatFromGroups()
    return
  }
  const group = groups.value.find((g) => g.id === categoryId)
  variables.value = (group?.variables ?? []).map((v) => ({ ...v, category_label: group?.label }))
})

onMounted(load)
</script>

<style scoped>
.variable-desc-html :deep(a) {
  color: var(--p-primary-color);
}
.variable-desc-html :deep(p) {
  margin: 0.15rem 0;
}
</style>
