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
  sheet.value?.open(event)
}

const groups = computed(() => TYPE_GROUPS.map((group) => ({ key: group.key, types: group.types.filter((type) => props.types.includes(type)) })).filter((group) => group.types.length))
const previewColor = computed(() => PALETTES.find((p) => p.id === style.value.palette)?.colors[0] ?? props.accent)
const swatch = (id: string) => {
  const colors = id === 'auto' ? AUTO_SWATCH : PALETTES.find((p) => p.id === id)!.colors
  const stops = colors.slice(0, 4)
  return `conic-gradient(from 210deg, ${stops.map((c, i) => `${c} ${(i * 100) / stops.length}% ${((i + 1) * 100) / stops.length}%`).join(', ')})`
}

const set = (patch: Partial<ChartStyle>) => (style.value = { ...style.value, ...patch })
</script>

<template>
  <button type="button" class="csb" :class="[`csb--${size}`, { 'csb--open': opened }]" :aria-label="t('dashboard.chartStyle.title')" :title="t('dashboard.chartStyle.title')" aria-haspopup="dialog" @click.stop="open">
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M3 15.5 7.5 10l3 3L17 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="16.4" cy="14.6" r="2.6" :fill="previewColor" />
    </svg>
  </button>

  <DashSheet ref="sheet" :title="t('dashboard.chartStyle.title')" icon="pi pi-palette" @hide="opened = false">
    <div class="cs">
      <section v-for="group in groups" :key="group.key" class="cs__group">
        <h4 class="cs__label">{{ t(`dashboard.chartStyle.groups.${group.key}`) }}</h4>
        <div class="cs__types">
          <button v-for="type in group.types" :key="type" type="button" class="cs__type" :class="{ 'cs__type--on': style.type === type }" :aria-pressed="style.type === type" @click="set({ type })">
            <span class="cs__preview"><ChartTypeIcon :type="type" :color="previewColor" /></span>
            <span class="cs__name">{{ t(`dashboard.chartStyle.types.${type}`) }}</span>
            <i v-if="style.type === type" class="pi pi-check cs__check" aria-hidden="true" />
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
            <span class="cs__dot" :style="{ background: swatch(palette.id) }" />
            <span class="cs__swatch-name">{{ t(`dashboard.chartStyle.palettes.${palette.id}`) }}</span>
          </button>
        </div>
      </section>

      <section v-if="toggles.length" class="cs__list">
        <label v-if="toggles.includes('grid')" class="cs__row">
          <span class="cs__row-icon" style="--c: #64748b"><i class="pi pi-th-large" /></span>
          <span class="cs__row-name">{{ t('dashboard.chartStyle.grid') }}</span>
          <ToggleSwitch :model-value="style.grid" @update:model-value="(grid: boolean) => set({ grid })" />
        </label>
        <label v-if="toggles.includes('average')" class="cs__row">
          <span class="cs__row-icon" style="--c: #f59e0b"><i class="pi pi-minus" /></span>
          <span class="cs__row-name">{{ t('dashboard.chartStyle.average') }}</span>
          <ToggleSwitch :model-value="style.average" @update:model-value="(average: boolean) => set({ average })" />
        </label>
      </section>

      <button type="button" class="cs__reset" @click="emit('reset')"><i class="pi pi-refresh" />{{ t('dashboard.chartStyle.reset') }}</button>
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
  gap: 1rem;
}
.cs__label {
  margin: 0 0 0.45rem;
  padding-inline: 0.15rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.cs__types {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.45rem;
}
.cs__type {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
  padding: 0.55rem 0.25rem 0.45rem;
  border: 0;
  border-radius: 0.85rem;
  background: var(--dsh-group, color-mix(in srgb, var(--p-text-color) 4.5%, transparent));
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;
  transition:
    background 0.2s,
    box-shadow 0.25s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.cs__type:hover {
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
.cs__type:active {
  transform: scale(0.95);
}
.cs__type--on {
  background: color-mix(in srgb, var(--p-primary-color) 12%, var(--p-content-background));
  box-shadow: inset 0 0 0 1.5px var(--p-primary-color);
}
.cs__preview {
  width: 2.75rem;
  height: 1.75rem;
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
}
.cs__check {
  position: absolute;
  top: 0.3rem;
  inset-inline-end: 0.3rem;
  display: grid;
  place-items: center;
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 999px;
  font-size: 0.5rem;
  color: #fff;
  background: var(--p-primary-color);
  animation: cs-pop 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}
@keyframes cs-pop {
  from {
    transform: scale(0.3);
    opacity: 0;
  }
}
.cs__swatches {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.25rem;
}
.cs__swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
  padding: 0.2rem 0;
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  cursor: pointer;
}
.cs__dot {
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 999px;
  box-shadow:
    inset 0 0 0 0.5px rgb(0 0 0 / 0.12),
    0 2px 6px -2px rgb(0 0 0 / 0.25);
  transition:
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1),
    box-shadow 0.25s;
}
.cs__swatch:hover .cs__dot {
  transform: scale(1.08);
}
.cs__swatch--on .cs__dot {
  box-shadow:
    0 0 0 2px var(--p-content-background),
    0 0 0 4px var(--p-primary-color);
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
  font-weight: 600;
}
.cs__list {
  display: flex;
  flex-direction: column;
  border-radius: 0.85rem;
  background: var(--dsh-group, color-mix(in srgb, var(--p-text-color) 4.5%, transparent));
  overflow: hidden;
}
.cs__row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.75rem;
  cursor: pointer;
}
.cs__row + .cs__row {
  border-top: 0.5px solid color-mix(in srgb, var(--p-text-color) 10%, transparent);
}
.cs__row-icon {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 0.45rem;
  color: #fff;
  background: var(--c);
}
.cs__row-icon i {
  font-size: 0.72rem;
}
.cs__row-name {
  flex: 1;
  font-size: 0.86rem;
}
.cs__reset {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 0;
  background: none;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.cs__reset i {
  font-size: 0.72rem;
}
@media (prefers-reduced-motion: reduce) {
  .cs__check {
    animation: none;
  }
}
</style>
