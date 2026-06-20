<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import VariableInsertDialog from '@/shared/components/VariableInsertDialog.vue'
import TemplateIncludeMenu from '@/shared/components/TemplateIncludeMenu.vue'
import type { ProxyTemplate } from '@/core/api/generated'

defineProps<{
  core?: string
  category?: string
  templateText?: string
  explicitSlugs?: string[]
  showInclude?: boolean
  readOnly?: boolean
  listScope?: 'category' | 'core'
}>()

const emit = defineEmits<{
  'insert-variable': [snippet: string]
  'insert-template': [template: ProxyTemplate]
}>()

const { t } = useI18n()
const varDialogVisible = ref(false)

function onVariable(snippet: string) {
  emit('insert-variable', snippet)
}
</script>

<template>
  <div class="editor-toolbar flex flex-wrap items-center gap-2 py-1">
    <Button
      icon="pi pi-code"
      :label="t('editor.insertVariable')"
      severity="secondary"
      size="small"
      @click="varDialogVisible = true"
    />
    <TemplateIncludeMenu
      v-if="showInclude !== false"
      :core="core"
      :category="category"
      :template-text="templateText"
      :explicit-slugs="explicitSlugs"
      :read-only="readOnly"
      :list-scope="listScope"
      @select="emit('insert-template', $event)"
    />
    <VariableInsertDialog v-model:visible="varDialogVisible" @select="onVariable" />
  </div>
</template>
