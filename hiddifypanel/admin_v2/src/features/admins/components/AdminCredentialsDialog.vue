<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import { canShareImages, copyMessageWithQr, qrPngFile, shareWithImage } from '@/shared/utils/hiddify-qr'
import type { AdminCredentials } from '@/features/admins/api'

/** `created`: a new admin; `reset`: an existing admin got a new password. */
const props = defineProps<{ name: string; credentials: AdminCredentials | null; kind: 'created' | 'reset' }>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
const toast = useToast()
const qrCode = ref<InstanceType<typeof HiddifyQrCode> | null>(null)
const copied = ref<'message' | 'link' | 'password' | null>(null)
const showPassword = ref(false)
let copiedTimer: number | undefined

// With an alias: link (no UUID) + username + password; else the UUID link + password.
const message = computed(() => {
  const c = props.credentials
  if (!c) return ''
  return c.alias
    ? t('admins.credentials.messageAlias', { link: c.admin_link, alias: c.alias, password: c.password })
    : t('admins.credentials.message', { link: c.admin_link, password: c.password })
})

const canShare = canShareImages()
/** Made when the dialog opens: the share sheet must open right on the click. */
const qrFile = ref<File | null>(null)
const sharing = ref(false)
/** The image being made (awaited if Share is clicked before it is ready). */
let preparing: Promise<File | null> | null = null

watch(visible, (open) => {
  if (open) {
    copied.value = null
    showPassword.value = false
  }
})

watch(
  [visible, () => props.credentials?.admin_link],
  ([open, link]) => {
    qrFile.value = null
    preparing = null
    if (!open || !link || !canShare) return
    // The image carries the name and link (never the password), for apps that keep only the image.
    const job = qrPngFile(link, `${(props.name || 'admin').replace(/[^\p{L}\p{N}_-]+/gu, '-')}-qr`, { title: props.name, caption: link }).catch(() => null)
    preparing = job
    void job.then((file) => {
      if (preparing === job) qrFile.value = file
    })
  },
  { immediate: true },
)

/** Message + QR image together into Telegram, WhatsApp, mail… */
async function share() {
  if (sharing.value) return
  sharing.value = true
  try {
    // Not ready yet (or the image could not be made): wait for it, else share the message alone.
    const file = qrFile.value ?? (preparing ? await preparing : null)
    if (file) {
      const result = await shareWithImage(message.value, file, props.credentials?.admin_link)
      if (result === 'failed') toast.add({ severity: 'warn', summary: t('qr.shareFailed'), life: 5000 })
      return
    }
    try {
      await navigator.share({ text: message.value })
    } catch (err) {
      if ((err as { name?: string })?.name !== 'AbortError') toast.add({ severity: 'warn', summary: t('qr.shareFailed'), life: 5000 })
    }
  } finally {
    sharing.value = false
  }
}

async function copy(what: 'message' | 'link' | 'password') {
  if (!props.credentials) return
  if (what === 'message') {
    // The message and the QR code of the link go to the clipboard together.
    const withImage = await copyMessageWithQr(message.value, props.credentials.admin_link)
    if (withImage) {
      qrCode.value?.flashCopied()
      // Chat apps read only one format from the clipboard (the text): say how to get the image there.
      toast.add({ severity: 'info', summary: t('qr.copiedBoth'), detail: canShare ? t('qr.copiedBothShare') : t('qr.copiedBothClick'), life: 7000 })
    } else {
      toast.add({ severity: 'info', summary: t('qr.textOnly'), life: 5000 })
    }
  } else {
    await navigator.clipboard.writeText(what === 'link' ? props.credentials.admin_link : props.credentials.password)
  }
  copied.value = what
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = null), 2000)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="kind === 'created' ? t('admins.credentials.createdTitle', { name }) : t('admins.credentials.resetTitle', { name })"
    :style="{ width: 'min(42rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div v-if="credentials" class="cred">
      <div class="cred__hero">
        <span class="cred__badge"><i class="pi" :class="kind === 'created' ? 'pi-user-plus' : 'pi-key'" /></span>
        <p class="m-0 text-muted-color">{{ t('admins.credentials.lead') }}</p>
      </div>

      <div class="cred__body">
        <HiddifyQrCode ref="qrCode" :value="credentials.admin_link" :size="160" class="cred__qr" />
        <div class="cred__fields">
          <div class="cred__field">
            <span class="cred__label">{{ t('admins.credentials.link') }}</span>
            <div class="cred__value">
              <code dir="ltr" class="cred__code">{{ credentials.admin_link }}</code>
              <Button
                :icon="copied === 'link' ? 'pi pi-check' : 'pi pi-copy'"
                text
                rounded
                size="small"
                :aria-label="t('common.copy')"
                v-tooltip.top="t('common.copy')"
                @click="copy('link')"
              />
            </div>
          </div>

          <div v-if="credentials.alias" class="cred__field">
            <span class="cred__label">{{ t('admins.credentials.username') }}</span>
            <div class="cred__value">
              <code dir="ltr" class="cred__code">{{ credentials.alias }}</code>
            </div>
          </div>
          <div class="cred__field">
            <span class="cred__label">{{ t('admins.credentials.password') }}</span>
            <div class="cred__value">
              <code dir="ltr" class="cred__code cred__code--password">{{ showPassword ? credentials.password : '•'.repeat(credentials.password.length) }}</code>
              <Button
                :icon="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"
                text
                rounded
                size="small"
                severity="secondary"
                :aria-label="t('admins.credentials.show')"
                @click="showPassword = !showPassword"
              />
              <Button
                :icon="copied === 'password' ? 'pi pi-check' : 'pi pi-copy'"
                text
                rounded
                size="small"
                :aria-label="t('common.copy')"
                v-tooltip.top="t('common.copy')"
                @click="copy('password')"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="cred__message">
        <div class="cred__label">{{ t('admins.credentials.messageLabel') }}</div>
        <p class="cred__message-text" dir="auto">{{ message }}</p>
      </div>

      <Message severity="warn" :closable="false" size="small">{{ t('admins.credentials.once') }}</Message>

      <div class="flex flex-wrap justify-end gap-2">
        <Button :label="t('admins.credentials.done')" severity="secondary" text @click="visible = false" />
        <Button
          :icon="copied === 'message' ? 'pi pi-check' : 'pi pi-copy'"
          :label="copied === 'message' ? t('common.copied') : t('admins.credentials.copyMessage')"
          :severity="canShare ? 'secondary' : undefined"
          :outlined="canShare"
          v-tooltip.top="t('admins.credentials.copyMessageHint')"
          @click="copy('message')"
        />
        <Button
          v-if="canShare"
          icon="pi pi-share-alt"
          :label="t('qr.share')"
          :loading="sharing"
          v-tooltip.top="t('qr.shareHint')"
          @click="share"
        />
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.cred {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.cred__hero {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.cred__badge {
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  color: #fff;
  background: var(--p-green-500, #22c55e);
  animation: cred-pop 0.45s cubic-bezier(0.2, 1.4, 0.4, 1) both;
}
.cred__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}
.cred__qr {
  justify-self: center;
}
.cred__fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}
@media (max-width: 640px) {
  .cred__body {
    grid-template-columns: 1fr;
  }
}
.cred__field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.cred__label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.cred__value {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0.25rem 0.25rem 0.25rem 0.75rem;
  border-radius: 10px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.cred__code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 0.82rem;
  background: none;
  text-align: start;
}
.cred__code--password {
  font-size: 0.95rem;
  letter-spacing: 0.06em;
}
.cred__message {
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 7%, transparent);
}
.cred__message-text {
  margin: 0.35rem 0 0;
  font-size: 0.88rem;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
@keyframes cred-pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cred__badge {
    animation: none;
  }
}
</style>
