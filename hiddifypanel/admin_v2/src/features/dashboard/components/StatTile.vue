<script lang="ts">
/** One row of a tile's hover card: a label and its value (main: the tile's own number, set apart) */
export interface TileDetail {
  label: string
  value: string
  main?: boolean
}

/** A reading against its reference, for the ring and compare faces */
export interface TileComparison {
  current: { label: string; amount: number; text: string }
  previous: { label: string; amount: number; text: string }
  /** The ring's caption: "78% of yesterday" */
  caption: string
}
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue'
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
    /** The face: a small chart (area, line, column, step, dots), a ring, or the bar pair against the previous period */
    kind?: string
    /** What the tile covers ("Last 30 Days"); ``live``: a pulsing dot, the tile is live */
    scope?: string
    live?: boolean
    comparison?: TileComparison
  }>(),
  { trend: undefined, details: () => [], sparkline: () => [], sparkLabels: () => [] },
)

const share = computed(() => {
  const c = props.comparison
  if (!c) return 0
  return c.previous.amount > 0 ? c.current.amount / c.previous.amount : c.current.amount > 0 ? 1 : 0
})
/** Past 100% the ring goes round again in a deeper shade, as Apple's rings do */
const RING = 2 * Math.PI * 15
const ringLaps = computed(() => [Math.min(1, share.value), Math.min(1, Math.max(0, share.value - 1))])
const percentText = computed(() => `${Math.round(share.value * 100)}%`)
const compareMax = computed(() => Math.max(props.comparison?.current.amount ?? 0, props.comparison?.previous.amount ?? 0, 1))

const esc = (text: string) => text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
/** The hover card: the tile's icon and name, then one row per number (label at the start, value at the end) */
const tip = computed(() => {
  if (!props.details.length) return undefined
  const rows = props.details.map((d) => `<div class="kpi-tip__row${d.main ? ' kpi-tip__row--main' : ''}"><dt>${esc(d.label)}</dt><dd>${esc(d.value)}</dd></div>`).join('')
  const value = `<div class="kpi-tip__card" style="--tip-accent:${esc(props.accent)}"><div class="kpi-tip__head"><span class="kpi-tip__icon"><i class="${esc(props.icon)}"></i></span>${esc(props.label)}</div><dl class="kpi-tip__rows">${rows}</dl></div>`
  return { value, escape: false, class: 'kpi-tip' }
})

/** Touch has no hover: a tap sends mouseenter and click together, and the click closes the card at once. There the
 *  card opens on focus (a tap on the focusable tile) and closes on blur (a tap elsewhere). */
const touch = typeof window !== 'undefined' && window.matchMedia('(hover: none)').matches
const tipArg = { position: 'top', event: touch ? 'focus' : 'hover' }

/** The card sits on <body> and PrimeVue only follows scrolling parents, not the page itself: on touch the open card
 *  stayed where it was while the tile scrolled away. A scroll now blurs the tile, which closes its card. */
let focused: HTMLElement | null = null
const blurOnScroll = () => focused?.blur()
/** A tap anywhere else closes the card too: the menu button and many others take no focus on iOS, so the tile kept
 *  its focus (and its card stayed over the opened menu) */
const blurOnTapOutside = (event: PointerEvent) => {
  if (focused && !focused.contains(event.target as Node)) focused.blur()
}
function onFocus(event: FocusEvent) {
  if (!touch) return
  focused = event.currentTarget as HTMLElement
  document.addEventListener('scroll', blurOnScroll, { capture: true, passive: true })
  document.addEventListener('pointerdown', blurOnTapOutside, { capture: true })
}
function onBlur() {
  focused = null
  document.removeEventListener('scroll', blurOnScroll, { capture: true })
  document.removeEventListener('pointerdown', blurOnTapOutside, { capture: true })
}
onBeforeUnmount(onBlur)
</script>

<template>
  <article v-tooltip:[tipArg]="tip" class="tile" :tabindex="touch && tip ? 0 : undefined" @focus="onFocus" @blur="onBlur" :style="{ '--tile-accent': accent }">
    <div class="tile__top">
      <div class="min-w-0">
        <p class="tile__label">{{ label }}</p>
        <p v-if="scope" class="tile__scope" :class="{ 'tile__scope--live': live }">
          <span v-if="live" class="tile__live-dot" /><i v-else class="pi pi-calendar" />
          <Transition name="tile-face" mode="out-in"
            ><span :key="scope">{{ scope }}</span></Transition
          >
        </p>
        <p class="tile__value">{{ value }}</p>
      </div>
      <div class="tile__aside">
        <slot name="tools" />
        <span class="tile__icon"><i :class="icon" /></span>
      </div>
    </div>
    <Transition name="tile-face" mode="out-in">
      <div v-if="kind === 'ring' && comparison" key="ring" class="tile__ring">
        <svg viewBox="0 0 36 36" class="tile__ring-svg" aria-hidden="true">
          <circle cx="18" cy="18" r="15" class="tile__ring-track" />
          <circle cx="18" cy="18" r="15" class="tile__ring-lap" :stroke-dasharray="`${RING * ringLaps[0]!} ${RING}`" />
          <circle v-if="ringLaps[1]! > 0" cx="18" cy="18" r="15" class="tile__ring-lap tile__ring-lap--2" :stroke-dasharray="`${RING * ringLaps[1]!} ${RING}`" />
        </svg>
        <div class="tile__ring-text">
          <b dir="ltr">{{ percentText }}</b>
          <span>{{ comparison.caption }}</span>
        </div>
      </div>
      <div v-else-if="kind === 'compare' && comparison" key="compare" class="tile__compare">
        <div v-for="(row, i) in [comparison.current, comparison.previous]" :key="i" class="tile__compare-row" :class="{ 'tile__compare-row--prev': i === 1 }">
          <span class="tile__compare-label">{{ row.label }}</span>
          <span class="tile__compare-track"><span class="tile__compare-fill" :style="{ width: `${Math.max(2, (row.amount / compareMax) * 100)}%` }" /></span>
          <b class="tile__compare-value" dir="ltr">{{ row.text }}</b>
        </div>
      </div>
      <Sparkline
        v-else-if="sparkline.length > 1"
        key="spark"
        :kind="(kind as 'area' | 'line' | 'column' | 'step' | 'dots' | undefined) ?? 'area'"
        :values="sparkline"
        :color="accent"
        :height="34"
        :labels="sparkLabels"
        :formatter="sparkFormatter ?? ((value: number) => String(value))"
        class="tile__spark"
      />
    </Transition>
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
  background: radial-gradient(120% 120% at 100% 0%, color-mix(in srgb, var(--tile-accent) 12%, transparent) 0%, transparent 55%), var(--p-content-background);
  box-shadow:
    0 1px 2px rgb(0 0 0 / 4%),
    0 10px 26px -20px rgb(15 23 42 / 35%);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}
/* A tap focuses the tile to open its card: no focus ring for that, only for the keyboard */
.tile:focus:not(:focus-visible) {
  outline: none;
}
@media (hover: hover) {
  .tile:hover {
    transform: translateY(-2px);
    box-shadow:
      0 1px 2px rgb(0 0 0 / 5%),
      0 20px 38px -24px rgb(15 23 42 / 45%);
  }
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
.tile__scope {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin: 0.2rem 0 0;
  overflow: hidden;
  font-size: 0.68rem;
  font-weight: 550;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.tile__scope span {
  overflow: hidden;
  text-overflow: ellipsis;
}
.tile__scope i {
  font-size: 0.62rem;
  color: var(--tile-accent);
}
.tile__scope--live {
  color: color-mix(in srgb, #22c55e 75%, var(--p-text-color));
}
.tile__live-dot {
  flex: none;
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 999px;
  background: #22c55e;
  animation: tile-live 2s infinite;
}
@keyframes tile-live {
  0% {
    box-shadow: 0 0 0 0 rgb(34 197 94 / 55%);
  }
  70%,
  100% {
    box-shadow: 0 0 0 0.35rem rgb(34 197 94 / 0%);
  }
}
.tile__aside {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  flex-shrink: 0;
}
/* the face against the previous period: a ring (past 100% a second lap) or a pair of bars */
.tile__ring {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 34px;
}
.tile__ring-svg {
  width: 2.6rem;
  height: 2.6rem;
  flex-shrink: 0;
  transform: rotate(-90deg);
}
.tile__ring-track,
.tile__ring-lap {
  fill: none;
  stroke-width: 4.5;
}
.tile__ring-track {
  stroke: color-mix(in srgb, var(--tile-accent) 16%, transparent);
}
.tile__ring-lap {
  stroke: var(--tile-accent);
  stroke-linecap: round;
  animation: tile-ring 0.9s cubic-bezier(0.32, 0.72, 0, 1) both;
  transition: stroke-dasharray 0.8s cubic-bezier(0.32, 0.72, 0, 1);
}
.tile__ring-lap--2 {
  stroke: color-mix(in srgb, var(--tile-accent) 62%, #000);
  animation-delay: 0.35s;
}
@keyframes tile-ring {
  from {
    stroke-dasharray: 0 100;
  }
}
.tile__ring-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}
.tile__ring-text b {
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
  color: var(--tile-accent);
}
html[dir='rtl'] .tile__ring-text b {
  text-align: end;
}
.tile__ring-text span {
  overflow: hidden;
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile__compare {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.3rem;
  min-height: 34px;
}
.tile__compare-row {
  display: grid;
  grid-template-columns: minmax(0, 3.6rem) minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.68rem;
}
.tile__compare-label {
  overflow: hidden;
  color: var(--p-text-muted-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile__compare-track {
  height: 0.42rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
  overflow: hidden;
}
.tile__compare-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--tile-accent);
  animation: tile-bar 0.8s cubic-bezier(0.32, 0.72, 0, 1) both;
  transition: width 0.6s cubic-bezier(0.32, 0.72, 0, 1);
}
.tile__compare-row--prev .tile__compare-fill {
  background: color-mix(in srgb, var(--tile-accent) 38%, transparent);
  animation-delay: 0.08s;
}
@keyframes tile-bar {
  from {
    width: 0;
  }
}
.tile__compare-value {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.tile-face-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.42s cubic-bezier(0.32, 0.72, 0, 1);
}
.tile-face-leave-active {
  transition: opacity 0.12s ease;
}
.tile-face-enter-from {
  opacity: 0;
  transform: translateY(5px);
}
.tile-face-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .tile__ring-lap,
  .tile__compare-fill {
    animation: none;
  }
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
  box-shadow:
    0 18px 40px -16px rgb(15 23 42 / 35%),
    0 2px 6px rgb(15 23 42 / 6%);
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
