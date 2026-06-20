<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import InputGroup from 'primevue/inputgroup'
import InputGroupAddon from 'primevue/inputgroupaddon'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import SysBadge from '@/shared/components/SysBadge.vue'
import { proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'
import {
  buildIncludeSnippet,
  effectiveTemplateContent,
  parseReferencedTemplateSlugs,
  templateDisplayName,
  buildTemplateSlug,
  templateSlugPrefix,
  slugSuffixFromFullSlug,
  buildTemplateSlugFromSuffix,
} from '@/shared/utils/template-slug'

const props = defineProps<{
  visible: boolean
  template: ProxyTemplate | null
  readOnly?: boolean
  core?: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  insert: [template: ProxyTemplate]
  cloned: [template: ProxyTemplate]
  saved: [template: ProxyTemplate]
}>()

const { t } = useI18n()
const toast = useToast()

const cloneDescription = ref('')
const cloning = ref(false)
const saving = ref(false)
const editMode = ref(false)
const editDraft = ref<ProxyTemplate | null>(null)
const viewStack = ref<ProxyTemplate[]>([])
const nestedVisible = ref(false)
const nestedTemplate = ref<ProxyTemplate | null>(null)
const nestedLoading = ref(false)

const stackTemplate = computed(() => viewStack.value[viewStack.value.length - 1] ?? props.template)
const activeTemplate = computed(() => editDraft.value ?? stackTemplate.value)
const displayName = computed(() => (activeTemplate.value ? templateDisplayName(activeTemplate.value) : ''))
const isBuiltin = computed(() => Boolean(activeTemplate.value?.is_builtin))
const contentReadOnly = computed(() => isBuiltin.value && !editDraft.value?.builtin_override)
const canGoBack = computed(() => viewStack.value.length > 1)

const slugPrefix = computed(() =>
  activeTemplate.value ? templateSlugPrefix(activeTemplate.value.core, activeTemplate.value.category) : '',
)

const slugSuffix = computed({
  get: () => (activeTemplate.value ? slugSuffixFromFullSlug(activeTemplate.value.slug, slugPrefix.value) : ''),
  set: (value: string) => {
    if (!editDraft.value) return
    editDraft.value.slug = buildTemplateSlugFromSuffix(editDraft.value.core, editDraft.value.category, value)
  },
})

const effectiveContent = computed(() => effectiveTemplateContent(editDraft.value, ''))

const referencedSlugs = computed(() => parseReferencedTemplateSlugs(effectiveContent.value, []))

const displayContent = computed({
  get: () => {
    if (!editDraft.value) return ''
    if (contentReadOnly.value) return effectiveContent.value
    return editDraft.value.content ?? ''
  },
  set: (value: string) => {
    if (editDraft.value && !contentReadOnly.value) {
      editDraft.value.content = value
    }
  },
})

watch(
  () => [props.visible, props.template] as const,
  ([open, tpl]) => {
    if (!open) {
      editMode.value = false
      editDraft.value = null
      viewStack.value = []
      nestedVisible.value = false
      nestedTemplate.value = null
      return
    }
    viewStack.value = tpl ? [tpl] : []
    editMode.value = Boolean(tpl && !tpl.is_builtin)
    editDraft.value = tpl ? { ...tpl } : null
    cloneDescription.value = tpl?.description?.trim() || ''
  },
  { immediate: true },
)

watch(stackTemplate, (tpl) => {
  if (!props.visible || !tpl) return
  editMode.value = Boolean(tpl && !tpl.is_builtin)
  editDraft.value = { ...tpl }
})

function close() {
  emit('update:visible', false)
}

function goBack() {
  if (viewStack.value.length > 1) {
    viewStack.value = viewStack.value.slice(0, -1)
  }
}

function onInsert() {
  if (activeTemplate.value) emit('insert', activeTemplate.value)
}

function insertIncludeSnippet(slug: string) {
  if (!editDraft.value || contentReadOnly.value) return
  const snippet = buildIncludeSnippet(slug)
  const content = editDraft.value.content ?? ''
  if (!content.includes(snippet)) {
    editDraft.value.content = (content.trim() ? `${content}\n` : '') + snippet
  }
}

async function openReferencedTemplate(slug: string) {
  nestedLoading.value = true
  try {
    const core = props.core || activeTemplate.value?.core
    let tpl: ProxyTemplate | undefined
    if (core) {
      const all = await proxyTemplatesApi.list({ core })
      tpl = all.find((item) => item.slug === slug)
    }
    if (!tpl) {
      toast.add({ severity: 'warn', summary: t('template.notFound'), detail: slug, life: 4000 })
      return
    }
    nestedTemplate.value = tpl
    nestedVisible.value = true
  } finally {
    nestedLoading.value = false
  }
}

function onOverrideToggle(value: boolean) {
  if (!editDraft.value) return
  if (value && !editDraft.value.builtin_override) {
    editDraft.value.content = editDraft.value.builtin_content || editDraft.value.content || ''
  } else if (!value) {
    editDraft.value.content = editDraft.value.builtin_content || editDraft.value.content || ''
  }
  editDraft.value.builtin_override = value
}

async function cloneTemplate() {
  if (!stackTemplate.value?.id) return
  cloning.value = true
  try {
    const cloned = await proxyTemplatesApi.duplicate(stackTemplate.value.id)
    const baseLabel = stackTemplate.value.description?.trim() || stackTemplate.value.slug
    const customDescription = cloneDescription.value.trim() || `${baseLabel} copy`
    const slug = buildTemplateSlug(
      cloned.core ?? stackTemplate.value.core,
      cloned.category ?? stackTemplate.value.category ?? '',
      customDescription,
    )
    const updated = await proxyTemplatesApi.update(cloned.id!, {
      name: customDescription,
      description: customDescription,
      slug,
      content: cloned.content,
    })
    editDraft.value = { ...updated, is_builtin: false }
    editMode.value = true
    toast.add({ severity: 'success', summary: t('template.cloned'), life: 3000 })
    emit('cloned', editDraft.value)
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 4000 })
  } finally {
    cloning.value = false
  }
}

async function saveEdits() {
  if (!editDraft.value?.id) return
  saving.value = true
  try {
    const desc = (editDraft.value.description || '').trim()
    editDraft.value.name = desc || slugSuffix.value || 'template'
    const patch: Partial<ProxyTemplate> = editDraft.value.is_builtin
      ? {
          name: editDraft.value.name,
          description: editDraft.value.description,
          builtin_override: editDraft.value.builtin_override,
          ...(editDraft.value.builtin_override ? { content: editDraft.value.content } : {}),
        }
      : {
          name: editDraft.value.name,
          slug: editDraft.value.slug,
          description: editDraft.value.description,
          content: editDraft.value.content,
        }
    const saved = await proxyTemplatesApi.update(editDraft.value.id, patch)
    editDraft.value = { ...saved, is_builtin: saved.is_builtin }
    editMode.value = !saved.is_builtin
    const top = viewStack.value[viewStack.value.length - 1]
    if (top?.id === saved.id) {
      viewStack.value = [...viewStack.value.slice(0, -1), { ...saved, is_builtin: saved.is_builtin }]
    }
    toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    emit('saved', editDraft.value)
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="displayName"
    class="w-full max-w-3xl"
    @update:visible="emit('update:visible', $event)"
  >
    <div v-if="activeTemplate" class="flex flex-col gap-3">
      <div class="flex flex-wrap gap-2 items-center">
        <Button
          v-if="canGoBack"
          icon="pi pi-arrow-left"
          :label="t('common.back')"
          text
          size="small"
          @click="goBack"
        />
        <SysBadge v-if="isBuiltin && !editMode" :customized="editDraft?.builtin_override" icon-only />
        <Tag v-if="editMode" severity="success" :value="t('template.editable')" />
        <span class="text-muted-color text-sm font-mono break-all">{{ activeTemplate.slug }}</span>
      </div>

      <HorizontalField v-if="editMode" :label="t('template.description')" input-id="edit-tpl-desc">
        <InputText id="edit-tpl-desc" v-model="editDraft!.description" class="w-full" />
      </HorizontalField>

      <HorizontalField v-if="editMode" :label="t('template.slug')" input-id="edit-tpl-slug">
        <InputGroup>
          <InputGroupAddon class="font-mono text-sm whitespace-nowrap">{{ slugPrefix }}</InputGroupAddon>
          <InputText id="edit-tpl-slug" v-model="slugSuffix" class="w-full font-mono" />
        </InputGroup>
      </HorizontalField>

      <HorizontalField v-if="isBuiltin && !editMode" :label="t('template.customContent')" input-id="view-tpl-override">
        <ToggleSwitch
          id="view-tpl-override"
          :model-value="Boolean(editDraft?.builtin_override)"
          @update:model-value="onOverrideToggle"
        />
      </HorizontalField>

      <HorizontalField v-if="isBuiltin && !editMode" :label="t('template.cloneDescription')" input-id="clone-desc">
        <InputText id="clone-desc" v-model="cloneDescription" class="w-full" />
      </HorizontalField>

      <div v-if="referencedSlugs.length" class="flex flex-col gap-2">
        <span class="text-sm font-medium">{{ t('template.referencedTemplates') }}</span>
        <div class="flex flex-wrap gap-2 template-referenced-list">
          <div v-for="slug in referencedSlugs" :key="slug" class="flex items-center gap-1">
            <Button
              :label="slug"
              size="small"
              severity="secondary"
              outlined
              class="font-mono text-xs"
              :loading="nestedLoading"
              @click="openReferencedTemplate(slug)"
            />
            <Button
              v-if="editMode && !contentReadOnly"
              icon="pi pi-plus"
              size="small"
              text
              :aria-label="t('template.insert')"
              @click="insertIncludeSnippet(slug)"
            />
          </div>
        </div>
      </div>

      <HorizontalField :label="t('template.content')">
        <Textarea
          v-model="displayContent"
          :readonly="contentReadOnly"
          rows="14"
          class="w-full font-mono text-sm template-content-textarea"
        />
      </HorizontalField>
    </div>

    <template #footer>
      <Button :label="t('common.cancel')" text @click="close" />
      <Button v-if="!readOnly" icon="pi pi-plus" :label="t('template.insert')" @click="onInsert" />
      <Button
        icon="pi pi-copy"
        :label="t('template.clone')"
        :loading="cloning"
        severity="secondary"
        @click="cloneTemplate"
      />
      <Button
        v-if="editMode || isBuiltin"
        icon="pi pi-save"
        :label="t('common.save')"
        :loading="saving"
        @click="saveEdits"
      />
    </template>
  </Dialog>

  <TemplateViewDialog
    v-model:visible="nestedVisible"
    :template="nestedTemplate"
    :read-only="readOnly"
    :core="core || activeTemplate?.core"
    @insert="onInsert"
    @cloned="emit('cloned', $event)"
    @saved="emit('saved', $event)"
  />
</template>

<style scoped>
.template-content-textarea {
  max-height: 24rem;
  overflow-y: auto;
  user-select: text;
}

.template-referenced-list {
  max-height: 8rem;
  overflow-y: auto;
}
</style>
