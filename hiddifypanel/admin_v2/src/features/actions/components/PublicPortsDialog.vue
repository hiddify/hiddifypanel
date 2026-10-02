<script setup lang="ts">
/** Every port this server needs open to the internet (TCP and UDP) and what uses it, ready for a firewall. */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import { apiErrorMessage, getHttp } from '@/core/api/client'

type PortMap = Record<string, string>
interface PublicPorts {
  tcp: PortMap
  udp: PortMap
}

const visible = defineModel<boolean>('visible', { required: true })
const { t } = useI18n()
const toast = useToast()

const data = ref<PublicPorts | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await getHttp().get<PublicPorts | string>('all-public-port/')
    data.value = typeof res.data === 'string' ? (JSON.parse(res.data) as PublicPorts) : res.data
  } catch (err) {
    error.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}
watch(visible, (open) => open && load(), { immediate: true })

/** Ports grouped by what uses them (one row per service, its ports in order). */
function groups(map: PortMap | undefined) {
  const byService = new Map<string, number[]>()
  for (const [port, service] of Object.entries(map ?? {})) {
    byService.set(service, [...(byService.get(service) ?? []), Number(port)])
  }
  return [...byService.entries()].map(([service, ports]) => ({ service, ports: ports.sort((a, b) => a - b) })).sort((a, b) => a.ports[0]! - b.ports[0]!)
}
const sections = computed(() => [
  { proto: 'tcp' as const, rows: groups(data.value?.tcp), count: Object.keys(data.value?.tcp ?? {}).length },
  { proto: 'udp' as const, rows: groups(data.value?.udp), count: Object.keys(data.value?.udp ?? {}).length },
])

function list(proto: 'tcp' | 'udp'): string {
  return Object.keys(data.value?.[proto] ?? {}).join(',')
}

/** Ready to paste: `ufw` commands for every port. */
const ufw = computed(() =>
  (['tcp', 'udp'] as const)
    .flatMap((proto) => Object.keys(data.value?.[proto] ?? {}).map((p) => `ufw allow ${p}/${proto}`))
    .join('\n'),
)

async function copy(text: string, what: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('actions.ports.copied', { what }), life: 2000 })
  } catch {
    /* clipboard blocked */
  }
}

const SERVICE_ICON: Record<string, string> = {
  tls: 'pi pi-lock',
  http: 'pi pi-globe',
  quic: 'pi pi-bolt',
  ssh: 'pi pi-desktop',
  wireguard: 'pi pi-shield',
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :header="t('actions.ports.title')" :style="{ width: 'min(40rem, calc(100vw - 1.5rem))' }" :breakpoints="{ '640px': '100vw' }">
    <p class="pp-lead">{{ t('actions.ports.lead') }}</p>

    <div v-if="loading" class="pp-grid">
      <Skeleton height="10rem" border-radius="14px" />
      <Skeleton height="10rem" border-radius="14px" />
    </div>
    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>

    <template v-else-if="data">
      <div class="pp-grid">
        <section v-for="s in sections" :key="s.proto" class="pp-card" :class="`pp-card--${s.proto}`">
          <header class="pp-card__head">
            <span class="pp-card__proto">{{ s.proto.toUpperCase() }}</span>
            <span class="pp-card__count">{{ t('actions.ports.count', { n: s.count }) }}</span>
            <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('actions.ports.copyList')" v-tooltip.top="t('actions.ports.copyList')" :disabled="!s.count" @click="copy(list(s.proto), s.proto.toUpperCase())" />
          </header>
          <ul class="pp-rows">
            <li v-for="r in s.rows" :key="r.service" class="pp-row">
              <span class="pp-row__service"><i :class="SERVICE_ICON[r.service] ?? 'pi pi-circle'" />{{ r.service }}</span>
              <span class="pp-row__ports" dir="ltr">
                <code v-for="p in r.ports" :key="p">{{ p }}</code>
              </span>
            </li>
            <li v-if="!s.rows.length" class="pp-row pp-row--empty">{{ t('actions.ports.none') }}</li>
          </ul>
        </section>
      </div>

      <div class="pp-ufw">
        <div class="pp-ufw__head">
          <span><i class="pi pi-shield" />{{ t('actions.ports.firewall') }}</span>
          <Button :label="t('common.copy')" icon="pi pi-copy" size="small" text @click="copy(ufw, 'ufw')" />
        </div>
        <pre dir="ltr">{{ ufw }}</pre>
      </div>
    </template>

    <template #footer>
      <Button :label="t('actions.ports.refresh')" icon="pi pi-refresh" severity="secondary" text :loading="loading" @click="load" />
      <Button :label="t('donation.close')" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.pp-lead {
  margin: 0 0 1rem;
  font-size: 0.88rem;
  color: var(--p-text-muted-color);
}
.pp-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}
.pp-card {
  --tone: var(--p-primary-color);
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}
.pp-card--udp {
  --tone: var(--p-violet-500, #8b5cf6);
}
.pp-card__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.5rem 0.45rem 0.85rem;
  background: color-mix(in srgb, var(--tone) 9%, transparent);
  border-bottom: 1px solid var(--p-content-border-color);
}
.pp-card__proto {
  font-weight: 800;
  letter-spacing: 0.05em;
  color: var(--tone);
}
.pp-card__count {
  flex: 1;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.pp-rows {
  margin: 0;
  padding: 0.35rem 0;
  list-style: none;
}
.pp-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.4rem 0.85rem;
}
.pp-row + .pp-row {
  border-top: 1px dashed var(--p-content-border-color);
}
.pp-row__service {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.86rem;
  font-weight: 600;
  text-transform: capitalize;
}
.pp-row__service i {
  font-size: 0.8rem;
  color: var(--tone);
}
.pp-row__ports {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.25rem;
}
.pp-row__ports code {
  padding: 0.05rem 0.45rem;
  border-radius: 7px;
  font-size: 0.78rem;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.pp-row--empty {
  justify-content: center;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.pp-ufw {
  margin-top: 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}
.pp-ufw__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.3rem 0.4rem 0.3rem 0.85rem;
  font-size: 0.84rem;
  font-weight: 600;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.pp-ufw__head span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.pp-ufw pre {
  margin: 0;
  max-height: 10rem;
  overflow: auto;
  padding: 0.6rem 0.85rem;
  font-size: 0.76rem;
  text-align: start;
}
@media (max-width: 560px) {
  .pp-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
