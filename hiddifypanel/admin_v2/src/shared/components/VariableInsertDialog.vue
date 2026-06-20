<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tag from 'primevue/tag'
import { useTemplateVariableCatalog } from '@/shared/composables/useTemplateVariableCatalog'
import { variableInsertSnippet } from '@/shared/utils/variable-insert-snippet'
import type { TemplateVariable } from '@/core/api/generated'

const visible = defineModel<boolean>('visible', { default: false })

const emit = defineEmits<{
  select: [snippet: string]
}>()

const { t } = useI18n()
const { variables, loading, load } = useTemplateVariableCatalog()
const query = ref('')

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return variables.value
  return variables.value.filter(
    (v) =>
      v.name.toLowerCase().includes(q) ||
      v.access.toLowerCase().includes(q) ||
      (v.access_bracket || '').toLowerCase().includes(q) ||
      v.label.toLowerCase().includes(q) ||
      (v.description || '').toLowerCase().includes(q) ||
      (v.category_label || v.category || '').toLowerCase().includes(q),
  )
})

function pick(v: TemplateVariable) {
  emit('select', variableInsertSnippet(v))
  visible.value = false
}

watch(visible, (open) => {
  if (open) {
    query.value = ''
    void load()
  }
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('editor.insertVariable')"
    class="variable-insert-dialog"
    :style="{ width: 'min(42rem, 96vw)' }"
  >
    <IconField class="mb-3 w-full">
      <InputIcon class="pi pi-search" />
      <InputText v-model="query" :placeholder="t('common.search')" class="w-full" autofocus />
    </IconField>

    <div v-if="loading" class="text-muted-color text-sm py-4 text-center">{{ t('common.search') }}…</div>
    <ul v-else class="list-none m-0 p-0 max-h-[24rem] overflow-y-auto flex flex-col gap-1">
      <li
        v-for="v in filtered"
        :key="v.access"
        class="rounded-border p-2 cursor-pointer transition-colors hover:bg-[var(--surface-hover)]"
        @click="pick(v)"
      >
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-medium">{{ v.label }}</span>
          <code class="text-xs text-muted-color">{{ v.name }}</code>
          <Tag :value="v.category_label || v.category" severity="secondary" class="text-xs" />
        </div>
        <div class="text-sm font-mono break-all mt-1">{{ v.access }}</div>
        <div
          v-if="v.value !== undefined && v.value !== null && v.value !== ''"
          class="text-xs text-muted-color mt-1 font-mono break-all"
        >
          = {{ typeof v.value === 'object' ? JSON.stringify(v.value) : String(v.value) }}
        </div>
        <div v-if="v.description" class="text-xs text-muted-color mt-1 variable-desc-html" v-html="v.description" />
      </li>
      <li v-if="!filtered.length" class="text-muted-color text-sm py-4 text-center">{{ t('editor.noVariables') }}</li>
    </ul>
  </Dialog>
</template>

<style scoped>
.variable-desc-html :deep(a) {
  color: var(--p-primary-color);
}
.variable-desc-html :deep(p) {
  margin: 0.25rem 0;
}
</style>
