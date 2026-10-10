<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import { canShareImages, downloadQrPng, qrPngFile, shareWithImage } from '@/shared/utils/hiddify-qr'
import { isSuperAdmin } from '@/core/panelShell'
import type { ShareDomain } from '@/shared/utils/share-domain'

/**
 * A link on a chosen domain: domain dropdown, QR code (click or Copy QR, Download), the link (copy, open, share).
 * Used for admin links and user links. The default slot shows below the link actions.
 */
const props = defineProps<{
  title: string
  /** For the QR share card and file names. */
  name: string
  domains: ShareDomain[]
  /** Appended to the domain's base, e.g. `<uuid>/` or `<uuid>/#name`. */
  path: string
  /** Used when there are no domains. */
  fallbackLink?: string
  /** Adds "Test configs": opens the config tester with this link (super admins only). */
  testable?: boolean
}>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const domain = ref('')
const qrCode = ref<InstanceType<typeof HiddifyQrCode> | null>(null)
const copied = ref<'link' | 'qr' | null>(null)
let copiedTimer: number | undefined

const selected = computed(() => props.domains.find((d) => d.domain === domain.value) ?? props.domains[0] ?? null)
const link = computed(() => (selected.value ? `${selected.value.base}${props.path}` : (props.fallbackLink ?? '')))

watch(
  visible,
  (open) => {
    if (!open) return
    copied.value = null
    domain.value = props.domains[0]?.domain ?? ''
  },
  { immediate: true },
)

function flash(what: 'link' | 'qr') {
  copied.value = what
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = null), 2000)
}

async function copyLink() {
  await navigator.clipboard.writeText(link.value)
  flash('link')
}

const canShare = canShareImages()
/** Made ahead of the click: the share sheet must open right on it. */
const qrFile = ref<File | null>(null)
const sharing = ref(false)
/** The image being made for the current link (awaited if Share is clicked before it is ready). */
let preparing: Promise<File | null> | null = null

function fileBase(): string {
  return `${(props.name || 'link').replace(/[^\p{L}\p{N}_-]+/gu, '-')}-${selected.value?.domain ?? 'link'}`
}

// `immediate`: the dialog is often created already open (it appears together with its user / admin).
watch(
  [visible, link],
  ([open, value]) => {
    qrFile.value = null
    preparing = null
    if (!open || !value || !canShare) return
    // The link is printed on the image too, for apps that keep only the image.
    const job = qrPngFile(value, fileBase(), { title: props.name, caption: value }).catch(() => null)
    preparing = job
    void job.then((file) => {
      if (preparing === job) qrFile.value = file
    })
  },
  { immediate: true },
)

async function share() {
  if (sharing.value) return
  sharing.value = true
  try {
    // Not ready yet (or the image could not be made): wait for it, else share the link alone.
    const file = qrFile.value ?? (preparing ? await preparing : null)
    if (file) {
      const result = await shareWithImage(link.value, file, link.value)
      if (result === 'failed') toast.add({ severity: 'warn', summary: t('qr.shareFailed'), life: 5000 })
      return
    }
    try {
      await navigator.share({ text: link.value, url: link.value })
    } catch (err) {
      if ((err as { name?: string })?.name !== 'AbortError') toast.add({ severity: 'warn', summary: t('qr.shareFailed'), life: 5000 })
    }
  } finally {
    sharing.value = false
  }
}

function testConfigs() {
  visible.value = false
  void router.push({ name: 'config-tester', query: { url: link.value.split('#')[0], start: '1' } })
}

async function copyQr() {
  if (await qrCode.value?.copy()) flash('qr')
}

function downloadQr() {
  void downloadQrPng(link.value, fileBase())
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="title"
    :style="{ width: 'min(42rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div class="link-dlg">
      <!-- Domain -->
      <div class="link-dlg__field">
        <label for="share-link-domain" class="link-dlg__label">{{ t('linkShare.domain') }}</label>
        <Select v-model="domain" :options="domains" option-label="label" option-value="domain" input-id="share-link-domain" :filter="domains.length > 8" class="w-full">
          <template #value="{ value }">
            <span v-if="selected" class="link-dlg__opt">
              <i class="pi pi-globe" />
              <span dir="ltr" class="link-dlg__opt-name">{{ selected.label }}</span>
              <span v-if="selected.kind !== 'direct'" class="link-dlg__kind" :class="`link-dlg__kind--${selected.kind}`">{{ t(`linkShare.kind.${selected.kind}`) }}</span>
            </span>
            <span v-else>{{ value }}</span>
          </template>
          <template #option="{ option }">
            <span class="link-dlg__opt">
              <span dir="ltr" class="link-dlg__opt-name" :title="option.domain">{{ option.label }}</span>
              <span v-if="option.kind !== 'direct'" class="link-dlg__kind" :class="`link-dlg__kind--${option.kind}`">{{ t(`linkShare.kind.${option.kind}`) }}</span>
            </span>
          </template>
        </Select>
      </div>

      <div class="link-dlg__body">
        <!-- QR: click the code to copy it as an image -->
        <div class="link-dlg__qr-wrap">
          <HiddifyQrCode ref="qrCode" :value="link" />
          <div class="link-dlg__qr-actions">
            <Button :icon="copied === 'qr' ? 'pi pi-check' : 'pi pi-copy'" :label="copied === 'qr' ? t('common.copied') : t('qr.copy')" size="small" severity="secondary" outlined @click="copyQr" />
            <Button icon="pi pi-download" :label="t('linkShare.download')" size="small" severity="secondary" outlined @click="downloadQr" />
          </div>
        </div>

        <!-- Link -->
        <div class="link-dlg__side">
          <div class="link-dlg__field">
            <span class="link-dlg__label">{{ t('linkShare.link') }}</span>
            <code dir="ltr" class="link-dlg__link">{{ link }}</code>
          </div>
          <div class="link-dlg__link-actions">
            <Button :icon="copied === 'link' ? 'pi pi-check' : 'pi pi-copy'" :label="copied === 'link' ? t('common.copied') : t('linkShare.copyLink')" @click="copyLink" />
            <Button as="a" :href="link" target="_blank" rel="noopener" icon="pi pi-external-link" :label="t('linkShare.open')" severity="secondary" outlined />
            <Button v-if="testable && isSuperAdmin" icon="pi pi-bolt" :label="t('configTester.menu')" severity="secondary" outlined @click="testConfigs" />
            <Button v-if="canShare" icon="pi pi-share-alt" :label="t('qr.share')" severity="secondary" outlined :loading="sharing" v-tooltip.top="t('qr.shareHint')" @click="share" />
          </div>
          <slot />
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.link-dlg {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.link-dlg__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.link-dlg__label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.link-dlg__opt {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.link-dlg__opt > i {
  font-size: 0.85rem;
  color: var(--p-primary-color);
}
.link-dlg__opt-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-dlg__kind {
  --kind: var(--p-primary-color);
  flex-shrink: 0;
  padding: 0 0.4rem;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--kind);
  background: color-mix(in srgb, var(--kind) 14%, transparent);
}
.link-dlg__kind--cdn {
  --kind: var(--p-amber-600, #d97706);
}
.link-dlg__kind--auto {
  --kind: var(--p-green-600, #16a34a);
}
.link-dlg__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}
.link-dlg__qr-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}
.link-dlg__qr-actions {
  display: flex;
  gap: 0.4rem;
}
.link-dlg__side {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-width: 0;
}
.link-dlg__link {
  padding: 0.65rem 0.8rem;
  border-radius: 10px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
  font-size: 0.82rem;
  overflow-wrap: anywhere;
  text-align: start;
}
.link-dlg__link-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.link-dlg__link-actions > * {
  flex: 1 1 auto;
}
@media (max-width: 640px) {
  .link-dlg__body {
    grid-template-columns: 1fr;
  }
}
</style>
