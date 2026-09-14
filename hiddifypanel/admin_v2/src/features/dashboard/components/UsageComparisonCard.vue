<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardUsage } from '@/core/api/generated'
import { formatBytes } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import TrendChip from './TrendChip.vue'

const props = defineProps<{ usage: DashboardUsage | null }>()

const { t } = useI18n()

/** Same-scale comparison of the four readings admins check most. */
const buckets = computed(() => [
  { key: 'monthlyAverage', value: props.usage?.averages.daily_month ?? 0 },
  { key: 'weeklyAverage', value: props.usage?.averages.daily_week ?? 0 },
  { key: 'yesterday', value: props.usage?.totals.yesterday ?? 0 },
  { key: 'today', value: props.usage?.totals.today ?? 0 },
])

const labels = computed(() => buckets.value.map((bucket) => t(`dashboard.${bucket.key}`)))

const chartSeries = computed(() => [
  {
    label: t('dashboard.dailyUsage'),
    values: buckets.value.map((bucket) => bucket.value),
    color: SERIES.usage,
    type: 'bar' as const,
  },
])
</script>

<template>
  <DashCard
    :title="t('dashboard.usageComparison')"
    :subtitle="t('dashboard.usageComparisonHint')"
    icon="pi pi-chart-line"
    :accent="SERIES.usageAvg"
    padded
  >
    <MetricChart
      :labels="labels"
      :series="chartSeries"
      type="bar"
      :value-formatter="(value: number) => formatBytes(value, 0)"
      :height="216"
      :legend="false"
      :max-x-ticks="4"
    />
    <template #footer>
      <div class="comparison-footer">
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsYesterday') }}</span>
          <TrendChip :value="usage?.trends.day ?? null" />
        </div>
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsPreviousWeek') }}</span>
          <TrendChip :value="usage?.trends.week ?? null" />
        </div>
        <div class="comparison-footer__row">
          <span>{{ t('dashboard.vsPreviousMonth') }}</span>
          <TrendChip :value="usage?.trends.month ?? null" />
        </div>
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.comparison-footer {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.comparison-footer__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
</style>
