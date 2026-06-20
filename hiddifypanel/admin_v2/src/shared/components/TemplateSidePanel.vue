<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import { proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'
import {
  expandReferencedTemplateSlugs,
  parseReferencedTemplateSlugs,
  sortTemplatesByIncluded,
  templateDisplayName,
} from '@/shared/utils/template-slug'
import SysBadge from '@/shared/components/SysBadge.vue'
import TemplateViewDialog from '@/shared/components/TemplateViewDialog.vue'
import TemplateCreateDialog from '@/shared/components/TemplateCreateDialog.vue'

const props = withDefaults(
  defineProps<{
    core?: string
    category?: string
    templateText?: string
    explicitSlugs?: string[]
    sectionLabel?: string
    allowCreate?: boolean
    readOnly?: boolean
    /** category: filter by category; core: list all templates for core */
    listScope?: 'category' | 'core'
  }>(),
  {
    listScope: 'category',
  },
)

const emit = defineEmits<{
  insert: [template: ProxyTemplate]
  cloned: [template: ProxyTemplate]
  saved: [template: ProxyTemplate]
}>()

const { t } = useI18n()
const raw = ref<ProxyTemplate[]>([])
const templateSearch = ref('')
const dialogVisible = ref(false)
const createVisible = ref(false)
const selected = ref<ProxyTemplate | null>(null)
const expandedSlugs = ref<string[]>([])

const directReferencedSlugs = computed(() =>
  parseReferencedTemplateSlugs(props.templateText ?? '', props.explicitSlugs ?? []),
)

const referencedSlugs = computed(() =>
  expandedSlugs.value.length ? expandedSlugs.value : directReferencedSlugs.value,
)

const templates = computed(() => {
  const sorted = sortTemplatesByIncluded(raw.value, referencedSlugs.value)
  for (const slug of referencedSlugs.value) {
    if (slug && !sorted.some((tpl) => tpl.slug === slug)) {
      sorted.push({
        slug,
        name: slug,
        description: '',
        core: props.core ?? '',
        category: props.category ?? '',
        is_builtin: false,
      } as ProxyTemplate)
    }
  }
  const q = templateSearch.value.trim().toLowerCase()
  if (!q) return sortTemplatesByIncluded(sorted, referencedSlugs.value)
  return sortTemplatesByIncluded(
    sorted.filter((tpl) => {
      const label = templateDisplayName(tpl).toLowerCase()
      const slug = (tpl.slug || '').toLowerCase()
      const desc = (tpl.description || '').toLowerCase()
      return label.includes(q) || slug.includes(q) || desc.includes(q)
    }),
    referencedSlugs.value,
  )
})

const panelHeader = computed(() =>
  props.sectionLabel ? `${t('template.sidePanel')}: ${props.sectionLabel}` : t('template.sidePanel'),
)

const canCreate = computed(() => Boolean(props.allowCreate && props.core && props.category))

function isIncluded(slug: string) {
  return referencedSlugs.value.includes(slug)
}

function isDirectlyIncluded(slug: string) {
  return directReferencedSlugs.value.includes(slug)
}

async function findTemplateBySlug(slug: string): Promise<ProxyTemplate | undefined> {
  const cached = raw.value.find((tpl) => tpl.slug === slug)
  if (cached) return cached
  if (!props.core) return undefined
  const all = await proxyTemplatesApi.list({ core: props.core })
  return all.find((tpl) => tpl.slug === slug)
}

async function refreshExpandedSlugs() {
  const seeds = directReferencedSlugs.value
  if (!seeds.length) {
    expandedSlugs.value = []
    return
  }
  const contentBySlug = new Map<string, string | null | undefined>(
    raw.value.map((tpl) => [tpl.slug, tpl.content]),
  )
  for (const slug of seeds) {
    if (!contentBySlug.has(slug)) {
      const tpl = await findTemplateBySlug(slug)
      if (tpl) contentBySlug.set(slug, tpl.content)
    }
  }
  expandedSlugs.value = expandReferencedTemplateSlugs(seeds, contentBySlug)
}

async function load() {
  if (!props.core) {
    raw.value = []
    expandedSlugs.value = []
    return
  }
  const list =
    props.listScope === 'core' || !props.category
      ? await proxyTemplatesApi.list({ core: props.core })
      : await proxyTemplatesApi.list({
          core: props.core,
          category: props.category,
        })
  const bySlug = new Map(list.map((tpl) => [tpl.slug, tpl]))
  const missing = directReferencedSlugs.value.filter((slug) => slug && !bySlug.has(slug))
  if (missing.length) {
    const all = await proxyTemplatesApi.list({ core: props.core })
    for (const tpl of all) {
      if (tpl.slug && missing.includes(tpl.slug)) {
        bySlug.set(tpl.slug, tpl)
      }
    }
  }
  raw.value = [...bySlug.values()]
  await refreshExpandedSlugs()
}

async function openTemplate(tpl: ProxyTemplate) {
  if (!tpl.id && tpl.slug && props.core) {
    const found = await findTemplateBySlug(tpl.slug)
    selected.value = found ?? tpl
  } else {
    selected.value = tpl
  }
  dialogVisible.value = true
}

function onInsert(tpl: ProxyTemplate) {
  if (props.readOnly) return
  emit('insert', tpl)
  dialogVisible.value = false
}

function onCloned(tpl: ProxyTemplate) {
  emit('cloned', tpl)
  void load()
}

function onCreated(tpl: ProxyTemplate) {
  void load()
  selected.value = tpl
  dialogVisible.value = true
}

onMounted(() => {
  void load()
})
watch(
  () => [props.core, props.category, props.listScope, props.explicitSlugs?.join('|'), props.templateText],
  () => {
    void load()
  },
)
</script>

<template>
  <Panel :header="panelHeader" class="template-side-panel h-full">
    <div v-if="core" class="mb-3">
      <IconField class="w-full">
        <InputIcon class="pi pi-search" />
        <InputText v-model="templateSearch" :placeholder="t('common.search')" class="w-full" />
      </IconField>
    </div>
    <div v-if="canCreate" class="mb-3">
      <Button
        icon="pi pi-plus"
        :label="t('template.new')"
        size="small"
        class="w-full"
        @click="createVisible = true"
      />
    </div>
    <p v-if="!core" class="text-muted-color text-sm m-0">{{ t('template.sidePanelHint') }}</p>
    <ul v-else class="list-none m-0 p-0 flex flex-col gap-1 template-side-list">
      <li
        v-for="tpl in templates"
        :key="tpl.id ?? tpl.slug"
        class="template-side-item rounded-border p-2 cursor-pointer transition-colors"
        :class="{ 'template-side-item--active': isIncluded(tpl.slug) }"
        @click="openTemplate(tpl)"
      >
        <div class="font-mono text-sm break-all">{{ templateDisplayName(tpl) }}</div>
        <div class="flex gap-1 mt-1 flex-wrap items-center">
          <SysBadge v-if="tpl.is_builtin" :customized="tpl.builtin_override" icon-only />
          <Tag
            v-if="isDirectlyIncluded(tpl.slug)"
            severity="info"
            :value="t('template.included')"
            class="text-xs"
          />
          <Tag
            v-else-if="isIncluded(tpl.slug)"
            severity="secondary"
            :value="t('template.referenced')"
            class="text-xs"
          />
        </div>
      </li>
      <li v-if="!templates.length" class="text-muted-color text-sm">{{ t('template.empty') }}</li>
    </ul>
  </Panel>

  <TemplateCreateDialog
    v-if="core && category"
    v-model:visible="createVisible"
    :core="core"
    :category="category"
    @created="onCreated"
  />

  <TemplateViewDialog
    v-model:visible="dialogVisible"
    :template="selected"
    :read-only="readOnly"
    :core="core"
    @insert="onInsert"
    @cloned="onCloned"
    @saved="onCloned"
  />
</template>

<style scoped>
.template-side-item:hover {
  background: var(--surface-hover);
}
.template-side-item--active {
  background: color-mix(in srgb, var(--primary-color) 12%, var(--surface-card));
  border-inline-start: 3px solid var(--primary-color);
}

.template-side-list {
  max-height: min(60vh, 32rem);
  overflow-y: auto;
  user-select: text;
}
</style>
