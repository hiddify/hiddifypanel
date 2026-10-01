<template>
  <PageHeader :title="t('actions.title')" :subtitle="t('actions.subtitle')" />
  <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    <Card v-for="action in visibleActions" :key="action.key" class="h-full">
      <template #title>
        <div class="flex items-center gap-2">
          <i :class="[action.icon, action.danger ? 'text-red-500' : 'text-primary']" />
          <span>{{ action.label }}</span>
        </div>
      </template>
      <template #content>
        <p class="text-muted-color m-0">{{ action.description }}</p>
      </template>
      <template #footer>
        <Button
          :label="action.label"
          :icon="action.icon"
          :severity="action.danger ? 'danger' : undefined"
          :outlined="!action.danger"
          :loading="busy === action.key"
          :disabled="busy !== null && busy !== action.key"
          @click="run(action)"
        />
      </template>
    </Card>
  </div>
  <PublicPortsDialog v-model:visible="portsVisible" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import PageHeader from '@/shared/components/PageHeader.vue'
import PublicPortsDialog from '@/features/actions/components/PublicPortsDialog.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage, getHttp } from '@/core/api/client'
import { openLegacyAction, systemActionUrls, type SystemActionUrls } from '@/core/panelShell'

type LegacyKey = keyof SystemActionUrls

interface ActionDef {
  key: LegacyKey | 'reset_cache' | 'public_ports'
  label: string
  description: string
  icon: string
  /** Legacy endpoints that only accept POST are submitted as a form (full page load to the log view). */
  method: 'get' | 'post' | 'api'
  confirm?: boolean
  danger?: boolean
}

const { t } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()
const busy = ref<ActionDef['key'] | null>(null)
const portsVisible = ref(false)

const actions = computed<ActionDef[]>(() => [
  { key: 'reset_cache', label: t('actions.resetCache'), description: t('actions.resetCacheHint'), icon: 'pi pi-eraser', method: 'api', confirm: true },
  { key: 'public_ports', label: t('actions.ports.title'), description: t('actions.ports.hint'), icon: 'pi pi-sitemap', method: 'api' },
  { key: 'status', label: t('actions.status'), description: t('actions.statusHint'), icon: 'pi pi-chart-line', method: 'get' },
  { key: 'viewlogs', label: t('actions.viewlogs'), description: t('actions.viewlogsHint'), icon: 'pi pi-inbox', method: 'get' },
  { key: 'apply_configs', label: t('actions.applyConfigs'), description: t('actions.applyConfigsHint'), icon: 'pi pi-bolt', method: 'post', confirm: true },
  { key: 'update', label: t('actions.update'), description: t('actions.updateHint'), icon: 'pi pi-upload', method: 'post', confirm: true, danger: true },
  { key: 'reinstall', label: t('actions.reinstall'), description: t('actions.reinstallHint'), icon: 'pi pi-refresh', method: 'post', confirm: true, danger: true },
  { key: 'reset', label: t('actions.restart'), description: t('actions.restartHint'), icon: 'pi pi-power-off', method: 'post', confirm: true, danger: true },
])

// Legacy actions show up only when the server handed us their URL (super_admin).
const visibleActions = computed(() =>
  actions.value.filter((a) => a.method === 'api' || Boolean(systemActionUrls.value[a.key as LegacyKey])),
)

async function resetCache() {
  busy.value = 'reset_cache'
  try {
    await getHttp().post('reset-cache/')
    toast.add({ severity: 'success', summary: t('actions.resetCacheDone'), life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('actions.resetCacheFailed'), detail: apiErrorMessage(error), life: 5000 })
  } finally {
    busy.value = null
  }
}

function execute(action: ActionDef) {
  if (action.key === 'public_ports') {
    portsVisible.value = true
    return
  }
  if (action.method === 'api') {
    void resetCache()
    return
  }
  const url = systemActionUrls.value[action.key as LegacyKey]
  if (!url) return
  // The classic page (with its live log) opens in a dialog instead of replacing this page.
  openLegacyAction({ title: action.label, url, method: action.method })
}

function run(action: ActionDef) {
  if (!action.confirm) {
    execute(action)
    return
  }
  dangerConfirm({
    message: t('actions.confirm'),
    header: action.label,
    accept: () => execute(action),
  })
}
</script>
