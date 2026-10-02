<template>
  <div class="meters" :class="{ 'meters--large': large }">
    <div v-for="row in rows" :key="row.key" class="meter" :title="row.title">
      <span class="meter__label"><i :class="row.icon" />{{ row.label }}</span>
      <MeterBar :used="row.used" :max="row.max" :text="row.text" :label="row.label" :size="large ? 'lg' : 'md'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import MeterBar from '@/shared/components/MeterBar.vue'
import { formatCount, formatGb } from '@/shared/utils/format-metrics'
import type { AdminLimits, AdminStats } from '@/features/admins/api'

const props = defineProps<{
  stats: AdminStats
  /** Null: no limits (super admin). */
  limits: AdminLimits | null
  large?: boolean
}>()

const { t } = useI18n()

function gb(value: number): string {
  return formatGb(value, value >= 100 ? 0 : 1)
}

/** `1.2 / 10 GB`: the unit once when both sides share it. */
function trafficText(used: number, max: number | null | undefined): string {
  const a = gb(used)
  if (!max) return `${a} / ∞`
  const b = gb(max)
  const unitA = a.split(' ')[1]
  return unitA && unitA === b.split(' ')[1] ? `${a.split(' ')[0]} / ${b}` : `${a} / ${b}`
}

function countText(used: number, max: number | null | undefined): string {
  return `${formatCount(used)} / ${max ? formatCount(max) : '∞'}`
}

const rows = computed(() =>
  (
    [
      { key: 'online', icon: 'pi pi-wifi', used: props.stats.online, max: props.limits?.max_online_users },
      { key: 'active', icon: 'pi pi-bolt', used: props.stats.active, max: props.limits?.max_active_users },
      { key: 'total', icon: 'pi pi-users', used: props.stats.total, max: props.limits?.max_users },
      { key: 'traffic', icon: 'pi pi-arrow-right-arrow-left', used: props.stats.usage_GB, max: props.limits?.max_total_usage_GB },
    ] as const
  ).map((row) => ({
    ...row,
    label: t(`admins.meter.${row.key}`),
    title: t(`admins.meter.${row.key}Hint`),
    text: row.key === 'traffic' ? trafficText(row.used, row.max) : countText(row.used, row.max),
  })),
)
</script>

<style scoped>
/* Phones: one meter per line (label beside the bar); tablets: two per row; desktop: side by side (label above). */
.meters {
  display: grid;
  gap: 0.45rem;
  min-width: 11.5rem;
}
.meter {
  display: grid;
  grid-template-columns: 5.25rem minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
}
.meter__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meter__label i {
  font-size: 0.7rem;
}

@media (min-width: 480px) and (max-width: 860px) {
  .meters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem 1rem;
  }
  .meter {
    grid-template-columns: 4.5rem minmax(0, 1fr);
  }
}
@media (min-width: 861px) {
  .meters {
    grid-template-columns: repeat(4, minmax(6rem, 1fr));
    gap: 0.4rem 0.75rem;
  }
  .meter {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}

/* Large (My account) */
.meters--large {
  gap: 0.9rem 1.5rem;
}
.meters--large .meter {
  grid-template-columns: 1fr;
  gap: 0.4rem;
  font-size: 0.9rem;
}
@media (min-width: 861px) {
  .meters--large {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

</style>
