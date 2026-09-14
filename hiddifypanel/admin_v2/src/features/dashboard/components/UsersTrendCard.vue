<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDailyPoint, DashboardUsers } from '@/core/api/generated'
import { formatDayLabel } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import { rollingAverage } from '../utils/series'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import MiniStat from './MiniStat.vue'

const props = defineProps<{
  series: DashboardDailyPoint[]
  users: DashboardUsers | null
  rangeDays: number
}>()

const { t, locale } = useI18n()

const labels = computed(() => props.series.map((point) => formatDayLabel(point.date, locale.value)))
const values = computed(() => props.series.map((point) => point.online))

const chartSeries = computed(() => [
  { label: t('dashboard.dailyOnline'), values: values.value, color: SERIES.users, type: 'line' as const, area: true },
  {
    label: t('dashboard.rollingAverage'),
    values: rollingAverage(values.value, 7),
    color: SERIES.online,
    type: 'line' as const,
    dashed: true,
  },
])
</script>

<template>
  <DashCard
    :title="t('dashboard.usersTrend')"
    :subtitle="t('dashboard.lastNDays', { days: rangeDays })"
    icon="pi pi-users"
    :accent="SERIES.users"
    padded
  >
    <MetricChart
      :labels="labels"
      :series="chartSeries"
      type="line"
      :value-formatter="(value: number) => String(Math.round(value))"
      :height="280"
      :max-x-ticks="rangeDays > 60 ? 8 : 12"
    />
    <template #footer>
      <div class="users-footer">
        <MiniStat
          :label="t('dashboard.totalUsers')"
          :value="String(users?.total ?? 0)"
          icon="pi pi-id-card"
          :accent="SERIES.users"
        />
        <MiniStat
          :label="t('dashboard.enabledUsers')"
          :value="String(users?.enabled ?? 0)"
          icon="pi pi-check-circle"
          :accent="SERIES.online"
        />
        <MiniStat
          :label="t('dashboard.monthlyAverage')"
          :value="String(users?.averages.daily_month ?? 0)"
          icon="pi pi-calendar"
          :accent="SERIES.download"
        />
        <MiniStat
          :label="t('dashboard.weeklyAverage')"
          :value="String(users?.averages.daily_week ?? 0)"
          icon="pi pi-calendar-clock"
          :accent="SERIES.usageAvg"
        />
      </div>
    </template>
  </DashCard>
</template>

<style scoped>
.users-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
  gap: 0.75rem 1.25rem;
}
</style>
