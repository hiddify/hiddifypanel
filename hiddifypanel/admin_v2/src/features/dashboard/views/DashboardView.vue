<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import PageHeader from '@/shared/components/PageHeader.vue'
import DashboardToolbar from '../components/DashboardToolbar.vue'
import KpiTiles from '../components/KpiTiles.vue'
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
      <UsageComparisonCard :usage="usage" :series="series" :nodes="nodes" :stacked="childId === null" />
    </div>

    <div class="dashboard__split">
      <UsersTrendCard
        :series="series"
        :users="users"
        :range-days="rangeDays"
        :nodes="nodes"
        :stacked="childId === null"
      />
      <UsersComparisonCard :users="users" :series="series" :nodes="nodes" :stacked="childId === null" />
    </div>

    <NodeHealthCard :nodes="nodeStats" :history="nodeSamples" :child-id="childId" />
  </div>
</template>

<style scoped>
/* Cards size against the space left beside the sidebar, not the viewport. */
.dashboard {
  container: dashboard / inline-size;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.dashboard__split {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
}
@container dashboard (min-width: 64rem) {
  .dashboard__split {
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  }
}
@media (max-width: 767px) {
  .dashboard,
  .dashboard__split {
    gap: 0.75rem;
  }
}
</style>
