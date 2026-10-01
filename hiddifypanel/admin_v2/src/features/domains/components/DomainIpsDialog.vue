<script setup lang="ts">
/** Where a domain points right now (its DNS), and whether each address is this server. */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import { apiErrorMessage, getHttp } from '@/core/api/client'

interface Ips {
  domain: string
  target: string
  ips: { ip: string; version: number; is_server_ip: boolean }[]
}

const props = defineProps<{ domainId: number | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const { t } = useI18n()

const data = ref<Ips | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (props.domainId === null) return
  loading.value = true
  error.value = null
  data.value = null
  try {
    data.value = (await getHttp().get<Ips>(`domains-page/${props.domainId}/ips/`, { timeout: 20_000 })).data
  } catch (err) {
    error.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}
watch(visible, (open) => open && load())
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :header="data?.domain || t('domains.ips.title')" :style="{ width: 'min(28rem, calc(100vw - 1.5rem))' }">
    <div v-if="loading" class="ips-list"><Skeleton v-for="i in 2" :key="i" height="2.6rem" border-radius="12px" /></div>
    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-else-if="data">
      <p v-if="data.target && data.target !== data.domain" class="ips-via" dir="ltr"><i class="pi pi-arrow-right" />{{ data.target }}</p>
      <p v-if="!data.ips.length" class="ips-empty"><i class="pi pi-question-circle" />{{ t('domains.ips.none') }}</p>
      <ul v-else class="ips-list">
        <li v-for="r in data.ips" :key="r.ip" class="ips-row" :class="{ 'ips-row--mine': r.is_server_ip }">
          <span class="ips-ver">IPv{{ r.version }}</span>
          <code dir="ltr">{{ r.ip }}</code>
          <span class="ips-tag" :class="r.is_server_ip ? 'ips-tag--mine' : 'ips-tag--other'">
            <i :class="r.is_server_ip ? 'pi pi-server' : 'pi pi-cloud'" />{{ r.is_server_ip ? t('domains.ips.thisServer') : t('domains.ips.elsewhere') }}
          </span>
        </li>
      </ul>
    </template>
    <template #footer>
      <Button :label="t('legacy.refresh')" icon="pi pi-refresh" severity="secondary" text :loading="loading" @click="load" />
      <Button :label="t('donation.close')" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.ips-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ips-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.75rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
}
.ips-row--mine {
  border-color: color-mix(in srgb, var(--p-green-500, #22c55e) 45%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 6%, transparent);
}
.ips-ver {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
}
.ips-row code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 0.86rem;
}
.ips-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}
.ips-tag--mine {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 14%, transparent);
}
.ips-tag--other {
  color: var(--p-orange-600, #ea580c);
  background: color-mix(in srgb, var(--p-orange-500, #f97316) 14%, transparent);
}
.ips-via {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.6rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.ips-empty {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  color: var(--p-text-muted-color);
}
</style>
