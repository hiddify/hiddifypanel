<script setup lang="ts">
import Sparkline from './Sparkline.vue'
import TrendChip from './TrendChip.vue'

withDefaults(
  defineProps<{
    label: string
    value: string
    icon: string
    accent: string
    caption?: string
    trend?: number | null
    trendLabel?: string
    tooltip?: string
    sparkline?: number[]
    sparkLabels?: string[]
    sparkFormatter?: (value: number) => string
  }>(),
  { trend: undefined, sparkline: () => [], sparkLabels: () => [] },
)
</script>

<template>
  <article
    v-tooltip.top="tooltip ? { value: tooltip } : undefined"
    class="tile"
    :class="{ 'tile--hoverable': tooltip }"
    :style="{ '--tile-accent': accent }"
  >
    <div class="tile__top">
      <div class="min-w-0">
        <p class="tile__label">{{ label }}</p>
        <p class="tile__value">{{ value }}</p>
      </div>
      <span class="tile__icon"><i :class="icon" /></span>
    </div>
    <Sparkline
      v-if="sparkline.length > 1"
      :values="sparkline"
      :color="accent"
      :height="34"
      :labels="sparkLabels"
      :formatter="sparkFormatter ?? ((value: number) => String(value))"
      class="tile__spark"
    />
    <div class="tile__bottom">
      <TrendChip v-if="trend !== undefined" :value="trend ?? null" :label="trendLabel" />
      <span v-if="caption" class="tile__caption">{{ caption }}</span>
    </div>
  </article>
</template>

<style scoped>
.tile {
  --tile-accent: var(--p-primary-color);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.1rem 1.25rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  background:
    radial-gradient(120% 120% at 100% 0%, color-mix(in srgb, var(--tile-accent) 12%, transparent) 0%, transparent 55%),
    var(--p-content-background);
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%), 0 10px 26px -20px rgb(15 23 42 / 35%);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
@media (hover: hover) {
  .tile:hover {
    transform: translateY(-2px);
    box-shadow: 0 1px 2px rgb(0 0 0 / 5%), 0 20px 38px -24px rgb(15 23 42 / 45%);
  }
}
.tile--hoverable {
  cursor: help;
}
.tile__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}
.tile__label {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.tile__value {
  margin: 0.3rem 0 0;
  font-size: 1.65rem;
  font-weight: 700;
  line-height: 1.15;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.tile__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 0.85rem;
  color: #fff;
  background: linear-gradient(135deg, var(--tile-accent), color-mix(in srgb, var(--tile-accent) 60%, #000));
  box-shadow: 0 8px 18px -10px color-mix(in srgb, var(--tile-accent) 70%, transparent);
}
.tile__spark {
  margin: 0 -0.25rem;
}
.tile__bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: auto;
}
.tile__caption {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
@media (max-width: 767px) {
  .tile {
    padding: 0.9rem 1rem;
  }
  .tile__top {
    gap: 0.5rem;
  }
  .tile__value {
    font-size: 1.3rem;
  }
  .tile__icon {
    width: 2rem;
    height: 2rem;
    border-radius: 0.7rem;
    font-size: 0.85rem;
  }
}
</style>
