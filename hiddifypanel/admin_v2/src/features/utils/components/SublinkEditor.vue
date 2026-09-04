<template>
  <div class="flex flex-col gap-3">
    <p v-if="!links.length" class="text-muted-color m-0">{{ t('utils.emptyLinks') }}</p>
    <Fieldset
      v-for="(link, index) in links"
      :key="index"
      :legend="linkTitle(link, index)"
      :toggleable="links.length > 1"
    >
      <Message v-if="link.kind === 'error'" severity="error" :closable="false">{{ link.error }}</Message>
      <template v-else-if="link.kind === 'vmess'">
        <label class="font-medium block mb-2">{{ t('utils.vmessJson') }}</label>
        <Textarea
          :model-value="link.json"
          class="w-full font-mono text-sm sublink-json"
          :auto-resize="false"
          :rows="18"
          spellcheck="false"
          :readonly="readonly"
          @update:model-value="(value: string) => updateVmess(index, value)"
        />
        <Message v-if="vmessError[index]" severity="error" class="mt-2" :closable="false">{{ vmessError[index] }}</Message>
      </template>
      <template v-else>
        <HorizontalField :label="t('utils.protocol')" :input-id="`${idPrefix}proto-${index}`">
          <InputText :id="`${idPrefix}proto-${index}`" class="w-full" :readonly="readonly" :model-value="link.protocol" @update:model-value="(value: string) => patchUri(index, { protocol: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.server')" :input-id="`${idPrefix}server-${index}`">
          <InputText :id="`${idPrefix}server-${index}`" class="w-full" :readonly="readonly" :model-value="link.server" @update:model-value="(value: string) => patchUri(index, { server: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.port')" :input-id="`${idPrefix}port-${index}`">
          <InputText :id="`${idPrefix}port-${index}`" class="w-full" :readonly="readonly" :model-value="link.port" @update:model-value="(value: string) => patchUri(index, { port: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.user')" :input-id="`${idPrefix}user-${index}`">
          <InputText :id="`${idPrefix}user-${index}`" class="w-full" :readonly="readonly" :model-value="link.user" @update:model-value="(value: string) => patchUri(index, { user: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.pass')" :input-id="`${idPrefix}pass-${index}`">
          <InputText :id="`${idPrefix}pass-${index}`" class="w-full" :readonly="readonly" :model-value="link.password" @update:model-value="(value: string) => patchUri(index, { password: value })" />
        </HorizontalField>
        <HorizontalField v-if="link.protocol === 'ss' || link.method" :label="t('utils.method')" :input-id="`${idPrefix}method-${index}`">
          <InputText :id="`${idPrefix}method-${index}`" class="w-full" :readonly="readonly" :model-value="link.method" @update:model-value="(value: string) => patchUri(index, { method: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.path')" :input-id="`${idPrefix}path-${index}`">
          <InputText :id="`${idPrefix}path-${index}`" class="w-full" :readonly="readonly" :model-value="link.path" @update:model-value="(value: string) => patchUri(index, { path: value })" />
        </HorizontalField>
        <HorizontalField :label="t('utils.fragment')" :input-id="`${idPrefix}frag-${index}`">
          <InputText :id="`${idPrefix}frag-${index}`" class="w-full" :readonly="readonly" :model-value="link.fragment" @update:model-value="(value: string) => patchUri(index, { fragment: value })" />
        </HorizontalField>

        <div class="flex items-center justify-between mb-2 mt-3">
          <span class="font-semibold">{{ t('utils.queryParams') }}</span>
          <Button v-if="!readonly" icon="pi pi-plus" size="small" :label="t('utils.addQuery')" @click="addParam(index)" />
        </div>
        <div v-for="(param, pIndex) in link.params" :key="pIndex" class="flex gap-2 mb-2 items-start">
          <InputText class="w-36 shrink-0" :placeholder="t('utils.queryKey')" :readonly="readonly" :model-value="param.key" @update:model-value="(value: string) => patchParam(index, pIndex, 'key', value)" />
          <InputText class="flex-auto min-w-0" :placeholder="t('utils.queryValue')" :readonly="readonly" :model-value="param.value" @update:model-value="(value: string) => patchParam(index, pIndex, 'value', value)" />
          <Button v-if="!readonly" icon="pi pi-times" text rounded severity="danger" :aria-label="t('common.delete')" @click="removeParam(index, pIndex)" />
        </div>
        <p v-if="!link.params.length" class="text-muted-color text-sm mt-0 mb-3">{{ t('utils.noQuery') }}</p>

        <label class="font-semibold block mb-1 mt-3">{{ t('utils.extraJson') }}</label>
        <small class="block mb-2 text-muted-color">{{ t('utils.extraHint') }}</small>
        <Textarea
          class="w-full font-mono text-sm sublink-json"
          :auto-resize="false"
          :rows="14"
          spellcheck="false"
          :placeholder="'{\n  \n}'"
          :readonly="readonly"
          :model-value="link.extra"
          @update:model-value="(value: string) => updateExtra(index, value)"
        />
        <Message v-if="extraError[index]" severity="error" class="mt-2" :closable="false">{{ extraError[index] }}</Message>
      </template>
    </Fieldset>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Fieldset from 'primevue/fieldset'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import {
  isPrettyUriLink,
  isPrettyVmessLink,
  linkTitle,
  type PrettyLink,
  type PrettyUriLink,
} from '@/shared/utils/sublink-pretty'

const props = withDefaults(
  defineProps<{
    readonly?: boolean
    idPrefix?: string
  }>(),
  { readonly: false, idPrefix: '' },
)

const links = defineModel<PrettyLink[]>('links', { default: () => [] })
const emit = defineEmits<{ change: [] }>()

const { t } = useI18n()
const extraError = ref<Record<number, string>>({})
const vmessError = ref<Record<number, string>>({})

function emitChange() {
  emit('change')
}

function replace(index: number, next: PrettyLink) {
  const copy = links.value.slice()
  copy[index] = next
  links.value = copy
  emitChange()
}

function updateVmess(index: number, json: string) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyVmessLink(link)) return
  try {
    const parsed = JSON.parse(json || '{}') as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(t('utils.vmessObject'))
    }
    vmessError.value = { ...vmessError.value, [index]: '' }
    replace(index, { ...link, json })
  } catch (err) {
    vmessError.value = { ...vmessError.value, [index]: err instanceof Error ? err.message : String(err) }
    const copy = links.value.slice()
    copy[index] = { ...link, json }
    links.value = copy
  }
}

function patchUri(index: number, patch: Partial<PrettyUriLink>) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyUriLink(link)) return
  replace(index, { ...link, ...patch })
}

function patchParam(index: number, pIndex: number, field: 'key' | 'value', value: string) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyUriLink(link)) return
  const params = link.params.map((param, i) => (i === pIndex ? { ...param, [field]: value } : param))
  replace(index, { ...link, params })
}

function addParam(index: number) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyUriLink(link)) return
  replace(index, { ...link, params: [...link.params, { key: '', value: '' }] })
}

function removeParam(index: number, pIndex: number) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyUriLink(link)) return
  replace(index, { ...link, params: link.params.filter((_, i) => i !== pIndex) })
}

function updateExtra(index: number, extra: string) {
  if (props.readonly) return
  const link = links.value[index]
  if (!isPrettyUriLink(link)) return
  if (extra.trim()) {
    try {
      JSON.parse(extra)
      extraError.value = { ...extraError.value, [index]: '' }
    } catch (err) {
      extraError.value = { ...extraError.value, [index]: err instanceof Error ? err.message : String(err) }
      const copy = links.value.slice()
      copy[index] = { ...link, extra }
      links.value = copy
      return
    }
  } else {
    extraError.value = { ...extraError.value, [index]: '' }
  }
  replace(index, { ...link, extra })
}
</script>

<style scoped>
.sublink-json {
  min-height: 16rem;
  field-sizing: fixed;
}
</style>

