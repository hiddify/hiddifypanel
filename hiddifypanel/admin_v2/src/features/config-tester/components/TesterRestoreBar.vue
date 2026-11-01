<script setup lang="ts">
/**
 * Top of the config tester: the configs it turned off, kept until the admin restores them (nothing comes back by
 * itself), and the Apply notice after turning configs off or on.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ApplyNotice from '@/shared/components/ApplyNotice.vue'
import { apiErrorMessage } from '@/core/api/client'
import { disabledProxies, loadDisabled, pendingApply, restoreProxies } from '@/features/config-tester/proxies'

const { t, locale } = useI18n()
const confirm = useConfirm()
const toast = useToast()

const open = ref(false)
const busy = ref(false)
const off = computed(() => disabledProxies.value.filter((p) => p.off))
const since = computed(() => {
  const first = Math.min(...off.value.map((p) => p.at))
  return Number.isFinite(first) ? new Date(first * 1000).toLocaleString(locale.value, { dateStyle: 'medium', timeStyle: 'short' }) : ''
})

onMounted(() => loadDisabled().catch(() => {}))

function restore() {
  const n = off.value.length
  confirm.require({
    header: t('configTester.proxies.restoreConfirmTitle', { n }, n),
    message: t('configTester.proxies.restoreConfirmMessage'),
    icon: 'pi pi-history',
    defaultFocus: 'accept',
    rejectProps: { label: t('common.cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('configTester.proxies.restore') },
    accept: async () => {
      busy.value = true
      try {
        const back = await restoreProxies()
        toast.add({ severity: 'success', summary: t('configTester.proxies.restored', { n: back.length }, back.length), life: 4000 })
        if (off.value.length) toast.add({ severity: 'warn', summary: t('configTester.proxies.stillOff', { names: off.value.map((p) => p.name).join(', ') }), life: 8000 })
      } catch (e) {
        toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 6000 })
      } finally {
        busy.value = false
      }
    },
  })
}
</script>

<template>
  <ApplyNotice v-model="pendingApply" />
  <Transition name="trb">
    <section v-if="off.length" class="trb">
      <span class="trb__icon" aria-hidden="true"><i class="pi pi-power-off" /></span>
      <div class="trb__body">
        <div class="trb__title">{{ t('configTester.proxies.restoreTitle', { n: off.length }, off.length) }}</div>
        <div class="trb__sub">{{ t('configTester.proxies.restoreHint', { date: since }) }}</div>
        <ul v-if="open" class="trb__names">
          <li v-for="p in off" :key="p.id" dir="ltr">{{ p.name }}</li>
        </ul>
      </div>
      <div class="trb__acts">
        <Button :label="open ? t('configTester.proxies.hideList') : t('configTester.proxies.showList')" :icon="open ? 'pi pi-angle-up' : 'pi pi-angle-down'" text size="small" severity="secondary" @click="open = !open" />
        <Button :label="t('configTester.proxies.restore')" icon="pi pi-history" size="small" :loading="busy" @click="restore" />
      </div>
    </section>
  </Transition>
</template>

<style scoped>
.trb {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.85rem 1rem;
  border: 1px solid color-mix(in srgb, var(--p-orange-400, #fb923c) 45%, transparent);
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-orange-400, #fb923c) 9%, var(--p-content-background));
}
.trb__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  flex: none;
  border-radius: 10px;
  color: var(--p-orange-600, #ea580c);
  background: color-mix(in srgb, var(--p-orange-400, #fb923c) 20%, transparent);
}
.trb__body {
  flex: 1;
  min-width: 12rem;
}
.trb__title {
  font-weight: 700;
}
.trb__sub {
  margin-top: 0.15rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.trb__names {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.6rem 0 0;
  padding: 0;
  list-style: none;
}
.trb__names li {
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.trb__acts {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-inline-start: auto;
}
.trb-enter-active,
.trb-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.trb-enter-from,
.trb-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
