<script setup lang="ts">
/**
 * The style button of a tile and its small window: the chart's type (lines, fills, bars, candles…, each drawn as a
 * tiny preview), its colour theme, and the grid / average switches. Every change shows on the chart at once.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ToggleSwitch from 'primevue/toggleswitch'
import { AUTO_SWATCH, PALETTES, TYPE_GROUPS, type ChartStyle } from '../composables/useChartStyle'
import ChartTypeIcon from './ChartTypeIcon.vue'
import DashSheet from './DashSheet.vue'

const props = withDefaults(
  defineProps<{
    /** The types this tile can be drawn as */
    types: readonly string[]
    /** The colour the "auto" theme draws previews in (the tile's own accent) */
    accent?: string
    toggles?: readonly ('grid' | 'average')[]
    size?: 'normal' | 'small'
  }>(),
  { accent: '#6366f1', toggles: () => ['grid', 'average'], size: 'normal' },
)
const style = defineModel<ChartStyle>({ required: true })
const emit = defineEmits<{ reset: [] }>()
const { t } = useI18n()

const sheet = ref<InstanceType<typeof DashSheet> | null>(null)
const opened = ref(false)
function open(event: Event) {
  opened.value = true
  // the tile's own card (its numbers, opened on hover or a tap) closes: the window takes its place
  const owner = (event.currentTarget as HTMLElement | null)?.closest<HTMLElement>('[data-pd-tooltip="true"], .tile')
  if (owner) {
    owner.dispatchEvent(new Event('mouseleave'))
    owner.dispatchEvent(new Event('blur'))
    if (owner.contains(document.activeElement)) (document.activeElement as HTMLElement).blur()
  }
  sheet.value?.open(event)
}

const groups = computed(() => TYPE_GROUPS.map((group) => ({ key: group.key, types: group.types.filter((type) => props.types.includes(type)) })).filter((group) => group.types.length))
const previewColor = computed(() => PALETTES.find((p) => p.id === style.value.palette)?.colors[0] ?? props.accent)
/** A palette as a soft mesh of its colours, like an iOS wallpaper swatch */
const swatch = (id: string) => {
  const c = id === 'auto' ? AUTO_SWATCH : PALETTES.find((p) => p.id === id)!.colors
  return [
    `radial-gradient(circle at 22% 20%, ${c[0]} 0, transparent 62%)`,
    `radial-gradient(circle at 82% 28%, ${c[1]} 0, transparent 60%)`,
    `radial-gradient(circle at 28% 86%, ${c[2]} 0, transparent 62%)`,
    `radial-gradient(circle at 86% 84%, ${c[3] ?? c[0]} 0, transparent 58%)`,
    c[0],
  ].join(', ')
}
/** Every type in one grid, in the groups' order (the preview names the group) */
const flatTypes = computed(() => groups.value.flatMap((group) => group.types))
/** The chosen type and the group it sits in, for the live preview */
const chosenGroup = computed(() => groups.value.find((group) => group.types.includes(style.value.type))?.key)

const set = (patch: Partial<ChartStyle>) => (style.value = { ...style.value, ...patch })
</script>

<template>
  <button type="button" class="csb" :class="[`csb--${size}`, { 'csb--open': opened }]" :aria-label="t('dashboard.chartStyle.title')" :title="t('dashboard.chartStyle.title')" aria-haspopup="dialog" @click.stop="open">
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M3 15.5 7.5 10l3 3L17 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="16.4" cy="14.6" r="2.6" :fill="previewColor" />
    </svg>
  </button>

  <DashSheet ref="sheet" :title="t('dashboard.chartStyle.title')" @hide="opened = false">
    <template #lead>
      <button type="button" class="dsh-round" :aria-label="t('dashboard.chartStyle.reset')" :title="t('dashboard.chartStyle.reset')" @click="emit('reset')">
        <i class="pi pi-replay" />
      </button>
    </template>
    <div class="cs" :style="{ '--cs-tint': previewColor }">
      <!-- the chosen type, alive and large, in the chosen colours -->
      <div v-if="chosenGroup" class="cs__hero">
        <div class="cs__hero-text">
          <Transition name="cs-swap" mode="out-in">
            <b :key="style.type">{{ t(`dashboard.chartStyle.types.${style.type}`) }}</b>
          </Transition>
          <span>{{ t(`dashboard.chartStyle.groups.${chosenGroup}`) }}</span>
        </div>
        <Transition name="cs-swap" mode="out-in">
          <div :key="`${style.type}-${style.palette}`" class="cs__hero-chart"><ChartTypeIcon :type="style.type" :color="previewColor" live /></div>
        </Transition>
      </div>

      <section v-if="flatTypes.length" class="cs__group">
        <h4 class="cs__label">{{ t('dashboard.chartStyle.type') }}</h4>
        <div class="cs__types">
          <button v-for="type in flatTypes" :key="type" type="button" class="cs__type" :class="{ 'cs__type--on': style.type === type }" :aria-pressed="style.type === type" @click="set({ type })">
            <span class="cs__preview"><ChartTypeIcon :type="type" :color="previewColor" :live="style.type === type" /></span>
            <span class="cs__name">{{ t(`dashboard.chartStyle.types.${type}`) }}</span>
          </button>
        </div>
      </section>

      <section class="cs__group">
        <h4 class="cs__label">{{ t('dashboard.chartStyle.colors') }}</h4>
        <div class="cs__swatches" role="radiogroup" :aria-label="t('dashboard.chartStyle.colors')">
          <button
            v-for="palette in PALETTES"
            :key="palette.id"
            type="button"
            role="radio"
            class="cs__swatch"
            :class="{ 'cs__swatch--on': style.palette === palette.id }"
            :aria-checked="style.palette === palette.id"
            :title="t(`dashboard.chartStyle.palettes.${palette.id}`)"
            @click="set({ palette: palette.id })"
          >
            <span class="cs__chip" :style="{ background: swatch(palette.id) }">
              <i v-if="style.palette === palette.id" class="pi pi-check" />
            </span>
            <span class="cs__swatch-name">{{ t(`dashboard.chartStyle.palettes.${palette.id}`) }}</span>
          </button>
        </div>
      </section>

      <section v-if="toggles.length" class="cs__list">
        <label v-if="toggles.includes('grid')" class="cs__row">
          <span class="cs__row-icon" style="--c: #8e8e93"><i class="pi pi-th-large" /></span>
          <span class="cs__row-name">{{ t('dashboard.chartStyle.grid') }}</span>
          <ToggleSwitch :model-value="style.grid" @update:model-value="(grid: boolean) => set({ grid })" />
        </label>
        <label v-if="toggles.includes('average')" class="cs__row">
          <span class="cs__row-icon" style="--c: #ff9f0a"><i class="pi pi-minus" /></span>
          <span class="cs__row-name">{{ t('dashboard.chartStyle.average') }}</span>
          <ToggleSwitch :model-value="style.average" @update:model-value="(average: boolean) => set({ average })" />
        </label>
      </section>
    </div>
  </DashSheet>
</template>

<style scoped>
.csb {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.15rem;
  height: 2.05rem;
  border: 0;
  border-radius: 0.7rem;
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
  box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 8%, transparent);
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.csb svg {
  width: 1.05rem;
  height: 1.05rem;
}
.csb--small {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 0.55rem;
}
.csb--small svg {
  width: 0.9rem;
  height: 0.9rem;
}
.csb:hover,
.csb--open {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-text-color) 11%, transparent);
}
.csb:active {
  transform: scale(0.9);
}
.csb:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}

.cs {
  --cti-hollow: var(--p-content-background);
  display: flex;
  flex-direction: column;
  gap: 1.05rem;
}
/* the live preview: the chosen type large, on a wash of its colour */
.cs__hero {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 5.6rem;
  padding: 0.85rem 1rem;
  border-radius: 1.5rem;
  background:
    radial-gradient(120% 140% at 100% 0%, color-mix(in srgb, var(--cs-tint) 26%, transparent), transparent 62%), radial-gradient(90% 120% at 0% 100%, color-mix(in srgb, var(--cs-tint) 12%, transparent), transparent 70%),
    var(--dsh-group);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.35);
  overflow: hidden;
  transition: background 0.5s;
}
.cs__hero-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  flex: 0 1 auto;
}
.cs__hero-text b {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.cs__hero-text span {
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
}
.cs__hero-chart {
  flex: 1;
  min-width: 0;
  height: 3.9rem;
  margin-inline-start: auto;
  max-width: 9.5rem;
}
.cs__label {
  margin: 0 0 0.45rem;
  padding-inline: 0.85rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.cs__types {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.25rem;
  padding: 0.3rem;
  border-radius: 1.35rem;
  background: var(--dsh-group);
}
.cs__type {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
  padding: 0.6rem 0.2rem 0.5rem;
  border: 0;
  border-radius: 1.08rem;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;
  transition:
    background 0.3s,
    box-shadow 0.3s,
    transform 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.cs__type:hover {
  background: color-mix(in srgb, var(--p-text-color) 5%, transparent);
}
.cs__type:active {
  transform: scale(0.93);
}
/* the chosen one: a raised glass lens, as iOS's selected control */
.cs__type--on,
.cs__type--on:hover {
  background: var(--p-content-background);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.6),
    0 6px 18px -8px color-mix(in srgb, var(--cs-tint) 65%, transparent),
    0 0 0 1.5px color-mix(in srgb, var(--cs-tint) 70%, transparent);
}
.cs__preview {
  width: 2.75rem;
  height: 1.75rem;
  transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.cs__type--on .cs__preview {
  transform: scale(1.08);
}
.cs__name {
  max-width: 100%;
  overflow: hidden;
  font-size: 0.68rem;
  font-weight: 550;
  line-height: 1.2;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--p-text-muted-color);
}
.cs__type--on .cs__name {
  color: var(--p-text-color);
  font-weight: 650;
}
.cs__swatches {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.2rem;
  padding: 0.6rem 0.35rem 0.5rem;
  border-radius: 1.35rem;
  background: var(--dsh-group);
}
.cs__swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  cursor: pointer;
}
/* a squircle of the palette's colours, glossy on top like glass */
.cs__chip {
  position: relative;
  display: grid;
  place-items: center;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 32%;
  box-shadow:
    inset 0 0 0 0.5px rgb(0 0 0 / 0.12),
    0 4px 10px -4px rgb(0 0 0 / 0.35);
  transition:
    transform 0.35s cubic-bezier(0.32, 0.72, 0, 1),
    box-shadow 0.3s;
}
.cs__chip::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgb(255 255 255 / 0.45) 0%, rgb(255 255 255 / 0.08) 42%, transparent 55%);
  pointer-events: none;
}
.cs__chip i {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 999px;
  font-size: 0.55rem;
  font-weight: 800;
  color: #111;
  background: rgb(255 255 255 / 0.92);
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.3);
  animation: cs-pop 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.cs__swatch:hover .cs__chip {
  transform: translateY(-2px);
}
.cs__swatch--on .cs__chip {
  transform: scale(1.06);
  box-shadow:
    0 0 0 2px var(--p-content-background),
    0 0 0 4px color-mix(in srgb, var(--p-text-color) 70%, transparent),
    0 6px 14px -5px rgb(0 0 0 / 0.4);
}
@keyframes cs-pop {
  from {
    transform: scale(0.3);
    opacity: 0;
  }
}
.cs__swatch-name {
  max-width: 100%;
  overflow: hidden;
  font-size: 0.62rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cs__swatch--on .cs__swatch-name {
  color: var(--p-text-color);
  font-weight: 650;
}
.cs__list {
  display: flex;
  flex-direction: column;
  border-radius: 1.35rem;
  background: var(--dsh-group);
  overflow: hidden;
}
.cs__row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.9rem;
  cursor: pointer;
}
.cs__row + .cs__row {
  position: relative;
}
/* iOS's inset separator: from the text on, not under the icon */
.cs__row + .cs__row::before {
  content: '';
  position: absolute;
  top: 0;
  inset-inline: 3.35rem 0;
  border-top: 0.5px solid var(--dsh-hair, color-mix(in srgb, var(--p-text-color) 10%, transparent));
}
.cs__row-icon {
  display: grid;
  place-items: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.5rem;
  color: #fff;
  background: linear-gradient(180deg, color-mix(in srgb, var(--c) 80%, #fff), var(--c));
}
.cs__row-icon i {
  font-size: 0.75rem;
}
.cs__row-name {
  flex: 1;
  font-size: 0.9rem;
}
.cs-swap-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.45s cubic-bezier(0.32, 0.72, 0, 1);
}
.cs-swap-leave-active {
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}
.cs-swap-enter-from {
  opacity: 0;
  transform: translateY(6px) scale(0.96);
}
.cs-swap-leave-to {
  opacity: 0;
  transform: scale(0.98);
}
html.app-dark .cs__type--on,
html.app-dark .cs__type--on:hover {
  background: color-mix(in srgb, var(--p-text-color) 12%, transparent);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.08),
    0 6px 18px -8px color-mix(in srgb, var(--cs-tint) 65%, transparent),
    0 0 0 1.5px color-mix(in srgb, var(--cs-tint) 70%, transparent);
}
html.app-dark .cs__hero {
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.06);
}
@media (prefers-reduced-motion: reduce) {
  .cs__chip i,
  .cs-swap-enter-active,
  .cs-swap-leave-active {
    animation: none;
    transition: none;
  }
}
</style>
