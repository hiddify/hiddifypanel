<template>
  <div class="flex flex-col gap-3 mb-5">
    <div class="flex flex-wrap justify-between items-center gap-3">
      <div class="flex items-center gap-2 flex-wrap">
        <Button icon="pi pi-arrow-left" text :label="t('common.back')" @click="router.push({ name: 'template-list' })" />
        <h2 class="text-2xl font-semibold m-0">{{ isNew ? t('template.new') : (form.description || form.slug) }}</h2>
        <SysBadge v-if="isBuiltin" :customized="form.builtin_override" />
      </div>
      <div class="flex gap-2">
        <Button
          v-if="isBuiltin"
          icon="pi pi-copy"
          :label="t('common.duplicate')"
          severity="secondary"
          @click="duplicateBuiltin"
        />
        <Button icon="pi pi-save" :label="t('common.save')" :loading="saving" @click="save" />
      </div>
    </div>
  </div>

  <Message v-if="isBuiltin" severity="info" :closable="false" class="mb-3">
    {{ form.builtin_override ? t('template.builtinReadOnly') : t('template.builtinDefaultHint') }}
  </Message>

  <Panel :header="t('template.listTitle')">
    <HorizontalField :label="t('template.description')" input-id="tpl-desc">
      <InputText id="tpl-desc" v-model="form.description" class="w-full" @input="onDescriptionInput" />
    </HorizontalField>
    <div :class="{ 'builtin-locked': structureLocked }">
    <HorizontalField :label="t('template.core')" input-id="tpl-core">
      <Select id="tpl-core" v-model="form.core" :options="coreOptions" class="w-full" @change="onCoreCategoryChange" />
    </HorizontalField>
    <HorizontalField :label="t('template.category')" input-id="tpl-cat">
      <Select id="tpl-cat" v-model="form.category" :options="categoryOptions" class="w-full" @change="onCoreCategoryChange" />
    </HorizontalField>
    <HorizontalField :label="t('template.slug')" input-id="tpl-slug" :hint="t('template.slugHint')">
      <InputGroup>
        <InputGroupAddon class="font-mono text-sm whitespace-nowrap">{{ slugPrefix }}</InputGroupAddon>
        <InputText
          id="tpl-slug"
          v-model="slugSuffix"
          :disabled="form.is_builtin"
          class="w-full font-mono"
          @input="slugTouched = true"
        />
      </InputGroup>
    </HorizontalField>
    </div>
  </Panel>

  <Panel :header="t('template.content')" class="mt-4">
    <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_19rem] gap-4 items-start">
      <div>
        <TemplatedEditor
          v-model="editorContent"
          :variant="usesJsonTemplate(form.core) ? 'json' : 'plain'"
          :height="usesJsonTemplate(form.core) ? '480px' : undefined"
          :rows="20"
          :core="form.core"
          :category="form.category"
          :show-include="!contentLocked"
          :read-only="contentLocked"
          :show-override="isBuiltin"
          :overridden="Boolean(form.builtin_override)"
          override-field="template-content"
          list-scope="core"
          @insert-template="onInsertTemplate"
          @update:overridden="onOverrideToggle"
          @reset="onOverrideToggle(false)"
        />
      </div>
      <TemplateSidePanel
        v-if="form.core"
        :core="form.core"
        :category="form.category"
        list-scope="core"
        :template-text="effectiveTemplateText"
        :section-label="form.slug"
        :allow-create="!contentLocked"
        :read-only="contentLocked"
        @insert="onInsertTemplate"
        @cloned="onTemplateCloned"
      />
    </div>
  </Panel>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import InputGroup from 'primevue/inputgroup'
import InputGroupAddon from 'primevue/inputgroupaddon'
import Message from 'primevue/message'
import SysBadge from '@/shared/components/SysBadge.vue'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import TemplatedEditor from '@/shared/components/TemplatedEditor.vue'
import TemplateSidePanel from '@/shared/components/TemplateSidePanel.vue'
import {
  buildIncludeSnippet,
  buildTemplateSlug,
  buildTemplateSlugFromSuffix,
  buildBuiltinContentPatch,
  effectiveTemplateContent,
  slugSuffixFromFullSlug,
  templateSlugPrefix,
} from '@/shared/utils/template-slug'
import { usesJsonTemplate } from '@/shared/utils/core-template'
import { customProxiesApi, proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'

const props = defineProps<{ id?: string }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const isNew = computed(() => route.name === 'template-new' || !props.id)
const isBuiltin = computed(() => Boolean(form.is_builtin) && !isNew.value)
const structureLocked = computed(() => isBuiltin.value)
const contentLocked = computed(() => isBuiltin.value && !form.builtin_override)
const saving = ref(false)

const effectiveTemplateText = computed(() => effectiveTemplateContent(form, ''))

const editorContent = computed({
  get: () => effectiveTemplateText.value,
  set: (value: string) => {
    if (!contentLocked.value) form.content = value
  },
})
const slugTouched = ref(false)
const coreOptions = ref<string[]>([])
const categoryOptions = ref<string[]>([])

const form = reactive<ProxyTemplate>({
  name: '',
  slug: '',
  core: 'xray',
  category: 'server_inbound',
  description: '',
  content: '',
  builtin_override: false,
  builtin_content: '',
})

const slugPrefix = computed(() => templateSlugPrefix(form.core, form.category))

const slugSuffix = computed({
  get: () => slugSuffixFromFullSlug(form.slug, slugPrefix.value),
  set: (value: string) => {
    form.slug = buildTemplateSlugFromSuffix(form.core, form.category, value)
  },
})

function onInsertTemplate(tpl: ProxyTemplate) {
  const snippet = buildIncludeSnippet(tpl.slug)
  const content = form.content ?? ''
  if (!content.includes(snippet)) {
    form.content = (content.trim() ? `${content}\n` : '') + snippet
  }
}

function onTemplateCloned() {
  // side panel reloads internally
}

function onOverrideToggle(value: boolean) {
  if (value && !form.builtin_override) {
    form.content = form.builtin_content || form.content || ''
  } else if (!value) {
    form.content = form.builtin_content || form.content || ''
  }
  form.builtin_override = value
}

function syncSlugFromDescription() {
  if (!isNew.value || slugTouched.value || form.is_builtin) return
  if (!form.description?.trim()) return
  form.slug = buildTemplateSlug(form.core, form.category, form.description)
}

function onDescriptionInput() {
  syncSlugFromDescription()
}

function onCoreCategoryChange() {
  if (form.is_builtin) return
  const suffix = slugSuffix.value || form.description || 'template'
  form.slug = buildTemplateSlugFromSuffix(form.core, form.category, suffix)
  if (!slugTouched.value) syncSlugFromDescription()
}

function ensureSlugBeforeSave() {
  if (form.is_builtin) return
  const trimmed = (form.slug || '').trim()
  if (!trimmed || !trimmed.includes('/')) {
    form.slug = buildTemplateSlug(form.core, form.category, form.description || slugSuffix.value || 'template')
  }
}

function syncNameFromDescription() {
  form.name = (form.description || '').trim() || slugSuffix.value || 'template'
}

async function load() {
  try {
    const meta = await customProxiesApi.meta()
    coreOptions.value = [...meta.server_cores, ...meta.client_cores].filter((v, i, a) => a.indexOf(v) === i)
    categoryOptions.value = meta.template_categories
    if (!isNew.value && props.id) {
      slugTouched.value = true
      const data = await proxyTemplatesApi.get(Number(props.id))
      Object.assign(form, data)
      if (data.builtin_content) {
        form.builtin_content = data.builtin_content
      } else if (!form.builtin_override && data.content) {
        form.builtin_content = data.content
      }
    } else {
      syncSlugFromDescription()
    }
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
  }
}

async function duplicateBuiltin() {
  if (!props.id) return
  const copy = await proxyTemplatesApi.duplicate(Number(props.id))
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  await router.push({ name: 'template-edit', params: { id: String(copy.id) } })
}

function buildPatch(): Partial<ProxyTemplate> {
  syncNameFromDescription()
  if (isBuiltin.value) {
    return buildBuiltinContentPatch(form, editorContent.value)
  }
  ensureSlugBeforeSave()
  return {
    slug: form.slug,
    core: form.core,
    category: form.category,
    name: form.name,
    description: form.description,
    content: form.content,
  }
}

async function save() {
  saving.value = true
  try {
    const patch = buildPatch()
    if (isNew.value) {
      const created = await proxyTemplatesApi.create(patch as ProxyTemplate)
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
      router.replace({ name: 'template-edit', params: { id: created.id } })
    } else {
      const updated = await proxyTemplatesApi.update(Number(props.id), patch)
      Object.assign(form, updated)
      if (!form.builtin_content && updated.builtin_content) {
        form.builtin_content = updated.builtin_content
      }
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    }
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      toast.add({ severity: 'error', summary: t('template.slugDuplicate'), life: 5000 })
    } else {
      toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 5000 })
    }
  } finally {
    saving.value = false
  }
}

watch(() => form.description, () => syncSlugFromDescription())

watch(
  () => props.id,
  () => {
    void load()
  },
  { immediate: true },
)
</script>
