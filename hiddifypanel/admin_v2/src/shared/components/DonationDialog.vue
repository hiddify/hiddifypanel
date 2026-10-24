<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import CoinIcon from '@/shared/components/CoinIcon.vue'
import { shellDialog, type DonationWallet } from '@/core/panelShell'

const CONTACT_EMAIL = 'info@hiddify.com'
/** Other ways to help, each with an icon of its own (the old text had emoji). */
const OTHER_HELP = [
  { key: 'share', icon: 'pi pi-share-alt' },
  { key: 'python', icon: 'pi pi-code' },
  { key: 'swift', icon: 'pi pi-apple' },
  { key: 'flutter', icon: 'pi pi-mobile' },
  { key: 'go', icon: 'pi pi-server' },
  { key: 'content', icon: 'pi pi-video' },
] as const

const { t } = useI18n()
const toast = useToast()
const copied = ref<string | null>(null)
const openQr = ref<string | null>(null)
/** "We need also other help" starts closed: the wallets come first. */
const showOtherHelp = ref(false)
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
      showOtherHelp.value = false
    }
  },
})

const wallets = computed(() => (shellDialog.value?.action === 'donation' ? shellDialog.value.wallets : []))

/** "Please contact us at {email} …" around the address, which is a mail link. */
const contact = computed(() => {
  const [before = '', after = ''] = t('donation.contact', { email: '\u0000' }).split('\u0000')
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
      <template v-if="wallets.length">
        <h3 class="donation__heading">{{ t('donation.paymentMethods') }}</h3>
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

      <section class="donation__more" :class="{ 'donation__more--open': showOtherHelp }">
        <button type="button" class="donation__more-toggle" :aria-expanded="showOtherHelp" aria-controls="donation-other-help" @click="showOtherHelp = !showOtherHelp">
          <span class="donation__more-title"><i class="pi pi-users" aria-hidden="true" />{{ t('donation.otherHelp') }}</span>
          <span class="donation__more-action">
            {{ showOtherHelp ? t('donation.showLess') : t('donation.showMore') }}
            <i class="pi pi-chevron-down" aria-hidden="true" />
          </span>
        </button>
        <div id="donation-other-help" class="donation__more-wrap">
          <div class="donation__more-inner">
            <ul class="donation__help">
              <li v-for="item in OTHER_HELP" :key="item.key">
                <span class="donation__help-icon" aria-hidden="true"><i :class="item.icon" /></span>{{ t(`donation.help.${item.key}`) }}
              </li>
            </ul>
            <p class="donation__contact">
              {{ contact.before }}<a :href="`mailto:${CONTACT_EMAIL}`" dir="ltr">{{ CONTACT_EMAIL }}</a>{{ contact.after }}
            </p>
          </div>
        </div>
      </section>
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
.donation__heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
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
/* "We need also other help": a header that opens the list, like the QR codes (grid rows 0fr -> 1fr). */
.donation__more {
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
}
.donation__more-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  padding: 0.7rem 0.85rem;
  border: 0;
  border-radius: 14px;
  background: none;
  font: inherit;
  color: inherit;
  text-align: start;
  cursor: pointer;
}
.donation__more-toggle:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
}
.donation__more-title {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-weight: 600;
}
.donation__more-title i {
  color: #ec4899;
}
.donation__more-action {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--p-primary-color);
}
.donation__more-action i {
  font-size: 0.75rem;
  transition: transform 0.3s ease;
}
.donation__more--open .donation__more-action i {
  transform: rotate(180deg);
}
.donation__more-wrap {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s ease;
}
.donation__more--open .donation__more-wrap {
  grid-template-rows: 1fr;
}
.donation__more-inner {
  min-height: 0;
  overflow: hidden;
  padding: 0 0.85rem;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.donation__more--open .donation__more-inner {
  opacity: 1;
  padding-bottom: 0.8rem;
}
.donation__help {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.45rem 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.donation__help li {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.donation__help-icon {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 9px;
  font-size: 0.85rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.donation__contact {
  margin: 0.75rem 0 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}
.donation__contact a {
  color: var(--p-primary-color);
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
  .donation__qr-inner,
  .donation__more-wrap,
  .donation__more-inner,
  .donation__more-action i {
    transition: none;
  }
}
</style>
