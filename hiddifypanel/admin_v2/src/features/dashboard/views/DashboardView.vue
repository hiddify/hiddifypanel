<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import PageHeader from '@/shared/components/PageHeader.vue'
import DashboardToolbar from '../components/DashboardToolbar.vue'
import HostInfoBar from '../components/HostInfoBar.vue'
import KpiTiles from '../components/KpiTiles.vue'
import NetworkCard from '../components/NetworkCard.vue'
import NodeHealthCard from '../components/NodeHealthCard.vue'
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
  samples,
  nodeSamples,
  rangeDays,
  childId,
  nodes,
  nodeStats,
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
    v-model:child-id="childId"
    v-model:live="live"
    :nodes="nodes"
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
      <UsageTrendCard
        :series="series"
        :usage="usage"
        :range-days="rangeDays"
        :nodes="nodes"
        :stacked="childId === null"
      />
      <UsageComparisonCard :usage="usage" />
    </div>

    <div class="dashboard__split">
      <UsersTrendCard :series="series" :users="users" :range-days="rangeDays" />
      <UsersComparisonCard :users="users" />
    </div>

    <NodeHealthCard :nodes="nodeStats" :history="nodeSamples" />

    <NetworkCard
      :network="system?.network ?? null"
      :samples="samples"
      :nodes="nodeStats"
      :node-samples="nodeSamples"
    />

    <HostInfoBar v-if="childId !== null || nodeStats.length <= 1" :host="system?.host ?? null" />
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
@media (max-width: 1199px) {
  .dashboard__split {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 767px) {
  .dashboard {
    gap: 0.75rem;
  }
}
</style>
