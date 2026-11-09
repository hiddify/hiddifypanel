<template>
  <p class="text-muted-color mt-0 mb-3">{{ t('qrTool.makeHint') }}</p>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="flex flex-col gap-2 min-w-0">
      <div class="flex items-center justify-between gap-2">
        <label for="qr-maker-text" class="font-medium">{{ t('qrTool.content') }}</label>
        <Button icon="pi pi-trash" text rounded size="small" severity="secondary" :aria-label="t('utils.clear')" :disabled="!text" @click="text = ''" />
      </div>
      <Textarea
        id="qr-maker-text"
        v-model="text"
        class="w-full font-mono text-sm qr-maker__input"
        dir="ltr"
        :auto-resize="false"
        :rows="10"
        spellcheck="false"
        :placeholder="t('qrTool.contentPlaceholder')"
      />
      <div class="flex flex-wrap items-center justify-between gap-2">
        <SelectButton v-model="style" :options="styleOptions" option-label="label" option-value="value" :allow-empty="false" :aria-label="t('qrTool.style')" />
        <small class="text-muted-color" dir="ltr">{{ t('qrTool.bytes', { count: bytes }) }}</small>
      </div>
      <small class="text-muted-color">{{ style === 'hiddify' ? t('qrTool.styleHiddifyHint') : t('qrTool.stylePlainHint') }}</small>
    </div>

    <div class="flex flex-col items-center justify-center gap-3 min-w-0">
      <div v-if="!text.trim()" class="qr-maker__empty">
        <i class="pi pi-qrcode" aria-hidden="true" />
        <span>{{ t('qrTool.emptyPreview') }}</span>
      </div>
      <Message v-else-if="tooLong" severity="warn" :closable="false" class="w-full">
        {{ style === 'hiddify' && fitsPlain ? t('qrTool.tooLongHiddify') : t('qrTool.tooLong') }}
        <Button v-if="style === 'hiddify' && fitsPlain" :label="t('qrTool.usePlain')" size="small" text class="ms-1" @click="style = 'plain'" />
      </Message>
      <template v-else>
        <div class="qr-maker__card">
          <canvas ref="canvas" :aria-label="t('qrTool.preview')" role="img" />
        </div>
        <div class="flex flex-wrap justify-center gap-2">
          <Button :label="t('qrTool.download')" icon="pi pi-download" @click="download" />
          <Button :label="t('qr.copy')" icon="pi pi-copy" severity="secondary" outlined :disabled="!canCopyImage" @click="copyImage" />
          <Button v-if="canShare" :label="t('qr.share')" icon="pi pi-share-alt" severity="secondary" outlined @click="share" />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { canShareImages } from '@/shared/utils/hiddify-qr'
import { drawQr, qrFits, qrPng, utf8Length, type QrStyle } from '@/features/qr-tool/qr-tool'

/** Live preview while typing; the PNG (download, copy, share) is made from the same text and style. */
const text = defineModel<string>('text', { default: '' })

const { t } = useI18n()
const toast = useToast()

const PREVIEW_SIZE = 240
const style = ref<QrStyle>('hiddify')
const canvas = ref<HTMLCanvasElement | null>(null)
const styleOptions = computed(() => [
  { label: t('qrTool.styleHiddify'), value: 'hiddify' as const },
  { label: t('qrTool.stylePlain'), value: 'plain' as const },
])

const bytes = computed(() => utf8Length(text.value))
const fits = ref(true)
const fitsPlain = ref(true)
const tooLong = computed(() => !fits.value)
const canCopyImage = typeof ClipboardItem !== 'undefined' && typeof navigator.clipboard?.write === 'function'
const canShare = canShareImages()

let timer: number | undefined
watch(
  [text, style],
  () => {
    window.clearTimeout(timer)
    timer = window.setTimeout(render, 150)
  },
  { immediate: true },
)
onBeforeUnmount(() => window.clearTimeout(timer))

async function render() {
  const value = text.value
  if (!value.trim()) return
  fits.value = qrFits(value, style.value)
  fitsPlain.value = style.value === 'plain' ? fits.value : qrFits(value, 'plain')
  if (!fits.value) return
  await nextTick() // the canvas appears once the text fits
  if (canvas.value) await drawQr(canvas.value, value, style.value, PREVIEW_SIZE)
}

function fileName(): string {
  return `qr-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.png`
}

async function download() {
  const url = URL.createObjectURL(await qrPng(text.value, style.value))
  const a = document.createElement('a')
  a.href = url
  a.download = fileName()
  a.click()
  URL.revokeObjectURL(url)
}

async function copyImage() {
  try {
    // The promise goes straight to ClipboardItem so Safari keeps the click's permission.
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': qrPng(text.value, style.value) })])
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    toast.add({ severity: 'warn', summary: t('qr.copyUnsupported'), life: 5000 })
  }
}

async function share() {
  const file = new File([await qrPng(text.value, style.value)], fileName(), { type: 'image/png' })
  try {
    await navigator.share({ files: [file] })
  } catch (err) {
    if ((err as { name?: string })?.name !== 'AbortError') toast.add({ severity: 'warn', summary: t('qrTool.shareFailed'), life: 4000 })
  }
}
</script>

<style scoped>
.qr-maker__input {
  min-height: 14rem;
  field-sizing: fixed;
}
/* White in dark mode too, so cameras can read the code. */
.qr-maker__card {
  padding: 1.1rem;
  border-radius: 20px;
  border: 1px solid var(--p-content-border-color);
  background: #fff;
}
.qr-maker__card canvas {
  display: block;
  width: min(240px, 100%);
  height: auto;
  aspect-ratio: 1;
}
.qr-maker__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem 1rem;
  width: 100%;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-content-border-radius, 12px);
  color: var(--p-text-muted-color);
  text-align: center;
}
.qr-maker__empty .pi {
  font-size: 2.5rem;
}
</style>
