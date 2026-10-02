<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { copyQrImage, drawHiddifyQr } from '@/shared/utils/hiddify-qr'

/** A Hiddify-style QR code (black on white, logo in the middle); clicking it copies the image. */
const props = withDefaults(defineProps<{ value: string; size?: number }>(), { size: 184 })
const emit = defineEmits<{ copied: [] }>()

const { t } = useI18n()
const toast = useToast()

const canvas = ref<HTMLCanvasElement | null>(null)
const copied = ref(false)
let timer: number | undefined

watch(
  [() => props.value, () => props.size, canvas],
  ([value, size, el]) => {
    if (value && el) void drawHiddifyQr(el, value, { size })
  },
  { immediate: true },
)

/** Copies the code as an image; shows the "Copied" overlay, or a hint where images can not be copied. */
async function copy(): Promise<boolean> {
  try {
    await copyQrImage(props.value)
  } catch {
    toast.add({ severity: 'warn', summary: t('qr.copyUnsupported'), life: 5000 })
    return false
  }
  flashCopied()
  emit('copied')
  return true
}

function flashCopied() {
  copied.value = true
  window.clearTimeout(timer)
  timer = window.setTimeout(() => (copied.value = false), 1800)
}

defineExpose({ copy, flashCopied })
</script>

<template>
  <button
    type="button"
    class="hqr"
    :class="{ 'hqr--copied': copied }"
    :aria-label="t('qr.copy')"
    v-tooltip.top="t('qr.clickToCopy')"
    @click="copy"
  >
    <canvas ref="canvas" :style="{ width: `${size}px`, height: `${size}px` }" />
    <span class="hqr__done" aria-hidden="true"><i class="pi pi-check" />{{ t('common.copied') }}</span>
  </button>
</template>

<style scoped>
/* White in dark mode too, so cameras can read the code. */
.hqr {
  position: relative;
  display: block;
  padding: 1.1rem;
  border-radius: 20px;
  border: 1px solid var(--p-content-border-color);
  background: #fff;
  font: inherit;
  cursor: copy;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}
.hqr:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 26px -16px rgba(15, 23, 42, 0.45);
}
.hqr:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 3px;
}
.hqr canvas {
  display: block;
}
.hqr__done {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border-radius: inherit;
  font-weight: 700;
  color: #fff;
  background: rgba(22, 163, 74, 0.82);
  opacity: 0;
  transform: scale(0.96);
  pointer-events: none;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.hqr--copied .hqr__done {
  opacity: 1;
  transform: none;
}
@media (prefers-reduced-motion: reduce) {
  .hqr,
  .hqr__done {
    transition: none;
  }
}
</style>
