<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardDisk } from '@/core/api/generated'
import { formatGb } from '@/shared/utils/format-metrics'
import { SERIES } from '../composables/useChartTheme'
import MetricBar from './MetricBar.vue'
import ResourceCard from './ResourceCard.vue'

const props = defineProps<{ disk: DashboardDisk | null }>()

const { t } = useI18n()

const percent = computed(() => props.disk?.percent ?? 0)

const headline = computed(() =>
  props.disk ? `${formatGb(props.disk.used_gb, 1)} / ${formatGb(props.disk.total_gb, 1)}` : '—',
)

const caption = computed(() => {
  if (!props.disk) return undefined
  const hiddify = props.disk.hiddify_gb
  const free = `${t('dashboard.free')} ${formatGb(props.disk.free_gb, 1)}`
  return hiddify === null ? free : `${free} · ${t('dashboard.hiddify')} ${formatGb(hiddify, 1)}`
})

interface BreakdownRow {
  label: string
  percent: number
  value: string
  color: string
}

const breakdown = computed<BreakdownRow[]>(() => {
  const disk = props.disk
  if (!disk) return []
  const rows: BreakdownRow[] = [
    { label: t('dashboard.used'), percent: disk.percent, value: formatGb(disk.used_gb, 1), color: SERIES.disk },
    {
      label: t('dashboard.free'),
      percent: disk.total_gb ? (disk.free_gb / disk.total_gb) * 100 : 0,
      value: formatGb(disk.free_gb, 1),
      color: SERIES.online,
    },
  ]
  if (disk.hiddify_gb !== null) {
    rows.push({
      label: t('dashboard.hiddify'),
      percent: disk.total_gb ? (disk.hiddify_gb / disk.total_gb) * 100 : 0,
      value: formatGb(disk.hiddify_gb, 1),
      color: SERIES.users,
    })
  }
  return rows
})
</script>

<template>
  <ResourceCard
    :title="t('dashboard.disk')"
    icon="pi pi-database"
    :accent="SERIES.disk"
    :percent="percent"
    :value="headline"
    :caption="caption"
  >
    <template #detail>
      <div class="disk-detail">
        <MetricBar
          v-for="row in breakdown"
          :key="row.label"
          :label="row.label"
          :percent="row.percent"
          :value="row.value"
          :color="row.color"
          compact
        />
      </div>
    </template>
  </ResourceCard>
</template>

<style scoped>
.disk-detail {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
</style>
