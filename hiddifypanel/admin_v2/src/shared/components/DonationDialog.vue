<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { shellDialog } from '@/core/panelShell'

interface Wallet {
  name: string
  address: string
}

const WALLETS_MARK = '<!--wallets-->'

const { t } = useI18n()
const toast = useToast()
const copied = ref<string | null>(null)
const openQr = ref<string | null>(null)
/** address -> SVG markup, generated on first open. */
const qrSvgs = reactive<Record<string, string>>({})

async function toggleQr(wallet: Wallet) {
  if (openQr.value === wallet.address) {
    openQr.value = null
    return
  }
  if (!qrSvgs[wallet.address]) {
    // Always dark-on-light: scanners read that most reliably, whatever the theme.
    qrSvgs[wallet.address] = await QRCode.toString(wallet.address, {
      type: 'svg',
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#111827', light: '#ffffff' },
    })
  }
  openQr.value = wallet.address
}

const visible = computed({
  get: () => shellDialog.value?.action === 'donation',
  set: (open: boolean) => {
    if (!open) {
      shellDialog.value = null
      openQr.value = null
    }
  },
})

/**
 * The translated text is the classic modal's HTML: wallet addresses are Bootstrap
 * button groups with `data-copy`. Pull them out into proper rows; keep the rest as text.
 */
const content = computed(() => {
  const html = shellDialog.value?.action === 'donation' ? shellDialog.value.html : ''
  const doc = new DOMParser().parseFromString(`<div id="root">${html}</div>`, 'text/html')
  const root = doc.getElementById('root')!
  const wallets: Wallet[] = []
  let list: Element | null = null
  for (const item of Array.from(root.querySelectorAll('li'))) {
    const addressLink = item.querySelector('a[data-copy]:not(.copy-link)') ?? item.querySelector('a[data-copy]')
    const address = addressLink?.getAttribute('data-copy')?.trim()
    if (!address) continue
    wallets.push({ name: addressLink?.textContent?.trim() || address.slice(0, 8), address })
    list ??= item.parentElement
    item.remove()
  }
  if (list) list.replaceWith(doc.createComment('wallets'))
  const [before = '', after = ''] = root.innerHTML.split(WALLETS_MARK)
  return { before, after, wallets }
})

async function copy(wallet: Wallet) {
  try {
    await navigator.clipboard.writeText(wallet.address)
  } catch {
    // Clipboard API blocked (http, old browser): fall back to a hidden textarea.
    const area = document.createElement('textarea')
    area.value = wallet.address
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  copied.value = wallet.address
  toast.add({ severity: 'success', summary: t('donation.copied', { name: wallet.name }), life: 2500 })
  window.setTimeout(() => {
    if (copied.value === wallet.address) copied.value = null
  }, 2000)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    dismissable-mask
    :header="shellDialog?.title || t('donation.title')"
    :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div class="donation">
      <div class="donation__hero" aria-hidden="true"><i class="pi pi-heart-fill" /></div>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
      <div class="donation__text" v-html="content.before" />

      <ul v-if="content.wallets.length" class="donation__wallets">
        <li v-for="wallet in content.wallets" :key="wallet.address" class="donation__wallet" :class="{ 'donation__wallet--open': openQr === wallet.address }">
          <div class="donation__wallet-row">
            <div class="min-w-0 flex-1">
              <div class="donation__wallet-name">{{ wallet.name }}</div>
              <code class="donation__wallet-address" dir="ltr" :title="wallet.address">{{ wallet.address }}</code>
            </div>
            <Button
              icon="pi pi-qrcode"
              size="small"
              :severity="openQr === wallet.address ? undefined : 'secondary'"
              :outlined="openQr !== wallet.address"
              :aria-label="t('donation.showQr', { name: wallet.name })"
              :aria-expanded="openQr === wallet.address"
              v-tooltip.top="t('donation.qr')"
              @click="toggleQr(wallet)"
            />
            <Button
              :icon="copied === wallet.address ? 'pi pi-check' : 'pi pi-copy'"
              :label="copied === wallet.address ? t('donation.copiedShort') : t('common.copy')"
              :severity="copied === wallet.address ? 'success' : 'secondary'"
              size="small"
              outlined
              @click="copy(wallet)"
            />
          </div>
          <div class="donation__qr-wrap">
            <div class="donation__qr-inner">
              <!-- eslint-disable-next-line vue/no-v-html -- SVG generated locally from the address -->
              <div v-if="qrSvgs[wallet.address]" class="donation__qr" :aria-label="t('donation.qrOf', { name: wallet.name })" role="img" v-html="qrSvgs[wallet.address]" />
              <code class="donation__qr-address" dir="ltr">{{ wallet.address }}</code>
            </div>
          </div>
        </li>
      </ul>

      <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
      <div class="donation__text" v-html="content.after" />
    </div>
    <template #footer>
      <Button :label="t('donation.close')" severity="secondary" text @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.donation {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  line-height: 1.6;
}
.donation__hero {
  align-self: center;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 1.5rem;
  color: #ec4899;
  background: color-mix(in srgb, #ec4899 14%, transparent);
  animation: donation-beat 1.6s ease-in-out infinite;
}
.donation__text :deep(h5),
.donation__text :deep(h6) {
  margin: 0.75rem 0 0.25rem;
  font-size: 1rem;
  font-weight: 600;
}
.donation__text :deep(ul) {
  margin: 0.25rem 0;
  padding-inline-start: 1.25rem;
}
.donation__text :deep(a) {
  color: var(--p-primary-color);
}
.donation__wallets {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.donation__wallet {
  padding: 0.6rem 0.75rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.05));
  transition: border-color 0.2s ease;
}
.donation__wallet--open {
  border-color: var(--p-primary-color);
}
.donation__wallet-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
/* Height animation without measuring: grid rows 0fr -> 1fr. */
.donation__qr-wrap {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s ease;
}
.donation__wallet--open .donation__qr-wrap {
  grid-template-rows: 1fr;
}
.donation__qr-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  min-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.donation__wallet--open .donation__qr-inner {
  opacity: 1;
  padding-top: 0.75rem;
}
.donation__qr {
  width: min(12rem, 60vw);
  aspect-ratio: 1;
  padding: 0.4rem;
  border-radius: 12px;
  background: #fff;
}
.donation__qr :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
.donation__qr-address {
  max-width: 100%;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
  text-align: center;
  user-select: all;
}
.donation__wallet-name {
  font-weight: 600;
}
.donation__wallet-address {
  display: block;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
@keyframes donation-beat {
  0%,
  100% {
    transform: scale(1);
  }
  15% {
    transform: scale(1.12);
  }
  30% {
    transform: scale(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .donation__hero {
    animation: none;
  }
  .donation__qr-wrap,
  .donation__qr-inner {
    transition: none;
  }
}
</style>
