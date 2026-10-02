<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { apiErrorMessage } from '@/core/api/client'
import DomainChipsInput from '@/features/quick-setup/components/DomainChipsInput.vue'
import DomainModeChipsInput from '@/features/quick-setup/components/DomainModeChipsInput.vue'
import { quickSetupApi, type DomainMode, type DomainsErrorBody, type ModeChip, type QuickSetupState } from '@/features/quick-setup/api'

const props = defineProps<{ state: QuickSetupState }>()
const emit = defineEmits<{ error: [message: string]; saved: [state: QuickSetupState] }>()

const { t } = useI18n()
const toast = useToast()

const entries = ref<ModeChip[]>(props.state.entries.map((e) => ({ ...e, touched: true })))
const sublinks = ref<string[]>([...props.state.sublink_domains])
const blockDomestic = ref(props.state.block_iran_sites)
const decoy = ref(props.state.decoy_domain)
const errors = ref<{ entries: Record<string, string>; sublink: Record<string, string>; decoy: string | null; required: boolean }>({
  entries: {},
  sublink: {},
  decoy: null,
  required: false,
})
const detecting = computed(() => entries.value.some((e) => e.detecting))
const MODE_HELP: { mode: DomainMode; icon: string }[] = [
  { mode: 'direct', icon: 'pi pi-bolt' },
  { mode: 'cdn', icon: 'pi pi-cloud' },
  { mode: 'reality', icon: 'pi pi-eye-slash' },
  { mode: 'relay', icon: 'pi pi-share-alt' },
]

function useIp(ip: string) {
  if (!entries.value.some((e) => e.domain === ip)) entries.value = [...entries.value, { domain: ip, mode: 'direct', touched: true }]
}

const ips = computed(() =>
  [
    { label: 'IPv4', value: props.state.ipv4, record: 'A' },
    { label: 'IPv6', value: props.state.ipv6, record: 'AAAA' },
  ].filter((ip) => ip.value),
)

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const area = document.createElement('textarea')
    area.value = text
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  toast.add({ severity: 'success', summary: t('quickSetup.domains.copied', { ip: text }), life: 2000 })
}

async function submit(): Promise<boolean> {
  errors.value = { entries: {}, sublink: {}, decoy: null, required: false }
  // Let pending detections settle so the saved modes are the detected ones.
  for (let waited = 0; detecting.value && waited < 20_000; waited += 200) await new Promise((resolve) => setTimeout(resolve, 200))
  if (!sublinks.value.length && !entries.value.some((e) => e.mode === 'direct' || e.mode === 'cdn')) {
    errors.value.required = true
    return false
  }
  try {
    const state = await quickSetupApi.domains({
      entries: entries.value.map(({ domain, mode }) => ({ domain, mode })),
      sublink_domains: sublinks.value,
      block_iran_sites: blockDomestic.value,
      decoy_domain: decoy.value.trim(),
    })
    for (const warning of state.warnings ?? []) toast.add({ severity: 'warn', summary: warning, life: 8000 })
    emit('saved', state)
    return true
  } catch (err) {
    const body = (err as { response?: { data?: DomainsErrorBody } })?.response?.data
    const fe = body?.field_errors
    if (fe) {
      errors.value = { entries: fe.entries ?? {}, sublink: fe.sublink_domains ?? {}, decoy: fe.decoy_domain ?? null, required: Boolean(fe.required) }
      return false
    }
    emit('error', apiErrorMessage(err))
    return false
  }
}

defineExpose({ submit })
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Server IPs -->
    <section class="qs-ips">
      <div class="qs-ips__intro">
        <i class="pi pi-server" />
        <div>
          <div class="font-semibold">{{ t('quickSetup.domains.ipsTitle') }}</div>
          <ol class="qs-steps-list">
            <li>{{ t('quickSetup.domains.how1') }}</li>
            <li>{{ t('quickSetup.domains.how2') }}</li>
          </ol>
        </div>
      </div>
      <div class="qs-ips__list">
        <div v-for="ip in ips" :key="ip.label" class="qs-ip">
          <span class="qs-ip__type">{{ ip.label }} <small>({{ ip.record }})</small></span>
          <code class="qs-ip__value" dir="ltr">{{ ip.value }}</code>
          <Button icon="pi pi-copy" size="small" text rounded :aria-label="t('common.copy')" v-tooltip.top="t('common.copy')" @click="copy(ip.value)" />
          <Button
            icon="pi pi-plus"
            size="small"
            text
            rounded
            :disabled="entries.some((e) => e.domain === ip.value)"
            :aria-label="t('quickSetup.domains.useIp')"
            v-tooltip.top="t('quickSetup.domains.useIp')"
            @click="useIp(ip.value)"
          />
        </div>
        <div v-if="!ips.length" class="text-muted-color">{{ t('quickSetup.domains.noIp') }}</div>
      </div>
    </section>

    <!-- Domains: any kind, detected automatically -->
    <section class="flex flex-col gap-2">
      <label for="qs-domains" class="qs-label"><i class="pi pi-link" /> {{ t('quickSetup.domains.domains') }} <span class="qs-required">*</span></label>
      <DomainModeChipsInput v-model="entries" input-id="qs-domains" placeholder="sub.domain.com, cdn.domain.com, www.example.com" :errors="errors.entries" :invalid="errors.required" />
      <small v-if="errors.required" class="qs-error">{{ t('quickSetup.domains.required') }}</small>
      <small class="qs-hint">{{ t('quickSetup.domains.domainsHint') }}</small>
      <div class="qs-modes">
        <div v-for="item in MODE_HELP" :key="item.mode" class="qs-mode" :class="`qs-mode--${item.mode}`">
          <span class="qs-mode__badge"><i :class="item.icon" /> {{ t(`quickSetup.domains.modes.${item.mode}`) }}</span>
          <span class="qs-mode__text">{{ t(`quickSetup.domains.modeHelp.${item.mode}`) }}</span>
        </div>
      </div>
    </section>

    <!-- Subscription-link domain -->
    <section class="qs-sublink">
      <div class="qs-sublink__head">
        <span class="qs-sublink__icon"><i class="pi pi-shield" /></span>
        <div class="flex-1 min-w-0">
          <label for="qs-sublink" class="qs-label">
            {{ t('quickSetup.domains.sublink') }}
            <span class="qs-badge-recommended"><i class="pi pi-star-fill" /> {{ t('quickSetup.domains.recommended') }}</span>
          </label>
          <p class="qs-hint m-0 mt-1">{{ t('quickSetup.domains.sublinkWhy') }}</p>
        </div>
      </div>
      <DomainChipsInput v-model="sublinks" input-id="qs-sublink" placeholder="sub.another-domain.com" :errors="errors.sublink" />
      <small class="qs-hint">{{ t('quickSetup.domains.sublinkHint') }}</small>
    </section>

    <!-- Block domestic -->
    <label class="qs-switch-row" for="qs-block">
      <span class="qs-switch-row__icon"><i class="pi pi-ban" /></span>
      <span class="flex-1 min-w-0">
        <span class="font-semibold block">{{ t('quickSetup.domains.block') }}</span>
        <span class="qs-hint">{{ t('quickSetup.domains.blockHint') }}</span>
      </span>
      <ToggleSwitch v-model="blockDomestic" input-id="qs-block" />
    </label>

    <!-- Decoy -->
    <section class="flex flex-col gap-2">
      <label for="qs-decoy" class="qs-label"><i class="pi pi-desktop" /> {{ t('quickSetup.domains.decoy') }}</label>
      <InputText id="qs-decoy" v-model="decoy" dir="ltr" placeholder="fa.wikipedia.org" :invalid="Boolean(errors.decoy)" autocomplete="off" spellcheck="false" />
      <small v-if="errors.decoy" class="qs-error">{{ errors.decoy }}</small>
      <small class="qs-hint">{{ t('quickSetup.domains.decoyHint') }}</small>
      <div class="qs-warning">
        <i class="pi pi-exclamation-triangle" />
        <ul>
          <li>{{ t('quickSetup.domains.decoyWarn1') }}</li>
          <li>{{ t('quickSetup.domains.decoyWarn2') }}</li>
          <li>{{ t('quickSetup.domains.decoyWarn3') }}</li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.qs-modes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.35rem;
}
.qs-mode {
  --tone: var(--p-green-500, #22c55e);
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--tone) 25%, transparent);
  background: color-mix(in srgb, var(--tone) 6%, transparent);
}
.qs-mode--cdn {
  --tone: var(--p-sky-500, #0ea5e9);
}
.qs-mode--reality {
  --tone: var(--p-violet-500, #8b5cf6);
}
.qs-mode--relay {
  --tone: var(--p-orange-500, #f97316);
}
.qs-mode__badge {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #fff;
  background: var(--tone);
}
.qs-mode__badge i {
  font-size: 0.7rem;
}
.qs-mode__text {
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
}
.qs-sublink {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1rem;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 30%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--p-primary-color) 9%, transparent), transparent 70%);
}
.qs-sublink__head {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}
.qs-sublink__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 10px;
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
}
.qs-badge-recommended {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-inline-start: 0.4rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--p-amber-700, #b45309);
  background: color-mix(in srgb, var(--p-amber-400, #fbbf24) 25%, transparent);
}
.qs-badge-recommended i {
  font-size: 0.6rem;
}
</style>
