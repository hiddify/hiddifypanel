<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :header="t('account.passkeys.suggest.title')" :style="{ width: 'min(27rem, calc(100vw - 1.5rem))' }">
    <div class="ps">
      <span class="ps__icon" aria-hidden="true"><i class="pi pi-shield" /></span>
      <p class="ps__text">{{ t('account.passkeys.suggest.body') }}</p>
      <p v-if="suggestion && suggestion.missing.length > 1" class="ps__domains">
        {{ t('account.passkeys.suggest.domains', { count: suggestion.missing.length }) }}
      </p>
      <small v-if="suggestion && !suggestion.domain && suggestion.missing.length" class="ps__domains">
        {{ t('account.passkeys.onIp', { host: hostname, domain: suggestion.missing[0] }) }}
      </small>
      <small v-if="error" class="ps__error" role="alert">{{ error }}</small>
    </div>
    <template #footer>
      <div class="ps__actions">
        <Button :label="t('account.passkeys.suggest.never')" severity="secondary" text size="small" @click="never" />
        <span class="flex-1" />
        <Button :label="t('account.passkeys.suggest.later')" severity="secondary" outlined @click="visible = false" />
        <Button :label="t('account.passkeys.add')" icon="pi pi-plus" autofocus :loading="adding" @click="add" />
      </div>
    </template>
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
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.75rem;
}
.ps__icon {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 1.5rem;
  color: var(--p-emerald-600, #059669);
  background: color-mix(in srgb, var(--p-emerald-500, #10b981) 14%, transparent);
}
.ps__text {
  margin: 0;
  line-height: 1.55;
}
.ps__domains {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.ps__error {
  color: var(--p-red-500, #ef4444);
}
.ps__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}
</style>
