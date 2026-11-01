<script setup lang="ts">
/**
 * After a test: this panel's configs (custom proxies) the test reached, worst first. Down ones (every tested link
 * failed) are picked to be turned off; partly down ones (some domains still work) only when the admin picks them.
 * Turned-off ones can be brought back with Restore (the bar at the top of the page), never by themselves.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import { apiErrorMessage } from '@/core/api/client'
import { disableProxies, proxyHealth, type ProxyHealth } from '@/features/config-tester/proxies'

/** the finished results of the test; null while it runs */
const props = defineProps<{ results: { name: string; ok: boolean }[] | null }>()

const { t } = useI18n()
const confirm = useConfirm()
const toast = useToast()

const proxies = ref<ProxyHealth[]>([])
const picked = ref<number[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const showUp = ref(false)
const showPartial = ref(false)

const down = computed(() => proxies.value.filter((p) => p.status === 'down'))
const partial = computed(() => proxies.value.filter((p) => p.status === 'partial'))
const up = computed(() => proxies.value.filter((p) => p.status === 'up'))
const pickable = computed(() => proxies.value.filter((p) => p.enabled && p.status !== 'up'))
const pickedOn = computed(() => picked.value.filter((id) => pickable.value.some((p) => p.id === id)))

let asked = ''
watch(
  () => props.results,
  async (results) => {
    if (!results?.length) return
    const key = JSON.stringify(results)
    if (key === asked) return
    asked = key
    loading.value = true
    error.value = ''
    try {
      proxies.value = await proxyHealth(results)
      // smart default: every config that is down and still on
      picked.value = proxies.value.filter((p) => p.status === 'down' && p.enabled).map((p) => p.id)
      showPartial.value = false
    } catch (e) {
      error.value = apiErrorMessage(e)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

function turnOff() {
  const ids = pickedOn.value
  if (!ids.length) return
  confirm.require({
    header: t('configTester.proxies.confirmTitle', { n: ids.length }, ids.length),
    message: t('configTester.proxies.confirmMessage'),
    icon: 'pi pi-power-off',
    defaultFocus: 'reject',
    rejectProps: { label: t('common.cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('configTester.proxies.disable', { n: ids.length }, ids.length), severity: 'danger' },
    accept: async () => {
      saving.value = true
      try {
        await disableProxies(ids)
        for (const p of proxies.value) if (ids.includes(p.id)) p.enabled = false
        picked.value = []
        toast.add({ severity: 'success', summary: t('configTester.proxies.disabledDone', { n: ids.length }, ids.length), life: 4000 })
      } catch (e) {
        toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 6000 })
      } finally {
        saving.value = false
      }
    },
  })
}
</script>

<template>
  <section v-if="results" class="ph" :aria-busy="loading">
    <header class="ph__head">
      <span class="ph__icon" aria-hidden="true"><i class="pi pi-server" /></span>
      <div class="min-w-0 flex-1">
        <h3 class="ph__title">{{ t('configTester.proxies.title') }}</h3>
        <p class="ph__sub">{{ t('configTester.proxies.subtitle') }}</p>
      </div>
      <div v-if="proxies.length" class="ph__chips">
        <span class="ph__chip ph__chip--down"><b>{{ down.length }}</b> {{ t('configTester.proxies.down') }}</span>
        <span class="ph__chip ph__chip--partial"><b>{{ partial.length }}</b> {{ t('configTester.proxies.partial') }}</span>
        <span class="ph__chip ph__chip--up"><b>{{ up.length }}</b> {{ t('configTester.proxies.up') }}</span>
      </div>
    </header>

    <p v-if="loading" class="ph__note"><i class="pi pi-spin pi-spinner" />{{ t('configTester.proxies.checking') }}</p>
    <p v-else-if="error" class="ph__note ph__note--error"><i class="pi pi-exclamation-circle" />{{ error }}</p>
    <p v-else-if="!proxies.length" class="ph__note"><i class="pi pi-info-circle" />{{ t('configTester.proxies.notOurs') }}</p>
    <template v-else>
      <p v-if="!down.length && !partial.length" class="ph__note ph__note--good"><i class="pi pi-check-circle" />{{ t('configTester.proxies.allGood') }}</p>
      <p v-else-if="!down.length" class="ph__note"><i class="pi pi-info-circle" />{{ t('configTester.proxies.noneDown', { n: partial.length }, partial.length) }}</p>
      <ul v-if="down.length || (partial.length && showPartial)" class="ph__list">
        <li v-for="p in showPartial ? [...down, ...partial] : down" :key="p.id" class="ph__row" :class="[`ph__row--${p.status}`, { 'ph__row--off': !p.enabled }]">
          <Checkbox v-model="picked" :value="p.id" :input-id="`ph-${p.id}`" :disabled="!p.enabled || saving" />
          <label :for="`ph-${p.id}`" class="ph__row-main">
            <span class="ph__name" dir="ltr">{{ p.name }}</span>
            <span class="ph__meta">
              <span class="ph__badge" :class="`ph__badge--${p.status}`">{{ t(`configTester.proxies.${p.status}`) }}</span>
              <span dir="ltr">{{ t('configTester.proxies.failedOf', { failed: p.failed, tested: p.tested }) }}</span>
              <span v-if="!p.enabled" class="ph__off"><i class="pi pi-power-off" />{{ t('configTester.proxies.alreadyOff') }}</span>
              <span v-else-if="p.status === 'partial'" class="ph__hint">{{ t('configTester.proxies.partialHint') }}</span>
            </span>
          </label>
        </li>
      </ul>
      <div class="ph__foot">
        <button v-if="partial.length" type="button" class="ph__more" :aria-expanded="showPartial" @click="showPartial = !showPartial">
          <i class="pi" :class="showPartial ? 'pi-angle-up' : 'pi-angle-down'" />{{ showPartial ? t('configTester.proxies.hidePartial') : t('configTester.proxies.showPartial', { n: partial.length }, partial.length) }}
        </button>
        <button v-if="up.length" type="button" class="ph__more" :aria-expanded="showUp" @click="showUp = !showUp">
          <i class="pi" :class="showUp ? 'pi-angle-up' : 'pi-angle-down'" />{{ t('configTester.proxies.showUp', { n: up.length }, up.length) }}
        </button>
        <Button
          v-if="pickable.length"
          icon="pi pi-power-off"
          :label="t('configTester.proxies.disable', { n: pickedOn.length }, pickedOn.length)"
          severity="danger"
          :outlined="!pickedOn.length"
          size="small"
          class="ms-auto"
          :disabled="!pickedOn.length"
          :loading="saving"
          @click="turnOff"
        />
      </div>
      <ul v-if="showUp" class="ph__list ph__list--up">
        <li v-for="p in up" :key="p.id" class="ph__row ph__row--up">
          <i class="pi pi-check-circle ph__ok" />
          <span class="ph__name" dir="ltr">{{ p.name }}</span>
          <span class="ph__meta" dir="ltr">{{ t('configTester.proxies.workingOf', { ok: p.tested - p.failed, tested: p.tested }) }}</span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.ph {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-primary-color) 3%, var(--p-content-background));
}
.ph__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.ph__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  flex: none;
  border-radius: 12px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.ph__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}
.ph__sub {
  margin: 0.15rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.ph__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.ph__chip {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--ph-c);
  background: color-mix(in srgb, var(--ph-c) 12%, transparent);
}
.ph__chip--down {
  --ph-c: var(--p-red-600, #dc2626);
}
.ph__chip--partial {
  --ph-c: var(--p-orange-600, #ea580c);
}
.ph__chip--up {
  --ph-c: var(--p-green-600, #16a34a);
}
.ph__note {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0.85rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.ph__note--error {
  color: var(--p-red-600, #dc2626);
}
.ph__note--good {
  color: var(--p-green-600, #16a34a);
}
.ph__list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 0.85rem 0 0;
  padding: 0;
  list-style: none;
}
.ph__row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 3px solid var(--ph-c, var(--p-content-border-color));
  border-radius: 10px;
  background: var(--p-content-background);
}
.ph__row--down {
  --ph-c: var(--p-red-500, #ef4444);
}
.ph__row--partial {
  --ph-c: var(--p-orange-400, #fb923c);
}
.ph__row--up {
  --ph-c: var(--p-green-500, #22c55e);
  padding-block: 0.4rem;
}
.ph__row--off {
  opacity: 0.6;
}
.ph__row-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
  cursor: pointer;
}
.ph__name {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.ph__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.6rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.ph__row--up .ph__meta {
  margin-inline-start: auto;
}
.ph__badge {
  padding: 0.05rem 0.45rem;
  border-radius: 6px;
  font-weight: 600;
  color: var(--ph-c);
  background: color-mix(in srgb, var(--ph-c) 14%, transparent);
}
.ph__badge--down {
  --ph-c: var(--p-red-600, #dc2626);
}
.ph__badge--partial {
  --ph-c: var(--p-orange-600, #ea580c);
}
.ph__off {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.ph__off i {
  font-size: 0.7rem;
}
.ph__hint {
  font-style: italic;
}
.ph__ok {
  color: var(--p-green-600, #16a34a);
}
.ph__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.85rem;
}
.ph__more {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  font: inherit;
  font-size: 0.8rem;
  color: var(--p-primary-color);
  background: none;
  cursor: pointer;
}
</style>
