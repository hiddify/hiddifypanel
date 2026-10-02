<script setup lang="ts">
/** One gateway port (TLS or HTTP) with a live check: free, or only used by haproxy / rpxy-l4. Empty = the default. */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import { domainsApi, type PortCheck } from '@/features/domains/api'

const props = defineProps<{ kind: 'tls' | 'http'; defaultPort: number; domainId?: number | null; inputId: string }>()
const model = defineModel<number | null>({ required: true })
/** False while the port is being checked or is not usable (the dialog waits for it). */
const valid = defineModel<boolean>('valid', { default: true })

const { t } = useI18n()
const checking = ref(false)
const result = ref<PortCheck | null>(null)
let timer: number | undefined
let seq = 0

const isDefault = computed(() => model.value === null || model.value === props.defaultPort)

async function check(port: number) {
  const mine = ++seq
  checking.value = true
  try {
    const res = await domainsApi.checkPort(props.kind, port, props.domainId)
    if (mine !== seq) return
    result.value = res
  } catch {
    if (mine === seq) result.value = { port, kind: props.kind, ok: false, code: 'unknown' }
  } finally {
    if (mine === seq) checking.value = false
  }
}

watch(
  model,
  (port) => {
    window.clearTimeout(timer)
    seq++
    result.value = null
    checking.value = false
    if (port === null || port === props.defaultPort) {
      valid.value = true
      return
    }
    valid.value = false
    checking.value = true
    timer = window.setTimeout(() => check(port), 450)
  },
  { immediate: true },
)
watch([result, checking], () => {
  if (isDefault.value) valid.value = true
  else valid.value = !checking.value && !!result.value?.ok
})

function detailText(r: PortCheck): string {
  const d = r.detail || ''
  if (r.code === 'reserved') {
    const [what, name] = d.split(/:(.*)/s)
    if (what === 'proxy') return t('domains.port.usedByProxy', { name })
    if (what === 'domain') return t('domains.port.usedByDomain', { name })
    if (what === 'gateway') return t(`domains.port.usedByGateway.${name}`)
    if (what === 'setting') return t('domains.port.usedBySetting', { name: name?.replace(/_/g, ' ') })
    return t('domains.port.system')
  }
  if (r.code === 'busy') return t('domains.port.busy', { name: d })
  if (r.code === 'invalid') return t('domains.port.invalid')
  return t('domains.port.unknown')
}
</script>

<template>
  <div class="port">
    <div class="port__row">
      <span class="port__proto" :class="`port__proto--${kind}`">{{ kind === 'tls' ? 'TLS' : 'HTTP' }}</span>
      <InputNumber
        v-model="model"
        :input-id="inputId"
        :use-grouping="false"
        :min="1"
        :max="65535"
        :placeholder="String(defaultPort)"
        class="port__input"
        fluid
      />
      <span class="port__state" aria-live="polite">
        <template v-if="isDefault"><i class="pi pi-check-circle port__ok" /><span>{{ t('domains.port.default') }}</span></template>
        <template v-else-if="checking"><i class="pi pi-spin pi-spinner" /><span>{{ t('domains.port.checking') }}</span></template>
        <template v-else-if="result?.ok"><i class="pi pi-check-circle port__ok" /><span>{{ t('domains.port.free') }}</span></template>
        <template v-else-if="result"><i class="pi pi-times-circle port__bad" /><span class="port__bad-text">{{ detailText(result) }}</span></template>
      </span>
    </div>
  </div>
</template>

<style scoped>
.port__row {
  display: grid;
  grid-template-columns: auto minmax(4.5rem, 6rem) minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
}
.port__proto {
  justify-self: start;
  padding: 0.15rem 0.5rem;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: var(--p-green-700, #15803d);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 14%, transparent);
}
.port__proto--http {
  color: var(--p-sky-700, #0369a1);
  background: color-mix(in srgb, var(--p-sky-500, #0ea5e9) 14%, transparent);
}
.port__state {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.port__ok {
  color: var(--p-green-500, #22c55e);
}
.port__bad {
  color: var(--p-red-500, #ef4444);
}
.port__bad-text {
  color: var(--p-red-600, #dc2626);
}
.port__state span {
  overflow-wrap: anywhere;
}
</style>
