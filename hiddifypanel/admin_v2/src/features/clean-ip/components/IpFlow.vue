<script setup lang="ts">
/**
 * Clean IPs for a CDN domain, in the order an admin thinks of it: 1. which domain and whose users (operator),
 * 2. find IPs that work (a scan from this browser), 3. put the best ones in the domain (the other operators' kept).
 */
import { computed, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { apiErrorMessage } from '@/core/api/client'
import { domainsApi, type DomainRow } from '@/features/domains/api'
import AddressChips from '@/shared/components/AddressChips.vue'
import OperatorIpEditor from '@/shared/components/OperatorIpEditor.vue'
import OperatorPicker from '@/shared/components/OperatorPicker.vue'
import { useAsnNames } from '@/shared/composables/useAsnNames'
import { addressesOf, parseOperatorIps, type OperatorKey } from '@/shared/utils/operator-ips'
import { mergeCdnIp, type CleanIpNetwork } from '../api'
import type { IpScan } from '../composables/useIpScan'
import FlowStep from './FlowStep.vue'
import ScanCard from './ScanCard.vue'
import { operatorLabel } from './operatorLabel'

const props = defineProps<{ scan: IpScan; net: CleanIpNetwork | null; domains: DomainRow[]; loaded: boolean }>()
const emit = defineEmits<{ saved: [domains: DomainRow[]]; copy: [text: string] }>()
const domainId = defineModel<number | null>('domainId', { required: true })
const perIsp = defineModel<number>('perIsp', { required: true })
const { t } = useI18n()
const toast = useToast()
const uid = useId()

// Who gets the IPs: operators (named or "AS…"); none: every operator without addresses of its own
const ops = ref<OperatorKey[]>([])
const opsTouched = ref(false)
// The IPs to save, as chips: the scan's fastest, editable before saving
const ipsText = ref('')
const preview = ref('')
const saving = ref(false)
const showAll = ref(false)

const cdnDomains = computed(() => props.domains.filter((d) => d.mode === 'cdn' || d.mode === 'worker'))
/** This network's AS ("AS12880"): offered in the operator list, and the default when Hiddify has no name for it. */
const ownAs = computed(() => (props.net && /^\d+$/.test(props.net.asn) ? `AS${props.net.asn}` : null))
const asns = useAsnNames()
const domain = computed(() => props.domains.find((d) => d.id === domainId.value))
/** Who the sentence names: the operators picked, or "every other operator". */
const whoLabel = computed(() => {
  if (!ops.value.length) return t('cleanIp.otherUsers')
  return ops.value
    .map((code) => {
      if (!code.startsWith('AS')) return operatorLabel(t, code)
      const name = asns.nameOf(code)
      return name ? `${code} (${name})` : code
    })
    .join('، ')
})
/** The scan's fastest IPs: what the IP chips start with. */
const chosen = computed(() => props.scan.passed.value.slice(0, perIsp.value))
const ips = computed(() => addressesOf(ipsText.value))
const dirty = computed(() => preview.value.trim() !== (domain.value?.cdn_ip ?? '').trim())

/** What the domain already has for these operators (replaced by the save): addresses, and for whom. */
const existing = computed(() => {
  const rows = parseOperatorIps(domain.value?.cdn_ip ?? '')
  const mine = ops.value.length ? rows.filter((r) => r.operators.some((c) => ops.value.includes(c))) : rows.filter((r) => !r.operators.length)
  return {
    hosts: [...new Set(mine.flatMap((r) => addressesOf(r.host)))],
    who: [...new Set(mine.flatMap((r) => r.operators.filter((c) => ops.value.includes(c))))],
  }
})
const targetDone = computed(() => !!domain.value)
const scanDone = computed(() => !props.scan.running.value && chosen.value.length > 0)

function rebuild() {
  if (!domain.value) return
  if (!ips.value.length) {
    preview.value = domain.value.cdn_ip || ''
    return
  }
  preview.value = mergeCdnIp(domain.value.cdn_ip, ops.value, ips.value).text
}

async function save() {
  if (!domainId.value) return
  saving.value = true
  try {
    const state = await domainsApi.update(domainId.value, { cdn_ip: preview.value.trim() })
    emit('saved', state.domains)
    toast.add({ severity: 'success', summary: t('cleanIp.saved', { domain: domain.value?.domain ?? '' }), life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
  } finally {
    saving.value = false
  }
}

// The detected operator (or its AS) and the first CDN domain are the defaults; any change rebuilds the field.
watch(() => props.net, (net) => {
  if (opsTouched.value || ops.value.length || !net) return
  ops.value = [ownAs.value, net.short_name !== 'unknown' ? net.short_name : null].filter((c): c is OperatorKey => !!c)
}, { immediate: true })
// A scan that ends (or another count) gives the chips its fastest IPs again
watch([chosen, () => props.scan.running.value], () => {
  if (!props.scan.running.value) ipsText.value = chosen.value.map((r) => r.ip).join(', ')
}, { immediate: true })
watch(cdnDomains, (list) => {
  if (!domainId.value && list.length) domainId.value = list[0].id
}, { immediate: true })
watch([domainId, ops, ipsText, () => props.domains], rebuild, { immediate: true, deep: true })
</script>

<template>
  <section class="card flow">
    <div v-if="!loaded" class="flow__loading"><i class="pi pi-spin pi-spinner" /></div>
    <Message v-else-if="!cdnDomains.length" severity="info" :closable="false" icon="pi pi-info-circle">
      {{ t('cleanIp.noCdnDomain') }}
      <RouterLink :to="{ name: 'domains' }" class="flow__link">{{ t('cleanIp.goDomains') }}</RouterLink>
    </Message>

    <template v-else>
      <!-- 1. where and for whom -->
      <FlowStep :number="1" :title="t('cleanIp.flow1Domain')" :hint="t('cleanIp.flow1DomainHint')" :done="targetDone">
        <div class="flow__target">
          <label class="flow__field">
            <span><i class="pi pi-globe" /> {{ t('cleanIp.qWhere') }}</span>
            <Select v-model="domainId" :input-id="`${uid}-domain`" :options="cdnDomains" option-label="domain" option-value="id" fluid />
          </label>
        </div>
      </FlowStep>

      <!-- 2. find IPs that work -->
      <FlowStep :number="2" :title="t('cleanIp.flow2')" :hint="t('cleanIp.flow2Hint')" :done="scanDone">
        <ScanCard :scan="scan" bare :show="perIsp" @copy="emit('copy', $event)" />
      </FlowStep>

      <!-- 3. into the domain -->
      <FlowStep :number="3" :title="t('cleanIp.flow3')" last>
        <div v-if="!chosen.length" class="flow__wait">
          <i class="pi pi-hourglass" />
          {{ scan.running.value ? t('cleanIp.flow3Scanning') : t('cleanIp.flow3Wait') }}
        </div>
        <template v-else>
          <div class="flow__summary">
            <p class="flow__sentence">
              {{ t('cleanIp.flow3Sentence', { count: ips.length }) }}
              <b class="flow__who">{{ whoLabel }}</b>
              {{ t('cleanIp.flow3On') }}
              <b dir="ltr">{{ domain?.domain }}</b>
            </p>
            <div class="flow__count">
              <span>{{ t('cleanIp.qHowMany') }}</span>
              <InputNumber v-model="perIsp" :min="1" :max="20" show-buttons button-layout="horizontal" class="flow__number" />
            </div>
          </div>
          <!-- one row, as in the domain's CDN IP field: these addresses, for these operators -->
          <div class="flow__row">
            <AddressChips v-model="ipsText" :placeholder="t('operatorIps.host')" :aria-label="t('cleanIp.flowIps')" />
            <small class="flow__field-hint">{{ t('cleanIp.flowIpsHint') }}</small>
            <div class="flow__for">
              <span class="flow__for-label">{{ t('operatorIps.for') }}</span>
              <OperatorPicker v-model="ops" :suggest="ownAs ? [ownAs] : []" class="flow__ops" @update:model-value="opsTouched = true" />
            </div>
            <small class="flow__field-hint">{{ t('cleanIp.qWhoMulti') }}</small>
          </div>
          <Message v-if="existing.hosts.length" severity="warn" :closable="false" icon="pi pi-exclamation-triangle" class="flow__existing">
            {{ t('cleanIp.existingWarn', { count: existing.hosts.length, who: existing.who.length ? existing.who.join('، ') : t('cleanIp.otherUsers') }) }}
            <span class="flow__existing-list" dir="ltr">{{ existing.hosts.slice(0, 6).join(', ') }}{{ existing.hosts.length > 6 ? ' …' : '' }}</span>
          </Message>
        </template>

        <button type="button" class="flow__all" :aria-expanded="showAll" @click="showAll = !showAll">
          <i class="pi" :class="showAll ? 'pi-chevron-up' : 'pi-chevron-down'" />
          {{ t('cleanIp.flowShowAll') }}
          <span v-if="dirty" class="flow__dirty"><i class="pi pi-circle-fill" /> {{ t('cleanIp.unsaved') }}</span>
        </button>
        <div v-show="showAll" class="flow__editor">
          <p class="flow__editor-hint">{{ t('cleanIp.flowAllHint') }}</p>
          <OperatorIpEditor v-model="preview" />
        </div>

        <div class="flow__actions">
          <Button :label="t('cleanIp.save')" icon="pi pi-cloud-upload" size="large" :loading="saving" :disabled="!domainId || !preview.trim() || !dirty" @click="save" />
        </div>
      </FlowStep>
    </template>
  </section>
</template>

<style scoped>
.flow {
  margin-bottom: 0;
  padding: 1.5rem 1.25rem;
}
.flow__loading {
  padding: 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
}
.flow__link {
  margin-inline-start: 0.35rem;
  font-weight: 600;
  color: var(--p-primary-color);
}
.flow__target {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
  gap: 0.75rem;
}
.flow__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
  font-size: 0.85rem;
  font-weight: 600;
}
.flow__field .pi {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.flow__wait {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.9rem;
  border-radius: 0.65rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
}
.flow__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 1rem;
  padding: 0.75rem 0.9rem;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-green-500) 8%, var(--p-content-background));
  border: 1px solid color-mix(in srgb, var(--p-green-500) 35%, var(--p-content-border-color));
}
.flow__sentence {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.7;
}
.flow__count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.flow__number :deep(input) {
  inline-size: 3rem;
  text-align: center;
}
/* operator codes and AS numbers keep Latin digits */
.flow__who {
  font-family: 'Vazirmatn', 'Lato', sans-serif;
}
.flow__field-hint {
  font-size: 0.74rem;
  font-weight: 400;
  color: var(--p-text-muted-color);
}
/* the row: as a row of the domain's CDN IP field */
.flow__row {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: var(--p-content-background);
}
.flow__row:focus-within {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, var(--p-content-border-color));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.flow__existing {
  margin-top: 0.6rem;
}
.flow__existing-list {
  display: block;
  margin-top: 0.25rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}
.flow__for {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.flow__for-label {
  flex: none;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.flow__ops {
  flex: 1;
}
@media (max-width: 575px) {
  .flow__for {
    flex-direction: column;
    align-items: stretch;
  }
}
.flow__all {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.9rem;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}
.flow__all .pi-chevron-up,
.flow__all .pi-chevron-down {
  font-size: 0.72rem;
}
.flow__dirty {
  margin-inline-start: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-orange-500);
}
.flow__dirty .pi {
  font-size: 0.45rem;
  vertical-align: middle;
}
.flow__editor {
  margin-top: 0.6rem;
  padding: 0.85rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
}
.flow__editor-hint {
  margin: 0 0 0.6rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.flow__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}
@media (max-width: 575px) {
  .flow__actions > * {
    flex: 1;
  }
}
</style>
