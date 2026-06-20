<template>
  <MultiSelect
    v-model="selected"
    :options="tagOptions"
    filter
    display="chip"
    class="w-full"
    :placeholder="t('proxy.tagsPlaceholder')"
  >
    <template #dropdownicon>
      <i class="pi pi-tags" />
    </template>
    <template #filtericon>
      <i class="pi pi-search" />
    </template>
    <template #header>
      <div class="font-medium px-3 py-2">{{ t('proxy.tagsHeader') }}</div>
    </template>
    <template #footer>
      <div class="p-3 flex flex-col gap-2 border-t border-surface-200 dark:border-surface-700">
        <div class="flex flex-row gap-2 items-center">
          <InputText
            v-model="draftTag"
            class="flex-1 min-w-0"
            :placeholder="t('proxy.tagsAddPlaceholder')"
            @keyup.enter="addDraftTag"
          />
          <Button
            type="button"
            :label="t('proxy.tagsAddNew')"
            severity="secondary"
            variant="text"
            size="small"
            icon="pi pi-plus"
            :disabled="!draftTag.trim()"
            class="shrink-0"
            @click="addDraftTag"
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
  suggestedTags?: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const { t } = useI18n()
const draftTag = ref('')

const selected = computed({
  get: () => normalizeTags(props.modelValue),
  set: (value) => emit('update:modelValue', normalizeTags(value)),
})

const tagOptions = computed(() => {
  const set = new Set<string>()
  for (const raw of props.suggestedTags ?? []) {
    const tag = raw?.trim()
    if (tag) set.add(tag)
  }
  for (const tag of selected.value) {
    set.add(tag)
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

function normalizeTags(tags: string[] | null | undefined): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  for (const raw of tags ?? []) {
    const tag = String(raw ?? '').trim()
    if (!tag || seen.has(tag)) continue
    seen.add(tag)
    out.push(tag)
  }
  return out
}

function addDraftTag() {
  const tag = draftTag.value.trim()
  if (!tag) return
  if (!selected.value.includes(tag)) {
    selected.value = [...selected.value, tag]
  }
  draftTag.value = ''
}

function clearAll() {
  selected.value = []
}
</script>
