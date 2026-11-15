<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import TelegramPrompt from '@/shared/components/TelegramPrompt.vue'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import PageHeader from '@/shared/components/PageHeader.vue'
import DashboardToolbar from '../components/DashboardToolbar.vue'
import KpiTiles from '../components/KpiTiles.vue'
import ConfigHealthCard from '../components/ConfigHealthCard.vue'
import NodeHealthCard from '../components/NodeHealthCard.vue'
import { isSuperAdmin } from '@/core/panelShell'
import UsageComparisonCard from '../components/UsageComparisonCard.vue'
import UsageTrendCard from '../components/UsageTrendCard.vue'
import UsersComparisonCard from '../components/UsersComparisonCard.vue'
import UsersTrendCard from '../components/UsersTrendCard.vue'
import { useDashboard } from '../composables/useDashboard'
import { computed } from 'vue'
import { daysBetween, shortDay } from '../utils/date-range'

const { t, locale } = useI18n()

const { series, previousSeries, usage, users, nodeSamples, rangeDays, customRange, childId, nodes, nodeStats, live, loading, refreshing, failed, updatedAt, refresh } = useDashboard(locale.value)

/** The period in days and in words, for the charts' ticks and subtitles */
const periodDays = computed(() => (customRange.value ? daysBetween(customRange.value.start, customRange.value.end) : rangeDays.value))
const periodLabel = computed(() => {
  const range = customRange.value
  if (!range) return t('dashboard.lastNDays', { days: rangeDays.value })
  if (range.preset) return t(`dashboard.period.presets.${range.preset}`)
  const days = t('dashboard.nDays', { days: periodDays.value })
  return range.start === range.end ? shortDay(range.start, locale.value) : `${shortDay(range.start, locale.value)} – ${shortDay(range.end, locale.value)} · ${days}`
})
</script>

<template>
  <PageHeader :title="t('dashboard.title')" :subtitle="t('dashboard.subtitle')" />
  <TelegramPrompt />

  <DashboardToolbar
    v-model:range-days="rangeDays"
    v-model:custom-range="customRange"
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
    <KpiTiles :users="users" :series="series" :previous-series="previousSeries" :period-label="periodLabel" />

    <div class="dashboard__split">
      <UsageTrendCard :series="series" :usage="usage" :range-days="periodDays" :period-label="periodLabel" :nodes="nodes" :stacked="childId === null" />
      <UsageComparisonCard :usage="usage" :series="series" :nodes="nodes" :stacked="childId === null" />
    </div>

    <div class="dashboard__split">
      <UsersTrendCard :series="series" :users="users" :range-days="periodDays" :period-label="periodLabel" :nodes="nodes" :stacked="childId === null" />
      <UsersComparisonCard :users="users" :series="series" :nodes="nodes" :stacked="childId === null" />
    </div>

    <!-- Every config tested from the server every 6 hours (super admins: it runs cores on the server) -->
    <ConfigHealthCard v-if="isSuperAdmin" />

    <NodeHealthCard :nodes="nodeStats" :history="nodeSamples" :child-id="childId" @renamed="refresh" />
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
