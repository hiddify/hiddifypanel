<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <label class="font-medium">{{ leftLabel }}</label>
        <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="copy(left)" />
      </div>
      <Textarea v-model="left" class="w-full font-mono text-sm util-textarea" :auto-resize="false" :rows="12" spellcheck="false" />
    </div>
    <div class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <label class="font-medium">{{ rightLabel }}</label>
        <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="copy(right)" />
      </div>
      <Textarea v-model="right" class="w-full font-mono text-sm util-textarea" :auto-resize="false" :rows="12" spellcheck="false" />
    </div>
  </div>
  <div class="flex flex-wrap gap-2 mt-3">
    <Button :label="encodeLabel" icon="pi pi-arrow-right" @click="runEncode" />
    <Button :label="decodeLabel" icon="pi pi-arrow-left" severity="secondary" @click="runDecode" />
    <Button :label="t('utils.swap')" icon="pi pi-sort-alt" severity="secondary" outlined @click="swap" />
    <Button v-if="showUrlSafe" :label="t('utils.urlSafe')" :severity="urlSafe ? 'primary' : 'secondary'" outlined @click="urlSafe = !urlSafe" />
  </div>
  <Message v-if="error" severity="error" class="mt-3" :closable="false">{{ error }}</Message>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'

const props = defineProps<{
  leftLabel: string
  rightLabel: string
  encodeLabel: string
  decodeLabel: string
  encode: (value: string, urlSafe?: boolean) => string
  decode: (value: string, urlSafe?: boolean) => string
  showUrlSafe?: boolean
}>()

const { t } = useI18n()
const toast = useToast()
const left = defineModel<string>('left', { default: '' })
const right = defineModel<string>('right', { default: '' })
const urlSafe = ref(false)
const error = ref<string | null>(null)

function runEncode() {
  error.value = null
  try {
    right.value = props.encode(left.value, urlSafe.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function runDecode() {
  error.value = null
  try {
    right.value = props.decode(left.value, urlSafe.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function swap() {
  const next = right.value
  right.value = left.value
  left.value = next
}

async function copy(value: string) {
  await navigator.clipboard.writeText(value)
  toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
}
</script>
