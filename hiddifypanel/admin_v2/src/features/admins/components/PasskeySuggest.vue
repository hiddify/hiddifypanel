<template>
  <Dialog
    v-model:visible="visible"
    modal
    :show-header="false"
    :dismissable-mask="true"
    :draggable="false"
    :style="{ width: 'min(25.5rem, calc(100vw - 1.5rem))' }"
    :pt="{ root: { class: 'ps-dialog' }, content: { class: 'ps-dialog__content' } }"
  >
    <div class="ps">
      <button type="button" class="ps__close" :aria-label="t('account.passkeys.suggest.later')" @click="visible = false">
        <i class="pi pi-times" />
      </button>
      <PasskeyHowAnimation />
      <div class="ps__head">
        <h2 class="ps__title">{{ t('account.passkeys.suggest.title') }}</h2>
        <p class="ps__text">{{ t('account.passkeys.suggest.body') }}</p>
        <p v-if="suggestion && suggestion.missing.length > 1" class="ps__domains">
          {{ t('account.passkeys.suggest.domains', { count: suggestion.missing.length }) }}
        </p>
        <small v-if="suggestion && !suggestion.domain && suggestion.missing.length" class="ps__domains">
          {{ t('account.passkeys.onIp', { host: hostname, domain: suggestion.missing[0] }) }}
        </small>
        <small v-if="error" class="ps__error" role="alert">{{ error }}</small>
      </div>
      <div class="ps__actions">
        <Button :label="t('account.passkeys.add')" icon="pi pi-key" autofocus rounded :loading="adding" class="ps__add" @click="add" />
        <Button :label="t('account.passkeys.suggest.later')" severity="secondary" text rounded class="ps__later" @click="visible = false" />
        <button type="button" class="ps__never" @click="never">{{ t('account.passkeys.suggest.never') }}</button>
      </div>
    </div>
  </Dialog>
  <PasskeyDomainsDialog v-model:visible="domainsOpen" :steps="steps" @done="domainsDone" />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { passkeySuggestion } from '@/core/panelShell'
import { addPasskeyHere, passkeyErrorKey, passkeysVersion } from '@/features/admins/passkey-add'
import PasskeyDomainsDialog from '@/features/admins/components/PasskeyDomainsDialog.vue'
import PasskeyHowAnimation from '@/features/admins/components/PasskeyHowAnimation.vue'
import type { PasskeyStep } from '@/features/admins/api'
import { passkeysSupported } from '@/shared/utils/webauthn'

/** Offered once after a password sign-in when the admin has no passkey yet (the panel decides; see passkeys_api). */
const NEVER_KEY = 'admin_v2_passkey_never'

const { t } = useI18n()
const route = useRoute()
const toast = useToast()
const visible = ref(false)
const hostname = window.location.hostname
const adding = ref(false)
const error = ref<string | null>(null)
// Kept after it is taken from the shell (shown once), for the dialog's text and the add.
const suggestion = ref(passkeySuggestion.value)

function declinedHere(): boolean {
  try {
    return localStorage.getItem(NEVER_KEY) === '1'
  } catch {
    return false
  }
}

let shown = false

function maybeShow() {
  // Once, not over the first setup, and not in a browser that can not make passkeys.
  if (shown || !suggestion.value || route.name === 'quick-setup' || !route.name) return
  shown = true
  passkeySuggestion.value = null
  if (passkeysSupported() && !declinedHere()) visible.value = true
}

watch(() => route.name, maybeShow, { immediate: true })
// The dev server's shell data arrives after the page.
watch(passkeySuggestion, (value) => {
  if (value && !shown) {
    suggestion.value = value
    maybeShow()
  }
})

function never() {
  try {
    localStorage.setItem(NEVER_KEY, '1')
  } catch {
    // private window: it is simply offered again after the next password sign-in
  }
  visible.value = false
}

const steps = ref<PasskeyStep[]>([])
const domainsOpen = ref(false)

/** Straight to the device's prompt here, then the other domains in frames (this page stays). */
async function add() {
  if (adding.value || !suggestion.value) return
  const { domain, missing } = suggestion.value
  adding.value = true
  error.value = null
  try {
    const result = await addPasskeyHere(domain, missing)
    steps.value = result.steps
    visible.value = false
    if (result.added) toast.add({ severity: 'success', summary: t('account.passkeys.addedToast'), life: 3000 })
    if (steps.value.length) domainsOpen.value = true
  } catch (e) {
    const key = passkeyErrorKey(e)
    error.value = key ? t(key) : apiErrorMessage(e)
  } finally {
    adding.value = false
  }
}

function domainsDone(added: number) {
  if (added) toast.add({ severity: 'success', summary: t('account.passkeys.tourDone', { n: added }, added), life: 4000 })
  passkeysVersion.value++
}
</script>

<style scoped>
.ps {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 0.75rem 0.75rem 1rem;
}
.ps__close {
  position: absolute;
  top: 1.25rem;
  inset-inline-end: 1.25rem;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border: 0;
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-content-background) 65%, transparent);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--p-text-color) 8%, transparent);
  cursor: pointer;
  transition: color 0.2s, transform 0.2s;
}
.ps__close:hover,
.ps__close:focus-visible {
  color: var(--p-text-color);
  transform: scale(1.06);
  outline: none;
}
.ps__head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.6rem;
  text-align: center;
}
.ps__title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.ps__text {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.5;
  color: color-mix(in srgb, var(--p-text-color) 78%, transparent);
}
.ps__domains {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}
.ps__error {
  color: var(--p-red-500, #ef4444);
}
.ps__actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.35rem;
  padding: 0 0.35rem;
}
.ps__add {
  min-height: 3.1rem;
  font-size: 1.02rem;
  font-weight: 600;
  box-shadow: 0 10px 22px -12px var(--p-primary-color);
}
.ps__later {
  min-height: 2.75rem;
  font-weight: 600;
}
.ps__never {
  align-self: center;
  padding: 0.3rem 0.6rem;
  border: 0;
  border-radius: 8px;
  background: none;
  font: inherit;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.ps__never:hover,
.ps__never:focus-visible {
  color: var(--p-text-color);
  text-decoration: underline;
  outline: none;
}
</style>

<style>
/* The dialog itself (not scoped: PrimeVue renders it outside this component): a rounded, frosted card */
.ps-dialog {
  max-height: calc(100dvh - 2rem);
  border-radius: 32px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--p-text-color) 8%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 86%, transparent);
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  box-shadow:
    0 30px 60px -20px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.ps-dialog .ps-dialog__content {
  padding: 0;
  overflow-y: auto;
  background: transparent;
  border-radius: inherit;
}
</style>
