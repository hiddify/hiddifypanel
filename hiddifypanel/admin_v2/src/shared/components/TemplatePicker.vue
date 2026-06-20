<template>
  <MultiSelect
    v-model="selected"
    :options="templates"
    option-label="label"
    option-value="value"
    :placeholder="t('proxy.templateSlugs')"
    filter
    display="chip"
    @update:model-value="onChange"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiSelect from 'primevue/multiselect'
import { proxyTemplatesApi } from '@/core/api/generated'

const props = defineProps<{
  modelValue: string[]
  core?: string
  category?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
  select: [slug: string, content: string]
}>()

const { t } = useI18n()
const raw = ref<{ slug: string; name: string; content?: string }[]>([])

const selected = computed({
  get: () => props.modelValue ?? [],
  set: (v) => emit('update:modelValue', v),
})

const templates = computed(() =>
  raw.value.map((t) => ({ label: `${t.name} (${t.slug})`, value: t.slug, content: t.content })),
)

async function load() {
  raw.value = await proxyTemplatesApi.list({
    core: props.core,
    category: props.category,
  })
}

function onChange(slugs: string[]) {
  emit('update:modelValue', slugs)
  const last = slugs[slugs.length - 1]
  const tpl = raw.value.find((x) => x.slug === last)
  if (tpl?.content) {
    emit('select', tpl.slug, tpl.content)
  }
}

onMounted(load)
watch(() => [props.core, props.category], load)
</script>
