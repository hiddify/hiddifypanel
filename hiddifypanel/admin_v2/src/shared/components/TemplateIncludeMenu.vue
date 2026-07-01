<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tag from 'primevue/tag'
import SysBadge from '@/shared/components/SysBadge.vue'
import { proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'
import {
  expandReferencedTemplateSlugs,
  parseReferencedTemplateSlugs,
  sortTemplatesByIncluded,
  templateDisplayName,
  asTemplateSlugList,
} from '@/shared/utils/template-slug'

const props = withDefaults(
  defineProps<{
    core?: string
    category?: string
    templateText?: string
    explicitSlugs?: string[]
    readOnly?: boolean
    listScope?: 'category' | 'core'
  }>(),
  {
    listScope: 'category',
  },
)

const emit = defineEmits<{
  select: [template: ProxyTemplate]
}>()

const { t } = useI18n()
const popoverRef = ref<InstanceType<typeof Popover> | null>(null)
const raw = ref<ProxyTemplate[]>([])
const query = ref('')
const loading = ref(false)
const expandedSlugs = ref<string[]>([])

const directReferencedSlugs = computed(() =>
  parseReferencedTemplateSlugs(props.templateText ?? '', asTemplateSlugList(props.explicitSlugs)),
)

const referencedSlugs = computed(() =>
  expandedSlugs.value.length ? expandedSlugs.value : directReferencedSlugs.value,
)

const templates = computed(() => sortTemplatesByIncluded(raw.value, referencedSlugs.value))

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return templates.value
  return templates.value.filter(
    (tpl) =>
      tpl.slug.toLowerCase().includes(q) ||
      tpl.name.toLowerCase().includes(q) ||
      (tpl.description || '').toLowerCase().includes(q),
  )
})

function isIncluded(slug: string) {
  return referencedSlugs.value.includes(slug)
}

function isDirectlyIncluded(slug: string) {
  return directReferencedSlugs.value.includes(slug)
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
  expandedSlugs.value = expandReferencedTemplateSlugs(seeds, contentBySlug)
}

async function load() {
  if (!props.core) {
    raw.value = []
    expandedSlugs.value = []
    return
  }
  loading.value = true
  try {
    const list =
      props.listScope === 'core' || !props.category
        ? await proxyTemplatesApi.list({ core: props.core })
        : await proxyTemplatesApi.list({ core: props.core, category: props.category })
    const bySlug = new Map(list.map((tpl) => [tpl.slug, tpl]))
    for (const slug of directReferencedSlugs.value) {
      if (slug && !bySlug.has(slug)) {
        const all = await proxyTemplatesApi.list({ core: props.core })
        const tpl = all.find((item) => item.slug === slug)
        if (tpl) bySlug.set(slug, tpl)
      }
    }
    raw.value = [...bySlug.values()]
    await refreshExpandedSlugs()
  } finally {
    loading.value = false
  }
}

function toggle(event: Event) {
  popoverRef.value?.toggle(event)
}

function onShow() {
  query.value = ''
  void load()
}

function pick(tpl: ProxyTemplate) {
  if (props.readOnly) return
  emit('select', tpl)
  popoverRef.value?.hide()
}

onMounted(() => {
  void load()
})
watch(
  () => [props.core, props.category, props.listScope, asTemplateSlugList(props.explicitSlugs).join('|'), props.templateText],
  () => {
    void load()
  },
)
</script>

<template>
  <Button
    icon="pi pi-file-import"
    :label="t('editor.includeTemplate')"
    severity="secondary"
    size="small"
    :disabled="!core"
    @click="toggle"
  />
  <Popover ref="popoverRef" class="template-include-popover" @show="onShow">
    <div class="w-72 max-w-[90vw] flex flex-col gap-2">
      <IconField class="w-full">
        <InputIcon class="pi pi-search" />
        <InputText v-model="query" :placeholder="t('common.search')" class="w-full" />
      </IconField>
      <div v-if="loading" class="text-muted-color text-sm py-2 text-center">…</div>
      <ul v-else class="list-none m-0 p-0 max-h-64 overflow-y-auto flex flex-col gap-1">
        <li
          v-for="tpl in filtered"
          :key="tpl.id ?? tpl.slug"
          class="rounded-border p-2 cursor-pointer transition-colors hover:bg-[var(--surface-hover)]"
          @click="pick(tpl)"
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
        <li v-if="!filtered.length" class="text-muted-color text-sm py-2 text-center">{{ t('template.empty') }}</li>
      </ul>
    </div>
  </Popover>
</template>
