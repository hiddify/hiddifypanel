<template>
  <MultiSelect
    v-model="selected"
    :options="categoryOptions"
    filter
    display="chip"
    class="w-full"
    :placeholder="t('proxy.categoriesPlaceholder')"
  >
    <template #dropdownicon>
      <i class="pi pi-list" />
    </template>
    <template #filtericon>
      <i class="pi pi-search" />
    </template>
    <template #header>
      <div class="font-medium px-3 py-2">{{ t('proxy.categoriesHeader') }}</div>
    </template>
    <template #footer>
      <div class="p-3 flex flex-col gap-2 border-t border-surface-200 dark:border-surface-700">
        <div class="flex flex-row gap-2 items-center">
          <InputText
            v-model="draftCategory"
            class="flex-1 min-w-0"
            :placeholder="t('proxy.categoriesAddPlaceholder')"
            @keyup.enter="addDraftCategory"
          />
          <Button
            type="button"
            :label="t('proxy.categoriesAddNew')"
            severity="secondary"
            variant="text"
            size="small"
            icon="pi pi-plus"
            :disabled="!draftCategory.trim()"
            class="shrink-0"
            @click="addDraftCategory"
          />
        </div>
        
      </div>
    </template>
  </MultiSelect>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiSelect from 'primevue/multiselect'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const props = defineProps<{
  modelValue: string[]
  suggestedCategories?: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const { t } = useI18n()
const draftCategory = ref('')

const selected = computed({
  get: () => normalizeCategories(props.modelValue),
  set: (value) => emit('update:modelValue', normalizeCategories(value)),
})

const categoryOptions = computed(() => {
  const set = new Set<string>()
  for (const raw of props.suggestedCategories ?? []) {
    const category = raw?.trim()
    if (category) set.add(category)
  }
  for (const category of selected.value) {
    set.add(category)
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

function normalizeCategories(categories: string[] | null | undefined): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  for (const raw of categories ?? []) {
    const category = String(raw ?? '').trim()
    if (!category || seen.has(category)) continue
    seen.add(category)
    out.push(category)
  }
  return out
}

function addDraftCategory() {
  const category = draftCategory.value.trim()
  if (!category) return
  if (!selected.value.includes(category)) {
    selected.value = [...selected.value, category]
  }
  draftCategory.value = ''
}

function clearAll() {
  selected.value = []
}
</script>
