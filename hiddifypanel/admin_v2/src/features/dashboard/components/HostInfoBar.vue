<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardHost } from '@/core/api/generated'
import { formatDuration } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import MiniStat from './MiniStat.vue'

const props = defineProps<{ host: DashboardHost | null }>()

const { t } = useI18n()

const items = computed(() => [
  { label: t('dashboard.hostname'), value: props.host?.hostname || '—', icon: 'pi pi-server', accent: SERIES.usage },
  {
    label: t('dashboard.uptime'),
    value: props.host ? formatDuration(props.host.uptime_s) : '—',
    icon: 'pi pi-clock',
    accent: SERIES.online,
  },
  {
    label: t('dashboard.panelVersion'),
    value: props.host?.panel_version || '—',
    icon: 'pi pi-tag',
    accent: SERIES.users,
  },
])
</script>

<template>
  <div class="host-bar">
    <MiniStat
      v-for="item in items"
      :key="item.label"
      :label="item.label"
      :value="item.value"
      :icon="item.icon"
      :accent="item.accent"
    />
  </div>
</template>

<style scoped>
.host-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.75rem 1.5rem;
  padding: 0.9rem 1.25rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--p-content-background) 85%, transparent);
}
</style>
