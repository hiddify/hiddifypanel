<template>
  <p class="text-muted-color mt-0 mb-3">{{ t('qrTool.scanHint') }}</p>

  <div v-if="result === null" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Camera -->
    <section class="qr-scan__box" :aria-label="t('qrTool.camera')">
      <div v-if="cameraState === 'running' || cameraState === 'starting'" class="qr-scan__video-wrap">
        <video ref="video" class="qr-scan__video" muted playsinline autoplay />
        <div class="qr-scan__frame" aria-hidden="true" />
        <ProgressSpinner v-if="cameraState === 'starting'" class="qr-scan__spinner" stroke-width="4" />
      </div>
      <div v-else class="qr-scan__placeholder">
        <i class="pi pi-camera" aria-hidden="true" />
        <span>{{ t('qrTool.cameraHint') }}</span>
      </div>
      <Message v-if="cameraError" severity="error" size="small" :closable="false" class="w-full">{{ cameraError }}</Message>
      <div class="flex flex-wrap items-center justify-center gap-2">
        <Button v-if="cameraState === 'idle'" :label="t('qrTool.startCamera')" icon="pi pi-camera" :disabled="!cameraSupported" @click="startCamera()" />
        <Button v-else :label="t('qrTool.stopCamera')" icon="pi pi-stop-circle" severity="secondary" outlined @click="stopCamera" />
        <Select
          v-if="cameras.length > 1 && cameraState !== 'idle'"
          v-model="cameraId"
          :options="cameras"
          option-label="label"
          option-value="deviceId"
          :aria-label="t('qrTool.chooseCamera')"
          class="qr-scan__camera-select"
          @change="startCamera(cameraId)"
        />
      </div>
    </section>

    <!-- Image: choose, drop or paste -->
    <section
      class="qr-scan__box qr-scan__drop"
      :class="{ 'qr-scan__drop--over': dragOver }"
      :aria-label="t('qrTool.image')"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
    >
      <div class="qr-scan__placeholder">
        <ProgressSpinner v-if="decodingFile" class="qr-scan__spinner--inline" stroke-width="4" />
        <i v-else class="pi pi-image" aria-hidden="true" />
        <span>{{ t('qrTool.imageHint') }}</span>
      </div>
      <Message v-if="fileError" severity="warn" size="small" :closable="false" class="w-full">{{ fileError }}</Message>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileChosen" />
      <Button :label="t('qrTool.chooseImage')" icon="pi pi-upload" severity="secondary" outlined :loading="decodingFile" @click="fileInput?.click()" />
    </section>
  </div>

  <!-- Result -->
  <div v-else class="flex flex-col gap-3">
    <Message severity="success" :closable="false">{{ t('qrTool.found') }}</Message>
    <Textarea :model-value="result" readonly class="w-full font-mono text-sm qr-scan__result" dir="ltr" :auto-resize="false" :rows="6" :aria-label="t('qrTool.content')" />
    <div class="flex flex-wrap gap-2">
      <Button :label="t('common.copy')" icon="pi pi-copy" @click="copy" />
      <Button v-if="isWebUrl(result)" :label="t('qrTool.openLink')" icon="pi pi-external-link" severity="secondary" outlined @click="openLink" />
      <Button v-if="isShareLinkText(result)" :label="t('qrTool.inspect')" icon="pi pi-code" severity="secondary" outlined @click="emit('inspect', result)" />
      <Button :label="t('qrTool.makeFromThis')" icon="pi pi-qrcode" severity="secondary" outlined @click="emit('make', result)" />
      <Button :label="t('qrTool.scanAgain')" icon="pi pi-refresh" text @click="reset" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { decodeQr, decodeQrFile } from '@/shared/utils/qr-decode'
import { isShareLinkText, isWebUrl } from '@/features/qr-tool/qr-tool'

/**
 * Reads a QR code with the camera, or from an image (chosen, dropped, or pasted with Ctrl+V anywhere on the page).
 * Everything happens in the browser.
 */
const emit = defineEmits<{ inspect: [text: string]; make: [text: string] }>()

const { t } = useI18n()
const toast = useToast()

/** Time between two camera frames that are read: enough for a quick scan, light on the CPU. */
const FRAME_INTERVAL_MS = 200

type CameraState = 'idle' | 'starting' | 'running'
interface CameraOption {
  deviceId: string
  label: string
}

const result = ref<string | null>(null)
const video = ref<HTMLVideoElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const cameraState = ref<CameraState>('idle')
const cameraError = ref<string | null>(null)
const cameras = ref<CameraOption[]>([])
const cameraId = ref<string | null>(null)
const fileError = ref<string | null>(null)
const decodingFile = ref(false)
const dragOver = ref(false)

// Browsers give the camera only to secure pages (https or localhost).
const cameraSupported = window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === 'function'
if (!cameraSupported) cameraError.value = t('qrTool.cameraNeedsHttps')

let stream: MediaStream | null = null
let frameTimer: number | undefined
/** Bumped on every start/stop, so a camera that opens after Stop is closed right away. */
let session = 0

function cameraErrorText(err: unknown): string {
  const name = (err as { name?: string })?.name
  if (name === 'NotAllowedError' || name === 'SecurityError') return t('qrTool.cameraDenied')
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return t('qrTool.noCamera')
  if (name === 'NotReadableError') return t('qrTool.cameraBusy')
  return t('qrTool.cameraFailed')
}

async function startCamera(deviceId?: string | null) {
  stopCamera()
  const mine = ++session
  cameraError.value = null
  cameraState.value = 'starting'
  try {
    const opened = await navigator.mediaDevices.getUserMedia({
      video: deviceId ? { deviceId: { exact: deviceId } } : { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    if (mine !== session) {
      opened.getTracks().forEach((track) => track.stop())
      return
    }
    stream = opened
    await nextTick()
    if (!video.value) return
    video.value.srcObject = opened
    await video.value.play()
    cameraState.value = 'running'
    cameraId.value = opened.getVideoTracks()[0]?.getSettings().deviceId ?? null
    void listCameras()
    scheduleFrame(mine)
  } catch (err) {
    if (mine !== session) return
    stopCamera()
    cameraError.value = cameraErrorText(err)
  }
}

/** Camera names are known only once permission is given. */
async function listCameras() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices
      .filter((device) => device.kind === 'videoinput')
      .map((device, index) => ({ deviceId: device.deviceId, label: device.label || t('qrTool.cameraN', { n: index + 1 }) }))
  } catch {
    cameras.value = []
  }
}

function scheduleFrame(mine: number) {
  frameTimer = window.setTimeout(() => void readFrame(mine), FRAME_INTERVAL_MS)
}

async function readFrame(mine: number) {
  if (mine !== session || !video.value) return
  let text: string | null = null
  try {
    if (video.value.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) text = await decodeQr(video.value)
  } catch {
    // A frame that can't be read: try the next one.
  }
  if (mine !== session) return
  if (text) {
    stopCamera()
    navigator.vibrate?.(60)
    showResult(text)
    return
  }
  scheduleFrame(mine)
}

function stopCamera() {
  session++
  window.clearTimeout(frameTimer)
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  if (video.value) video.value.srcObject = null
  cameraState.value = 'idle'
}

async function readFile(file: File | null | undefined) {
  if (!file) return
  fileError.value = null
  if (!file.type.startsWith('image/')) {
    fileError.value = t('qrTool.notAnImage')
    return
  }
  decodingFile.value = true
  try {
    const text = await decodeQrFile(file)
    if (text) showResult(text)
    else fileError.value = t('qrTool.noCodeFound')
  } catch {
    fileError.value = t('qrTool.imageUnreadable')
  } finally {
    decodingFile.value = false
  }
}

function onFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  void readFile(input.files?.[0])
  input.value = '' // the same file can be chosen again
}

function onDrop(event: DragEvent) {
  dragOver.value = false
  void readFile(event.dataTransfer?.files?.[0])
}

/** An image pasted anywhere on the page (Ctrl+V of a screenshot); text pastes into fields are left alone. */
function onPaste(event: ClipboardEvent) {
  if (result.value !== null) return
  const item = Array.from(event.clipboardData?.items ?? []).find((entry) => entry.kind === 'file' && entry.type.startsWith('image/'))
  if (!item) return
  event.preventDefault()
  void readFile(item.getAsFile())
}

function showResult(text: string) {
  result.value = text
  fileError.value = null
}

function reset() {
  result.value = null
}

async function copy() {
  if (result.value === null) return
  try {
    await navigator.clipboard.writeText(result.value)
    toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
  } catch {
    toast.add({ severity: 'warn', summary: t('qrTool.copyFailed'), life: 4000 })
  }
}

function openLink() {
  if (result.value && isWebUrl(result.value)) window.open(result.value.trim(), '_blank', 'noopener,noreferrer')
}

onMounted(() => window.addEventListener('paste', onPaste))
onBeforeUnmount(() => {
  window.removeEventListener('paste', onPaste)
  stopCamera()
})

defineExpose({ stopCamera })
</script>

<style scoped>
.qr-scan__box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem;
  min-height: 18rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-content-border-radius, 12px);
  background: var(--p-content-background);
}
.qr-scan__drop {
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}
.qr-scan__drop--over {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}
.qr-scan__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
  text-align: center;
}
.qr-scan__placeholder .pi {
  font-size: 2.5rem;
}
.qr-scan__video-wrap {
  position: relative;
  width: 100%;
  max-width: 26rem;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: 12px;
  background: #000;
}
.qr-scan__video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
/* A guide square in the middle; the whole frame is read, not only this square. */
.qr-scan__frame {
  position: absolute;
  top: 50%;
  left: 50%;
  height: 70%;
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border: 3px solid rgba(255, 255, 255, 0.85);
  border-radius: 16px;
  box-shadow: 0 0 0 100vmax rgba(0, 0, 0, 0.25);
  pointer-events: none;
}
.qr-scan__spinner {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 3rem;
  height: 3rem;
}
.qr-scan__spinner--inline {
  width: 2.5rem;
  height: 2.5rem;
}
.qr-scan__camera-select {
  max-width: 16rem;
}
.qr-scan__result {
  min-height: 9rem;
  field-sizing: fixed;
}
@media (prefers-reduced-motion: reduce) {
  .qr-scan__drop {
    transition: none;
  }
}
</style>
