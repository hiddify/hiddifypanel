<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import { canShareImages, downloadQrPng, qrPngFile, shareWithImage } from '@/shared/utils/hiddify-qr'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import type { AdminRow, LinkDomain } from '@/features/admins/api'

const props = defineProps<{ admin: AdminRow | null; domains: LinkDomain[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ resetPassword: [admin: AdminRow] }>()

const { t } = useI18n()
const toast = useToast()

const domain = ref('')
const qrCode = ref<InstanceType<typeof HiddifyQrCode> | null>(null)
const copied = ref<'link' | 'qr' | null>(null)
let copiedTimer: number | undefined

const selected = computed(() => props.domains.find((d) => d.domain === domain.value) ?? props.domains[0] ?? null)
const link = computed(() => {
  if (!props.admin) return ''
  return selected.value ? `${selected.value.base}${props.admin.uuid}/` : props.admin.admin_link
})

watch(visible, (open) => {
  if (!open) return
  copied.value = null
  domain.value = props.domains[0]?.domain ?? ''
})

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

function fileBase(): string {
  return `${(props.admin?.name || 'admin').replace(/[^\p{L}\p{N}_-]+/gu, '-')}-${selected.value?.domain ?? 'link'}`
}

watch([visible, link], async ([open, value]) => {
  qrFile.value = null
  if (open && value && canShare) {
    // The link is printed on the image too, for apps that keep only the image.
    const file = await qrPngFile(value, fileBase(), { title: props.admin?.name, caption: value })
    if (value === link.value) qrFile.value = file
  }
})

async function share() {
  if (!qrFile.value || sharing.value) return
  sharing.value = true
  const result = await shareWithImage(link.value, qrFile.value, link.value)
  sharing.value = false
  if (result === 'failed') toast.add({ severity: 'warn', summary: t('qr.shareFailed'), life: 5000 })
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
    :header="t('admins.linkDialog.title', { name: admin?.name ?? '' })"
    :style="{ width: 'min(42rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div v-if="admin" class="link-dlg">
      <!-- Domain -->
      <div class="link-dlg__field">
        <label for="admin-link-domain" class="link-dlg__label">{{ t('admins.linkDialog.domain') }}</label>
        <Select
          v-model="domain"
          :options="domains"
          option-label="label"
          option-value="domain"
          input-id="admin-link-domain"
          :filter="domains.length > 8"
          class="w-full"
        >
          <template #value="{ value }">
            <span v-if="selected" class="link-dlg__opt">
              <i class="pi pi-globe" />
              <span dir="ltr" class="link-dlg__opt-name">{{ selected.label }}</span>
              <span v-if="selected.kind !== 'direct'" class="link-dlg__kind" :class="`link-dlg__kind--${selected.kind}`">{{ t(`admins.linkDialog.kind.${selected.kind}`) }}</span>
            </span>
            <span v-else>{{ value }}</span>
          </template>
          <template #option="{ option }">
            <span class="link-dlg__opt">
              <span dir="ltr" class="link-dlg__opt-name" :title="option.domain">{{ option.label }}</span>
              <span v-if="option.kind !== 'direct'" class="link-dlg__kind" :class="`link-dlg__kind--${option.kind}`">{{ t(`admins.linkDialog.kind.${option.kind}`) }}</span>
            </span>
          </template>
        </Select>
      </div>

      <div class="link-dlg__body">
        <!-- QR -->
        <div class="link-dlg__qr-wrap">
          <!-- Click the code to copy it as an image -->
          <HiddifyQrCode ref="qrCode" :value="link" />
          <div class="link-dlg__qr-actions">
            <Button :icon="copied === 'qr' ? 'pi pi-check' : 'pi pi-copy'" :label="copied === 'qr' ? t('common.copied') : t('qr.copy')" size="small" severity="secondary" outlined @click="copyQr" />
            <Button icon="pi pi-download" :label="t('admins.linkDialog.download')" size="small" severity="secondary" outlined @click="downloadQr" />
          </div>
        </div>

        <!-- Link -->
        <div class="link-dlg__side">
          <div class="link-dlg__field">
            <span class="link-dlg__label">{{ t('admins.col.link') }}</span>
            <code dir="ltr" class="link-dlg__link">{{ link }}</code>
          </div>
          <div class="link-dlg__link-actions">
            <Button :icon="copied === 'link' ? 'pi pi-check' : 'pi pi-copy'" :label="copied === 'link' ? t('common.copied') : t('admins.copyLink')" @click="copyLink" />
            <Button as="a" :href="link" target="_blank" rel="noopener" icon="pi pi-external-link" :label="t('admins.linkDialog.open')" severity="secondary" outlined />
            <Button
              v-if="canShare"
              icon="pi pi-share-alt"
              :label="t('qr.share')"
              severity="secondary"
              outlined
              :loading="sharing || !qrFile"
              v-tooltip.top="t('qr.shareHint')"
              @click="share"
            />
          </div>

          <div class="link-dlg__pw">
            <i class="pi" :class="admin.has_password ? 'pi-key' : 'pi-unlock'" />
            <div class="flex-1 min-w-0">
              <div class="font-medium">{{ admin.has_password ? t('admins.linkDialog.pwSet') : t('admins.linkDialog.pwNone') }}</div>
              <small class="text-muted-color">{{ t('admins.linkDialog.pwHint') }}</small>
            </div>
            <Button v-if="admin.can_edit" icon="pi pi-refresh" :label="t('admins.resetPassword')" size="small" severity="warn" text @click="emit('resetPassword', admin)" />
          </div>
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
.link-dlg__pw {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 8%, transparent);
  font-size: 0.88rem;
}
.link-dlg__pw > i {
  color: var(--p-amber-600, #d97706);
}
@media (max-width: 640px) {
  .link-dlg__body {
    grid-template-columns: 1fr;
  }
  .link-dlg__pw {
    flex-wrap: wrap;
  }
}
</style>
