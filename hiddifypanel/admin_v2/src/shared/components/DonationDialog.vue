<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import CoinIcon from '@/shared/components/CoinIcon.vue'
import { shellDialog, type DonationWallet } from '@/core/panelShell'

const WALLETS_MARK = '<!--wallets-->'

const { t } = useI18n()
const toast = useToast()
const copied = ref<string | null>(null)
const openQr = ref<string | null>(null)
/** address -> SVG markup, generated on first open. */
const qrSvgs = reactive<Record<string, string>>({})

async function toggleQr(wallet: DonationWallet) {
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

const wallets = computed(() => (shellDialog.value?.action === 'donation' ? shellDialog.value.wallets : []))

/** The translated text marks where the wallets go (`.donation-wallets`); without the mark they follow the text. */
const content = computed(() => {
  const html = shellDialog.value?.action === 'donation' ? shellDialog.value.html : ''
  const doc = new DOMParser().parseFromString(`<div id="root">${html}</div>`, 'text/html')
  const root = doc.getElementById('root')!
  // A catalog compiled before the wallets moved to hutils/donation.py still holds the old list (`data-copy`
  // buttons): drop it, so no old address is shown, and put the wallets where it was.
  const mark = root.querySelector('.donation-wallets')
  const oldList = root.querySelector('a[data-copy]')?.closest('ul')
  if (mark) {
    oldList?.remove()
    mark.replaceWith(doc.createComment('wallets'))
  } else {
    oldList?.replaceWith(doc.createComment('wallets'))
  }
  const [before = '', after = ''] = root.innerHTML.split(WALLETS_MARK)
  return { before, after }
})

async function copy(wallet: DonationWallet) {
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
  toast.add({ severity: 'success', summary: t('donation.copied', { name: `${wallet.name} (${wallet.network})` }), life: 2500 })
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
    :style="{ width: 'min(38rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <div class="donation">
      <div class="donation__hero" aria-hidden="true"><i class="pi pi-heart-fill" /></div>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
      <div class="donation__text" v-html="content.before" />

      <template v-if="wallets.length">
        <ul class="donation__wallets">
          <li v-for="wallet in wallets" :key="wallet.address" class="donation__wallet" :class="{ 'donation__wallet--open': openQr === wallet.address }">
            <div class="donation__wallet-row">
              <CoinIcon :coin="wallet.id" />
              <div class="donation__wallet-body">
                <div class="donation__wallet-head">
                  <span class="donation__wallet-name">{{ wallet.name }}</span>
                  <span class="donation__network" dir="ltr">{{ wallet.network }}</span>
                </div>
                <!-- The whole address, never cut: people compare it before they send. A click copies it too. -->
                <button type="button" class="donation__address" dir="ltr" :title="t('donation.copyAddress', { name: wallet.name })" @click="copy(wallet)">
                  {{ wallet.address }}
                </button>
              </div>
              <div class="donation__actions">
                <Button
                  :icon="copied === wallet.address ? 'pi pi-check' : 'pi pi-copy'"
                  :label="copied === wallet.address ? t('donation.copiedShort') : t('common.copy')"
                  :severity="copied === wallet.address ? 'success' : undefined"
                  size="small"
                  class="donation__copy"
                  :aria-label="t('donation.copyAddress', { name: wallet.name })"
                  @click="copy(wallet)"
                />
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
              </div>
            </div>
            <div class="donation__qr-wrap">
              <div class="donation__qr-inner">
                <!-- eslint-disable-next-line vue/no-v-html -- SVG generated locally from the address -->
                <div v-if="qrSvgs[wallet.address]" class="donation__qr" :aria-label="t('donation.qrOf', { name: wallet.name })" role="img" v-html="qrSvgs[wallet.address]" />
              </div>
            </div>
          </li>
        </ul>
        <p class="donation__hint"><i class="pi pi-info-circle" />{{ t('donation.networkHint') }}</p>
      </template>

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
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.donation__wallet {
  padding: 0.75rem 0.85rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}
.donation__wallet:hover,
.donation__wallet--open {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, var(--p-content-border-color));
  box-shadow: 0 6px 18px -12px color-mix(in srgb, var(--p-primary-color) 60%, transparent);
}
.donation__wallet-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.donation__wallet-body {
  flex: 1;
  min-width: 0;
}
.donation__wallet-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.15rem;
}
.donation__wallet-name {
  font-weight: 600;
}
.donation__network {
  /* Like the address: Latin digits (the Persian UI font draws "BEP20" as "BEP۲۰"). */
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  padding: 0 0.45rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.donation__address {
  display: block;
  width: 100%;
  margin: 0;
  padding: 0.15rem 0;
  border: 0;
  background: none;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
  text-align: start;
  overflow-wrap: anywhere;
  cursor: copy;
  transition: color 0.15s ease;
}
.donation__address:hover,
.donation__address:focus-visible {
  color: var(--p-text-color);
}
.donation__actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.4rem;
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
  justify-content: center;
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
.donation__hint {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.donation__hint i {
  margin-top: 0.25rem;
  font-size: 0.8rem;
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
/* Narrow screens: the buttons go icon-only so the address keeps its width. */
@media (max-width: 480px) {
  .donation__wallet {
    padding: 0.65rem 0.7rem;
  }
  .donation__wallet-row {
    gap: 0.6rem;
  }
  .donation__copy :deep(.p-button-label) {
    display: none;
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
