<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import PageHeader from '@/shared/components/PageHeader.vue'
import CpuCard from '../components/CpuCard.vue'
import DashboardToolbar from '../components/DashboardToolbar.vue'
import DiskCard from '../components/DiskCard.vue'
import HostInfoBar from '../components/HostInfoBar.vue'
import KpiTiles from '../components/KpiTiles.vue'
import MemoryCard from '../components/MemoryCard.vue'
import NetworkCard from '../components/NetworkCard.vue'
import UsageComparisonCard from '../components/UsageComparisonCard.vue'
import UsageTrendCard from '../components/UsageTrendCard.vue'
import UsersComparisonCard from '../components/UsersComparisonCard.vue'
import UsersTrendCard from '../components/UsersTrendCard.vue'
import { useDashboard } from '../composables/useDashboard'

const { t } = useI18n()

const {
  series,
  usage,
  users,
  system,
  processes,
  samples,
  rangeDays,
  live,
  loading,
  refreshing,
  failed,
  updatedAt,
  refresh,
} = useDashboard()
</script>

<template>
  <PageHeader :title="t('dashboard.title')" :subtitle="t('dashboard.subtitle')" />

  <DashboardToolbar
    v-model:range-days="rangeDays"
    v-model:live="live"
    :refreshing="refreshing"
    :failed="failed"
    :updated-at="updatedAt"
    class="mb-4"
    @refresh="refresh"
  />

  <ProgressBar v-if="loading" mode="indeterminate" style="height: 3px" class="mb-4" />
  <Message v-else-if="failed && !usage" severity="error" :closable="false" class="mb-4">
    {{ t('dashboard.loadFailedHint') }}
  </Message>

  <div class="dashboard">
    <KpiTiles :usage="usage" :users="users" :series="series" />

    <div class="dashboard__split">
      <UsageTrendCard :series="series" :usage="usage" :range-days="rangeDays" />
      <UsageComparisonCard :usage="usage" />
    </div>

    <div class="dashboard__split">
      <UsersTrendCard :series="series" :users="users" :range-days="rangeDays" />
      <UsersComparisonCard :users="users" />
    </div>

    <div class="dashboard__resources">
      <CpuCard :cpu="system?.cpu ?? null" :processes="processes?.cpu ?? []" :samples="samples" />
      <MemoryCard :memory="system?.memory ?? null" :processes="processes?.memory ?? []" :samples="samples" />
      <DiskCard :disk="system?.disk ?? null" />
    </div>

    <NetworkCard :network="system?.network ?? null" :samples="samples" />

    <HostInfoBar :host="system?.host ?? null" />
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.dashboard__split {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 1rem;
}
.dashboard__resources {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
  gap: 1rem;
  align-items: start;
}
@media (max-width: 1199px) {
  .dashboard__split {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
