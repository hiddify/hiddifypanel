<template>
  <p class="text-muted-color mt-0 mb-3">{{ kind === 'base64' ? t('utils.base64Live') : t('utils.urlLive') }}</p>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div v-for="side in sides" :key="side.role" class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <label class="font-medium flex items-center gap-2">
          <i :class="side.role === 'encoded' ? 'pi pi-lock' : 'pi pi-align-left'" />{{ side.label }}
        </label>
        <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="copy(side.value)" />
      </div>
      <Textarea
        :model-value="side.value"
        class="w-full font-mono text-sm util-textarea"
        :class="{ 'util-textarea--invalid': side.role === 'encoded' && !!error }"
        :auto-resize="false"
        :rows="12"
        spellcheck="false"
        dir="ltr"
        :aria-label="side.label"
        @update:model-value="(v: string | undefined) => (side.role === 'encoded' ? onEncodedInput(v ?? '') : onPlainInput(v ?? ''))"
      />
    </div>
  </div>
  <div class="flex flex-wrap items-center gap-2 mt-3">
    <Button :label="t('utils.swap')" icon="pi pi-sort-alt" severity="secondary" outlined @click="swapped = !swapped" />
    <label v-if="kind === 'base64'" class="flex items-center gap-2 cursor-pointer">
      <Checkbox v-model="urlSafe" binary input-id="util-urlsafe" @update:model-value="reencode" />
      <span>{{ t('utils.urlSafe') }}</span>
    </label>
    <Button icon="pi pi-trash" :label="t('utils.clear')" text severity="secondary" :disabled="!plain && !encoded" @click="clear" />
    <Message v-if="notice" severity="info" size="small" :closable="false" class="util-notice">{{ notice }}</Message>
  </div>
  <Message v-if="error" severity="error" class="mt-3" :closable="false">{{ error }}</Message>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'
import { decodeIfBase64, decodeUrl, decodeUtf8Base64, encodeUrl, encodeUtf8Base64, splitProtocolPrefix } from '@/shared/utils/text-codecs'

/**
 * Both sides are live: type Base64 and the text updates, type text and the Base64 updates. A `vmess://` (any
 * protocol://) in front of the Base64 is kept and ignored when decoding. Text that is really Base64 pasted into
 * the text side swaps the two sides by itself.
 */
const props = defineProps<{ kind: 'base64' | 'url' }>()
const { t } = useI18n()
const toast = useToast()

const plain = ref('')
const encoded = ref('')
/** The `protocol://` in front of the Base64, put back when text is encoded. */
const prefix = ref('')
/** Base64 on the left instead of the right. */
const swapped = ref(false)
const urlSafe = ref(false)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)

const sides = computed(() => {
  const base64 = { role: 'encoded' as const, label: props.kind === 'base64' ? t('utils.base64Label') : t('utils.urlEncodedLabel'), value: encoded.value }
  const text = { role: 'plain' as const, label: t('utils.textLabel'), value: plain.value }
  return swapped.value ? [base64, text] : [text, base64]
})

function encodeText(value: string): string {
  return props.kind === 'base64' ? prefix.value + encodeUtf8Base64(value, urlSafe.value) : encodeUrl(value)
}

function decodeText(body: string): string {
  return props.kind === 'base64' ? decodeUtf8Base64(body) : decodeUrl(body)
}

/** Is this text really in the encoded form (so it belongs on the other side)? */
function looksEncoded(value: string): boolean {
  if (props.kind === 'base64') return decodeIfBase64(splitProtocolPrefix(value)[1]) !== null
  if (!/%[0-9a-f]{2}/i.test(value)) return false
  try {
    return decodeUrl(value) !== value
  } catch {
    return false
  }
}

function onEncodedInput(value: string) {
  encoded.value = value
  notice.value = null
  // Base64 only: a protocol:// in front is not part of it
  const [protocol, body] = props.kind === 'base64' ? splitProtocolPrefix(value) : ['', value]
  prefix.value = protocol
  if (!body.trim()) {
    plain.value = ''
    error.value = null
    return
  }
  try {
    plain.value = decodeText(body)
    error.value = null
  } catch {
    error.value = props.kind === 'base64' ? t('utils.notBase64') : t('utils.notUrlEncoded')
  }
}

function onPlainInput(value: string) {
  // Encoded text landed on the plain side: it belongs on the other one
  if (looksEncoded(value)) {
    swapped.value = !swapped.value
    onEncodedInput(value.trim())
    notice.value = t('utils.autoSwapped')
    return
  }
  plain.value = value
  notice.value = null
  error.value = null
  encoded.value = value ? encodeText(value) : ''
}

/** URL-safe changed: encode the text again. */
function reencode() {
  if (plain.value) encoded.value = encodeText(plain.value)
}

function clear() {
  plain.value = ''
  encoded.value = ''
  prefix.value = ''
  error.value = null
  notice.value = null
}

async function copy(value: string) {
  await navigator.clipboard.writeText(value)
  toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
}
</script>

<style scoped>
.util-textarea--invalid {
  border-color: var(--p-red-500, #ef4444);
}
.util-notice {
  margin: 0;
}
</style>
