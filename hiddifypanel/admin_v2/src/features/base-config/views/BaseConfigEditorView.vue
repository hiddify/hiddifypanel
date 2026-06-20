<template>
  <div class="flex flex-col gap-3 mb-5">
    <div class="flex flex-wrap justify-between items-center gap-3">
      <div class="flex items-center gap-2 flex-wrap">
        <Button icon="pi pi-arrow-left" text :label="t('common.back')" @click="router.push({ name: 'base-config-list' })" />
        <h2 class="text-2xl font-semibold m-0">{{ isNew ? t('baseConfig.new') : form.name }}</h2>
        <SysBadge v-if="isBuiltin" :customized="form.builtin_override" />
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          v-if="isBuiltin"
          icon="pi pi-copy"
          :label="t('common.duplicate')"
          severity="secondary"
          @click="duplicateBuiltin"
        />
        <Button v-if="!isBuiltin || form.builtin_override" icon="pi pi-upload" :label="t('proxy.import')" severity="secondary" @click="runImport" />
        <Button icon="pi pi-download" :label="t('proxy.export')" severity="secondary" @click="exportDialogVisible = true" />
        <Button icon="pi pi-check-circle" :label="t('common.validate')" severity="secondary" @click="runValidate" />
        <Button icon="pi pi-save" :label="t('common.save')" :loading="saving" @click="save" />
      </div>
    </div>
  </div>

  <Message v-if="isBuiltin" severity="info" :closable="false" class="mb-3">
    {{ form.builtin_override ? t('baseConfig.builtinReadOnly') : t('baseConfig.builtinDefaultHint') }}
  </Message>

  <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_19rem] gap-4 items-start">
    <div class="min-w-0 flex flex-col gap-4">
      <Panel :header="t('baseConfig.listTitle')">
        <HorizontalField :label="t('common.enabled')" input-id="bc-enable">
          <ToggleSwitch id="bc-enable" v-model="form.enable!" />
        </HorizontalField>
        <HorizontalField :label="t('baseConfig.name')" input-id="bc-name">
          <InputText id="bc-name" v-model="form.name" class="w-full" />
        </HorizontalField>
        <div :class="{ 'builtin-locked': structureLocked }">
        <HorizontalField :label="t('baseConfig.side')" input-id="bc-side">
          <Select id="bc-side" v-model="form.side" :options="meta?.sides ?? []" class="w-full" :disabled="!isNew" @change="onSideChange" />
        </HorizontalField>
        <HorizontalField :label="t('baseConfig.core')" input-id="bc-core">
          <Select id="bc-core" v-model="form.core" :options="coreOptions" class="w-full" :disabled="!isNew" />
        </HorizontalField>
        <HorizontalField :label="t('baseConfig.version')" input-id="bc-version">
          <InputGroup>
            <InputGroupAddon>≥</InputGroupAddon>
            <InputText id="bc-version" v-model="form.version" placeholder="1.0.0" class="w-full" />
          </InputGroup>
        </HorizontalField>
        <HorizontalField :label="t('baseConfig.description')" input-id="bc-desc">
          <InputText id="bc-desc" v-model="form.description" class="w-full" />
        </HorizontalField>
        </div>
      </Panel>

      <Panel :header="t('baseConfig.content')">
        <BuiltinStateBar
          v-if="isBuiltin"
          :override="Boolean(form.builtin_override)"
          show-toggle
          @update:override="onOverrideToggle"
        />
        <div :class="{ 'builtin-locked': contentLocked }">
        <TemplatedEditor
          v-model="editorContent"
          :variant="usesJsonTemplate(form.core) ? 'json' : 'plain'"
          :height="usesJsonTemplate(form.core) ? '520px' : undefined"
          :rows="24"
          :core="form.core"
          :category="templateCategory"
          :explicit-slugs="form.template_slugs ?? []"
          :read-only="contentLocked"
          @insert-template="onInsertTemplate"
        />
        </div>
      </Panel>

      <ValidationPanel v-if="validation" :result="validation" />
    </div>

    <TemplateSidePanel
      v-if="form.core"
      :core="form.core"
      :category="templateCategory"
      list-scope="core"
      :template-text="effectiveTemplateText"
      :explicit-slugs="form.template_slugs ?? []"
      :section-label="`${form.side}/${form.core}`"
      :allow-create="!structureLocked || form.builtin_override"
      :read-only="contentLocked"
      @insert="onInsertTemplate"
      @cloned="() => {}"
    />
  </div>

  <BundleExportDialog v-model:visible="exportDialogVisible" @confirm="runExport" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
import BuiltinStateBar from '@/shared/components/BuiltinStateBar.vue'
import ToggleSwitch from 'primevue/toggleswitch'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import TemplatedEditor from '@/shared/components/TemplatedEditor.vue'
import ValidationPanel from '@/shared/components/ValidationPanel.vue'
import TemplateSidePanel from '@/shared/components/TemplateSidePanel.vue'
import BundleExportDialog from '@/shared/components/BundleExportDialog.vue'
import {
  buildIncludeSnippet,
  effectiveTemplateContent,
  parseReferencedTemplateSlugs,
} from '@/shared/utils/template-slug'
import { usesJsonTemplate } from '@/shared/utils/core-template'
import { downloadJson, pickFile } from '@/shared/utils/custom-proxy-bundle'
import {
  proxyBaseConfigsApi,
  type ProxyBaseConfig,
  type ProxyBaseConfigMeta,
  type ProxyTemplate,
  type ValidationResult,
} from '@/core/api/generated'

const props = defineProps<{ id?: string }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const isNew = computed(() => route.name === 'base-config-new' || !props.id)
const saving = ref(false)
const validation = ref<ValidationResult | null>(null)
const exportDialogVisible = ref(false)

const form = reactive<ProxyBaseConfig>({
  side: 'client',
  core: 'xray',
  version: '',
  name: '',
  description: '',
  content: '{}',
  template_slugs: [],
  enable: true,
  builtin_override: false,
  builtin_content: '',
})

const isBuiltin = computed(() => Boolean(form.is_builtin) && !isNew.value)
const structureLocked = computed(() => isBuiltin.value)
const contentLocked = computed(() => isBuiltin.value && !form.builtin_override)
const meta = ref<ProxyBaseConfigMeta | null>(null)

const coreOptions = computed(() => meta.value?.cores_by_side[form.side] ?? [])
const templateCategory = computed(() =>
  form.side === 'server' ? 'server_inbound' : 'client_outbound',
)

const contentFallback = computed(() => (usesJsonTemplate(form.core) ? '{}' : ''))

const effectiveTemplateText = computed(() =>
  effectiveTemplateContent(form, contentFallback.value),
)

const editorContent = computed({
  get: () => effectiveTemplateText.value,
  set: (value: string) => {
    if (!contentLocked.value) form.content = value
  },
})

function onOverrideToggle(value: boolean) {
  if (value && !form.builtin_override) {
    form.content = form.builtin_content || form.content || '{}'
  } else if (!value) {
    form.content = form.builtin_content || form.content || '{}'
  }
  form.builtin_override = value
}

function onSideChange() {
  const cores = coreOptions.value
  if (cores.length && !cores.includes(form.core)) {
    form.core = cores[0]
  }
}

function ensureTemplateSlug(slug: string) {
  const slugs = form.template_slugs ?? []
  if (!slugs.includes(slug)) {
    form.template_slugs = [...slugs, slug]
  }
}

function onInsertTemplate(tpl: ProxyTemplate) {
  ensureTemplateSlug(tpl.slug)
  const snippet = buildIncludeSnippet(tpl.slug)
  const tplText = form.content ?? ''
  if (!tplText.includes(snippet)) {
    form.content = (tplText.trim() ? `${tplText}\n` : '') + snippet
  }
}

function syncTemplateSlugsFromContent() {
  form.template_slugs = parseReferencedTemplateSlugs(
    effectiveTemplateText.value,
    form.template_slugs ?? [],
  )
}

async function load() {
  meta.value = await proxyBaseConfigsApi.meta()
  if (!isNew.value && props.id) {
    const data = await proxyBaseConfigsApi.get(Number(props.id))
    Object.assign(form, data)
    if (form.enable === undefined) form.enable = true
    if (!form.template_slugs) form.template_slugs = []
    if (!form.content) form.content = '{}'
    if (!form.builtin_content && data.content) {
      form.builtin_content = data.builtin_content ?? data.content
    }
    syncTemplateSlugsFromContent()
  }
}

async function duplicateBuiltin() {
  if (!props.id) return
  const dup = await proxyBaseConfigsApi.duplicate(Number(props.id))
  toast.add({ severity: 'success', summary: t('common.duplicate'), life: 3000 })
  router.push({ name: 'base-config-edit', params: { id: dup.id } })
}

async function runValidate() {
  const result = await proxyBaseConfigsApi.validate(form)
  validation.value = {
    ok: result.ok,
    errors: result.errors,
    warnings: result.warnings,
  }
  if (!result.ok) {
    toast.add({ severity: 'error', summary: t('common.validationFailed'), life: 4000 })
  }
}

async function save() {
  if (!isBuiltin.value) {
    await runValidate()
    if (validation.value && !validation.value.ok) return
  } else if (form.builtin_override) {
    await runValidate()
    if (validation.value && !validation.value.ok) return
  }
  saving.value = true
  try {
    const patch: Partial<ProxyBaseConfig> = isBuiltin.value
      ? {
          name: form.name,
          enable: form.enable,
          description: form.description,
          builtin_override: form.builtin_override,
          ...(form.builtin_override
            ? { content: form.content, template_slugs: form.template_slugs }
            : {}),
        }
      : form
    if (isNew.value) {
      const created = await proxyBaseConfigsApi.create(patch as ProxyBaseConfig)
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
      router.replace({ name: 'base-config-edit', params: { id: created.id } })
    } else {
      const updated = await proxyBaseConfigsApi.update(Number(props.id), patch)
      Object.assign(form, updated)
      toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    }
  } finally {
    saving.value = false
  }
}

async function runExport(excludeBuiltin: boolean) {
  try {
    const bundle = await proxyBaseConfigsApi.exportBundle({
      ...form,
      exclude_builtin_templates: excludeBuiltin,
    })
    const name = `${form.side}-${form.core}-${form.version || 'config'}`.replace(/[^a-z0-9_-]+/gi, '-')
    downloadJson(bundle, `${name}.json`)
  } catch {
    toast.add({ severity: 'error', summary: t('proxy.exportFailed'), life: 4000 })
  }
}

async function runImport() {
  const file = await pickFile()
  if (!file) return
  try {
    const bundle = JSON.parse(await file.text())
    const result = await proxyBaseConfigsApi.importBundle(bundle)
    const config = result.base_config
    Object.assign(form, config)
    if (!form.template_slugs) form.template_slugs = []
    if (!form.content) form.content = '{}'
    toast.add({
      severity: 'success',
      summary: t('proxy.importSuccess', { count: result.templates_imported }),
      life: 4000,
    })
  } catch {
    toast.add({ severity: 'error', summary: t('proxy.importFailed'), life: 4000 })
  }
}

onMounted(load)

watch(
  () => [form.content, form.builtin_content, form.builtin_override] as const,
  () => {
    syncTemplateSlugsFromContent()
  },
)
</script>

<style scoped>
.builtin-locked {
  opacity: 0.72;
  pointer-events: none;
}
</style>
