<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardUsers } from '@/core/api/generated'
import { SERIES } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'
import MetricChart from './MetricChart.vue'
import ResourceGauge from './ResourceGauge.vue'

const props = defineProps<{ users: DashboardUsers | null }>()

const { t } = useI18n()

const buckets = computed(() => [
  { key: 'monthUsers', value: props.users?.online.month ?? 0 },
  { key: 'weekUsers', value: props.users?.online.week ?? 0 },
  { key: 'yesterday', value: props.users?.online.yesterday ?? 0 },
  { key: 'today', value: props.users?.online.today ?? 0 },
  { key: 'onlineNow', value: props.users?.online.m5 ?? 0 },
])

const labels = computed(() => buckets.value.map((bucket) => t(`dashboard.${bucket.key}`)))

const chartSeries = computed(() => [
  {
    label: t('dashboard.onlineUsers'),
    values: buckets.value.map((bucket) => bucket.value),
    color: SERIES.online,
    type: 'bar' as const,
  },
])

const onlineShare = computed(() => {
  const total = props.users?.total ?? 0
  if (!total) return 0
  return ((props.users?.online.m5 ?? 0) / total) * 100
})
</script>

<template>
  <DashCard
    :title="t('dashboard.usersComparison')"
    :subtitle="t('dashboard.usersComparisonHint')"
    icon="pi pi-user-plus"
    :accent="SERIES.online"
    padded
  >
    <div class="users-compare">
      <div class="users-compare__gauge">
        <ResourceGauge
          :percent="onlineShare"
          :color="SERIES.online"
          :value="`${users?.online.m5 ?? 0}/${users?.total ?? 0}`"
          :caption="t('dashboard.onlineNow')"
          :auto-color="false"
          :size="110"
        />
        <p class="users-compare__hint">{{ t('dashboard.inFiveMinutes') }}</p>
      </div>
      <MetricChart
        class="users-compare__chart"
        :labels="labels"
        :series="chartSeries"
        type="bar"
        :value-formatter="(value: number) => String(Math.round(value))"
        :height="216"
        :legend="false"
        :max-x-ticks="5"
      />
    </div>
  </DashCard>
</template>

<style scoped>
.users-compare {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.users-compare__gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}
.users-compare__hint {
  margin: 0;
  font-size: 0.7rem;
  text-align: center;
  color: var(--p-text-muted-color);
}
.users-compare__chart {
  flex: 1;
  min-width: 0;
}
@media (max-width: 575px) {
  .users-compare {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
