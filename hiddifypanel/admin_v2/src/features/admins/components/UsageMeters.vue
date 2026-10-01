<template>
  <div class="meters" :class="{ 'meters--large': large }">
    <div v-for="row in rows" :key="row.key" class="meter" :class="`meter--${row.tone}`" :title="row.title">
      <span class="meter__label"><i :class="row.icon" />{{ row.label }}</span>
      <div
        class="meter__bar"
        role="meter"
        :aria-label="row.label"
        :aria-valuenow="row.used"
        :aria-valuemin="0"
        :aria-valuemax="row.max ?? undefined"
        :aria-valuetext="row.text"
      >
        <!-- Text over the empty part -->
        <span class="meter__text" dir="ltr">{{ row.text }}</span>
        <!-- Same text, clipped to the filled part, in the fill's contrast color -->
        <span class="meter__fill" :style="{ width: `${row.percent}%` }">
          <span class="meter__text meter__text--on-fill" dir="ltr">{{ row.text }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatCount, formatGb } from '@/shared/utils/format-metrics'
import { meterTone, type AdminLimits, type AdminStats } from '@/features/admins/api'

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
    tone: meterTone(row.used, row.max),
    label: t(`admins.meter.${row.key}`),
    title: t(`admins.meter.${row.key}Hint`),
    text: row.key === 'traffic' ? trafficText(row.used, row.max) : countText(row.used, row.max),
    // A sliver stays visible once anything is used, so 1 of 1000 still shows.
    percent: row.max ? (row.used > 0 ? Math.max(4, Math.min(100, (row.used * 100) / row.max)) : 0) : 0,
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
  --fill: linear-gradient(90deg, #34d399, #10b981 55%, #059669);
  --fill-glow: rgba(16, 185, 129, 0.45);
  --on-fill: #fff;
  display: grid;
  grid-template-columns: 5.25rem minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
}
.meter--warn {
  --fill: linear-gradient(90deg, #fde047, #facc15 50%, #f59e0b);
  --fill-glow: rgba(245, 158, 11, 0.45);
  --on-fill: #422006;
}
.meter--danger {
  --fill: linear-gradient(90deg, #fb923c, #f43f5e 55%, #e11d48);
  --fill-glow: rgba(244, 63, 94, 0.5);
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

.meter__bar {
  /* cqw below = this bar's width, so the clipped text lines up with the one under it. */
  container-type: inline-size;
  position: relative;
  height: 1.3rem;
  border-radius: 999px;
  overflow: hidden;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.12);
}
.meter--none .meter__bar {
  background: repeating-linear-gradient(
    -45deg,
    color-mix(in srgb, var(--p-primary-color) 7%, transparent) 0 6px,
    color-mix(in srgb, var(--p-primary-color) 12%, transparent) 6px 12px
  );
}
.meter__fill {
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  overflow: hidden;
  border-radius: inherit;
  background: var(--fill);
  box-shadow: 0 0 10px -2px var(--fill-glow);
  transition: width 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
/* Glossy top highlight */
.meter__fill::before {
  content: '';
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0));
}
/* Slow sheen across the fill */
.meter__fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 20%, rgba(255, 255, 255, 0.35) 45%, transparent 70%);
  transform: translateX(-100%);
  animation: meter-sheen 3.2s ease-in-out infinite;
}
.meter__text {
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 100cqw;
  display: grid;
  place-items: center;
  font-size: 0.72rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
  white-space: nowrap;
  color: var(--p-text-color);
}
.meter__text--on-fill {
  z-index: 1;
  color: var(--on-fill);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.18);
}
.meter--warn .meter__text--on-fill {
  text-shadow: none;
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
.meters--large .meter__bar {
  height: 1.75rem;
}
.meters--large .meter__text {
  font-size: 0.85rem;
}
@media (min-width: 861px) {
  .meters--large {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@keyframes meter-sheen {
  0%,
  35% {
    transform: translateX(-100%);
  }
  75%,
  100% {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .meter__fill {
    transition: none;
  }
  .meter__fill::after {
    animation: none;
    display: none;
  }
}
</style>
