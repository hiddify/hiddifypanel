<script lang="ts">
/** One row of a tile's hover card: a label and its value (main: the tile's own number, set apart) */
export interface TileDetail {
  label: string
  value: string
  main?: boolean
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import Sparkline from './Sparkline.vue'
import TrendChip from './TrendChip.vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string
    icon: string
    accent: string
    caption?: string
    trend?: number | null
    trendLabel?: string
    details?: TileDetail[]
    sparkline?: number[]
    sparkLabels?: string[]
    sparkFormatter?: (value: number) => string
  }>(),
  { trend: undefined, details: () => [], sparkline: () => [], sparkLabels: () => [] },
)

const esc = (text: string) => text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
/** The hover card: the tile's icon and name, then one row per number (label at the start, value at the end) */
const tip = computed(() => {
  if (!props.details.length) return undefined
  const rows = props.details
    .map((d) => `<div class="kpi-tip__row${d.main ? ' kpi-tip__row--main' : ''}"><dt>${esc(d.label)}</dt><dd>${esc(d.value)}</dd></div>`)
    .join('')
  const value = `<div class="kpi-tip__card" style="--tip-accent:${esc(props.accent)}"><div class="kpi-tip__head"><span class="kpi-tip__icon"><i class="${esc(props.icon)}"></i></span>${esc(props.label)}</div><dl class="kpi-tip__rows">${rows}</dl></div>`
  return { value, escape: false, class: 'kpi-tip' }
})
</script>

<template>
  <article
    v-tooltip.top="tip"
    class="tile"
    :class="{ 'tile--hoverable': details.length }"
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

<style>
/* The tiles' hover card (PrimeVue puts the tooltip in <body>, so not scoped): a light card in the page's colours, the
   tile's own colour on its icon and top edge, the numbers as label / value rows that line up */
.p-tooltip.kpi-tip {
  max-width: 19rem;
}
.p-tooltip.kpi-tip .p-tooltip-text {
  padding: 0;
  border-radius: 14px;
  background: var(--p-content-background);
  color: var(--p-text-color);
  border: 1px solid var(--p-content-border-color);
  box-shadow: 0 18px 40px -16px rgb(15 23 42 / 35%), 0 2px 6px rgb(15 23 42 / 6%);
  white-space: normal;
  overflow: hidden;
}
.p-tooltip.kpi-tip.p-tooltip-top .p-tooltip-arrow {
  border-top-color: var(--p-content-border-color);
}
.kpi-tip__card {
  min-width: 14rem;
  border-top: 3px solid var(--tip-accent);
}
.kpi-tip__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.85rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.kpi-tip__icon {
  display: inline-grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 7px;
  font-size: 0.75rem;
  color: var(--tip-accent);
  background: color-mix(in srgb, var(--tip-accent) 14%, transparent);
}
.kpi-tip__rows {
  margin: 0;
  padding: 0 0.85rem 0.55rem;
}
.kpi-tip__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 0.38rem 0;
  border-top: 1px solid var(--p-content-border-color);
  font-size: 0.82rem;
}
.kpi-tip__row dt {
  color: var(--p-text-muted-color);
}
.kpi-tip__row dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
/* The tile's own number, first and set apart */
.kpi-tip__row--main {
  border-top: 0;
  padding-bottom: 0.5rem;
}
.kpi-tip__row--main dt {
  color: var(--p-text-color);
  font-weight: 600;
}
.kpi-tip__row--main dd {
  font-size: 0.95rem;
  color: var(--tip-accent);
}
</style>
