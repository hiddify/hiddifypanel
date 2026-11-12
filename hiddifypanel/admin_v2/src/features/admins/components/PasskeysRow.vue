<template>
  <div class="pk">
    <div class="pk__line">
      <span class="pk__icon"><i class="pi pi-shield" /></span>
      <div class="pk__text">
        <b>{{ t('account.passkeys.title') }}</b>
        <small>{{ hint }}</small>
      </div>
      <Button
        :label="t('account.passkeys.add')"
        icon="pi pi-plus"
        size="small"
        outlined
        :disabled="!canAdd"
        :loading="(loading && !info) || adding"
        @click="add"
      />
    </div>

    <Message v-if="loadError" severity="error" size="small" :closable="false">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="flex-1 min-w-0">{{ loadError }}</span>
        <Button :label="t('account.passkeys.retry')" icon="pi pi-refresh" size="small" text @click="load" />
      </div>
    </Message>
    <Message v-else-if="!supported" severity="secondary" size="small" :closable="false">{{ t('account.passkeys.unsupported') }}</Message>
    <!-- On the IP: no passkey can be made or used on this page (WebAuthn needs a domain name) -->
    <Message v-else-if="onIp" severity="info" size="small" :closable="false" icon="pi pi-info-circle">{{ onIp }}</Message>

    <ul v-if="info?.passkeys.length" class="pk__list">
      <li v-for="p in info.passkeys" :key="p.id" class="pk__item">
        <i class="pi pi-key pk__item-icon" />
        <div class="pk__text">
          <span class="pk__name">{{ p.name }}</span>
          <small>
            <span class="pk__domain" :class="{ 'pk__domain--here': p.domain === info.domain }" dir="ltr">{{ p.domain }}</span>
            · {{ usedText(p) }}
          </small>
        </div>
        <Button icon="pi pi-trash" severity="danger" text rounded size="small" :aria-label="t('account.passkeys.remove')" :loading="removing === p.id" @click="askRemove(p)" />
      </li>
    </ul>

    <PasskeyDomainsDialog v-model:visible="domainsOpen" :steps="steps" @done="domainsDone" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { apiErrorMessage } from '@/core/api/client'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { longDate } from '@/shared/utils/dates'
import { passkeysSupported } from '@/shared/utils/webauthn'
import { adminsApi, type MyPasskeys, type Passkey } from '@/features/admins/api'
import { addPasskeyHere, passkeyErrorKey, passkeysVersion } from '@/features/admins/passkey-add'
import PasskeyDomainsDialog from '@/features/admins/components/PasskeyDomainsDialog.vue'
import type { PasskeyStep } from '@/features/admins/api'

const { t, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const supported = passkeysSupported()
const info = ref<MyPasskeys | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const adding = ref(false)
const removing = ref<number | null>(null)

/** On a domain (not an IP): this device adds its passkey here (another device can too), then the other domains. */
const canAdd = computed(() => supported && (!!info.value?.domain || !!info.value?.missing.length))

const hint = computed(() => {
  if (!info.value) return t('account.passkeys.hint')
  if (!info.value.missing.length) return info.value.passkeys.length ? t('account.passkeys.allDone') : t('account.passkeys.needsDomain')
  return t('account.passkeys.hintMissing', { domains: info.value.missing.join(', ') })
})

/** Why this page itself gets no passkey: it is open on an IP address. */
const onIp = computed(() => {
  const domain = info.value && !info.value.domain ? (info.value.passkeys[0]?.domain ?? info.value.missing[0]) : null
  return domain ? t('account.passkeys.onIp', { host: window.location.hostname, domain }) : ''
})

function usedText(p: Passkey): string {
  const added = t('account.passkeys.added', { date: longDate(p.created_at, locale.value) })
  return p.last_used_at ? `${added} · ${t('account.passkeys.lastUsed', { date: longDate(p.last_used_at, locale.value) })}` : added
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    info.value = await adminsApi.myPasskeys()
  } catch (e) {
    loadError.value = apiErrorMessage(e)
  } finally {
    loading.value = false
  }
}

const steps = ref<PasskeyStep[]>([])
const domainsOpen = ref(false)

/** Straight to the device's passkey prompt here, then the other domains in frames, without leaving this page. */
async function add() {
  if (!info.value || adding.value) return
  adding.value = true
  try {
    const result = await addPasskeyHere(info.value.domain, info.value.missing)
    steps.value = result.steps
    if (result.added) toast.add({ severity: 'success', summary: t('account.passkeys.addedToast'), life: 3000 })
    if (steps.value.length) domainsOpen.value = true
  } catch (e) {
    const key = passkeyErrorKey(e)
    toast.add({ severity: key === 'account.passkeys.cancelled' ? 'info' : 'error', summary: key ? t(key) : apiErrorMessage(e), life: 5000 })
    await load()
  } finally {
    adding.value = false
  }
}

function domainsDone(added: number) {
  if (added) toast.add({ severity: 'success', summary: t('account.passkeys.tourDone', { n: added }, added), life: 4000 })
  void load()
}

function askRemove(p: Passkey) {
  dangerConfirm({
    header: t('account.passkeys.removeTitle'),
    message: t('account.passkeys.removeMessage', { name: p.name }),
    acceptLabel: t('account.passkeys.remove'),
    accept: async () => {
      removing.value = p.id
      try {
        await adminsApi.removePasskey(p.id)
        await load()
      } catch (e) {
        toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
      } finally {
        removing.value = null
      }
    },
  })
}

watch(passkeysVersion, load)

onMounted(load)
</script>

<style scoped>
.pk {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.pk__line {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.pk__icon {
  flex-shrink: 0;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--p-emerald-600, #059669);
  background: color-mix(in srgb, var(--p-emerald-500, #10b981) 14%, transparent);
}
.pk__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.pk__text b {
  font-size: 0.9rem;
}
.pk__text small {
  font-size: 0.78rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.pk__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.pk__item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.45rem 0.4rem 0.45rem 0.7rem;
  padding-inline: 0.7rem 0.4rem;
  border-radius: 10px;
  background: var(--p-content-hover-background);
}
.pk__item-icon {
  color: var(--p-text-muted-color);
}
.pk__name {
  font-size: 0.86rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pk__domain {
  font-family: var(--p-font-family-mono, ui-monospace, monospace);
}
.pk__domain--here {
  color: var(--p-primary-color);
  font-weight: 600;
}
</style>
