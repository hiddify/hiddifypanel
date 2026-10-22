<script setup lang="ts">
/** The internet this browser is on (the operator the scan tests), as the panel sees it. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import type { CleanIpNetwork } from '../api'
import { operatorLabel } from './operatorLabel'

const props = defineProps<{ net: CleanIpNetwork | null; error: string }>()
defineEmits<{ refresh: [] }>()
const { t } = useI18n()

const known = computed(() => !!props.net && props.net.short_name !== 'unknown')
// The name alone: the AS number has its own chip (shown always, detected operator or not)
const operatorName = computed(() => (props.net ? operatorLabel(t, props.net.short_name) : ''))
const asKnown = computed(() => !!props.net && /^\d+$/.test(props.net.asn))
// Another country than the panel's: a VPN is on, so the scan would test the VPN, not the users' operator
const vpnOn = computed(() => !!props.net?.panel_country && props.net.country !== 'unknown' && props.net.country !== props.net.panel_country)
</script>

<template>
  <section class="net card">
    <div class="net__main">
      <span class="net__icon" :class="{ 'net__icon--warn': vpnOn }"><i class="pi" :class="vpnOn ? 'pi-exclamation-triangle' : 'pi-wifi'" /></span>
      <div class="net__body">
        <div class="net__label">{{ t('cleanIp.yourNetwork') }}</div>
        <template v-if="net">
          <div class="net__name">
            {{ operatorName }}
            <span v-if="known" class="net__code">{{ net.short_name }}</span>
            <span class="net__code net__code--as" dir="ltr" v-tooltip.bottom="asKnown ? net.org : t('cleanIp.asUnknown')">AS{{ asKnown ? net.asn : ' ?' }}</span>
          </div>
          <div v-if="net.asn && net.asn !== 'unknown'" class="net__meta"><span class="ltr">AS{{ net.asn }} · {{ net.org }} · {{ net.country.toUpperCase() }}</span></div>
        </template>
        <div v-else-if="error" class="net__error">{{ error }}</div>
        <template v-else>
          <Skeleton width="10rem" height="1.4rem" class="mb-1" />
          <Skeleton width="14rem" height="0.9rem" />
        </template>
      </div>
      <Button icon="pi pi-refresh" text rounded :aria-label="t('cleanIp.refreshNetwork')" v-tooltip.bottom="t('cleanIp.refreshNetwork')" @click="$emit('refresh')" />
    </div>
    <Message v-if="vpnOn" severity="warn" :closable="false" class="mt-3">{{ t('cleanIp.vpnWarning') }}</Message>
  </section>
</template>

<style scoped>
.net {
  margin-bottom: 0;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, color-mix(in srgb, var(--p-primary-color) 10%, var(--p-content-background)), var(--p-content-background) 60%);
}
.net__main {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.net__icon {
  width: 3rem;
  height: 3rem;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  border-radius: 1rem;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.net__icon--warn {
  background: var(--p-orange-500);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--p-orange-500) 35%, transparent);
}
.net__body {
  flex: 1;
  min-width: 0;
}
.net__label {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.net__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
}
.net__code {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.net__code--as {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
  font-variant-numeric: tabular-nums;
}
.net__meta {
  margin-top: 0.15rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.net__error {
  color: var(--p-red-500);
  font-size: 0.9rem;
}
.ltr {
  direction: ltr;
  unicode-bidi: isolate;
}
</style>
