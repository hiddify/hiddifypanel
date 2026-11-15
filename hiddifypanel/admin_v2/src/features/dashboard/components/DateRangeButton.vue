<script setup lang="ts">
/**
 * The dashboard's period button and its small window: quick periods (today, yesterday, this month, last month, the
 * last N days) and a calendar to pick any days from … to, in the page's own calendar.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import DashSheet from './DashSheet.vue'
import { MAX_DAYS, QUICK_PRESETS, addDays, daysBetween, fromIso, iso, monthGrid, presetRange, shortDay, today, type CustomRange, type QuickPreset } from '../utils/date-range'

const props = defineProps<{ rangeDays: number; customRange: CustomRange | null; toolbarDays: readonly number[] }>()
const emit = defineEmits<{ 'pick-days': [days: number]; 'pick-range': [range: CustomRange] }>()
const { t, locale } = useI18n()

const sheet = ref<InstanceType<typeof DashSheet> | null>(null)
const minDay = iso(addDays(today(), 1 - MAX_DAYS))
const maxDay = iso(today())

/** The preset now in use (the toolbar's N days count as "last N") */
const activePreset = computed<QuickPreset | null>(() => (props.customRange ? (props.customRange.preset ?? null) : (`last${props.rangeDays}` as QuickPreset)))

const label = computed(() => {
  const range = props.customRange
  if (!range) return ''
  if (range.preset) return t(`dashboard.period.presets.${range.preset}`)
  return range.start === range.end ? shortDay(range.start, locale.value) : `${shortDay(range.start, locale.value)} – ${shortDay(range.end, locale.value)}`
})

// --- the calendar --------------------------------------------------------------------------------------------
const anchor = ref(today())
const start = ref<string | null>(null)
const end = ref<string | null>(null)
const hover = ref<string | null>(null)
const grid = computed(() => monthGrid(anchor.value, locale.value))
const canBack = computed(() => iso(grid.value.first) > minDay)
const canForward = computed(() => iso(grid.value.last) < maxDay)

function onOpen(event: Event) {
  const range = props.customRange
  start.value = range?.start ?? null
  end.value = range?.end ?? null
  anchor.value = range ? fromIso(range.end) : today()
  sheet.value?.open(event)
}

function pickDay(day: string) {
  if (day < minDay || day > maxDay) return
  if (!start.value || end.value) {
    start.value = day
    end.value = null
  } else if (day < start.value) {
    end.value = start.value
    start.value = day
  } else end.value = day
}

/** The range drawn on the calendar: the picked one, or from the first pick to the day under the pointer */
const shown = computed(() => {
  if (start.value && end.value) return [start.value, end.value] as const
  if (start.value && hover.value) return (hover.value < start.value ? [hover.value, start.value] : [start.value, hover.value]) as readonly [string, string]
  if (start.value) return [start.value, start.value] as const
  return null
})
function cell(day: string) {
  const range = shown.value
  return {
    off: day < minDay || day > maxDay,
    today: day === maxDay,
    edge: !!range && (day === range[0] || day === range[1]),
    first: !!range && day === range[0] && range[0] !== range[1],
    last: !!range && day === range[1] && range[0] !== range[1],
    within: !!range && day > range[0] && day < range[1],
  }
}
const pickedDays = computed(() => (start.value ? daysBetween(start.value, end.value ?? start.value) : 0))

function apply(close: () => void) {
  if (!start.value) return
  emit('pick-range', { start: start.value, end: end.value ?? start.value })
  close()
}
function preset(id: QuickPreset, close: () => void) {
  const days = Number(id.replace('last', ''))
  if (props.toolbarDays.includes(days)) emit('pick-days', days)
  else emit('pick-range', presetRange(id, locale.value))
  close()
}
</script>

<template>
  <button type="button" class="drb" :class="{ 'drb--on': customRange }" :aria-label="t('dashboard.period.title')" aria-haspopup="dialog" @click="onOpen">
    <i class="pi pi-calendar" />
    <Transition name="drb-label">
      <span v-if="customRange" :key="label" class="drb__label">{{ label }}</span>
    </Transition>
  </button>

  <DashSheet ref="sheet" :title="t('dashboard.period.title')" icon="pi pi-calendar">
    <template #default="{ close }">
      <div class="dr">
        <div class="dr__presets">
          <button v-for="id in QUICK_PRESETS" :key="id" type="button" class="dr__preset" :class="{ 'dr__preset--on': activePreset === id }" @click="preset(id, close)">
            {{ t(`dashboard.period.presets.${id}`) }}
          </button>
        </div>

        <div class="dr__fields">
          <div class="dr__field" :class="{ 'dr__field--active': !start || !!end }">
            <span>{{ t('dashboard.period.from') }}</span>
            <b>{{ start ? shortDay(start, locale) : '—' }}</b>
          </div>
          <i class="pi pi-arrow-right dr__arrow" />
          <div class="dr__field" :class="{ 'dr__field--active': !!start && !end }">
            <span>{{ t('dashboard.period.to') }}</span>
            <b>{{ end ? shortDay(end, locale) : start ? t('dashboard.period.pickEnd') : '—' }}</b>
          </div>
        </div>

        <div class="dr__cal">
          <div class="dr__nav">
            <button type="button" class="dr__step" :disabled="!canBack" :aria-label="t('dashboard.period.previousMonth')" @click="anchor = addDays(grid.first, -1)">
              <i class="pi pi-chevron-left" />
            </button>
            <Transition name="dr-title" mode="out-in">
              <span :key="grid.title" class="dr__title">{{ grid.title }}</span>
            </Transition>
            <button type="button" class="dr__step" :disabled="!canForward" :aria-label="t('dashboard.period.nextMonth')" @click="anchor = addDays(grid.last, 1)">
              <i class="pi pi-chevron-right" />
            </button>
          </div>
          <div class="dr__week">
            <span v-for="(w, i) in grid.weekdays" :key="i">{{ w }}</span>
          </div>
          <Transition name="dr-month" mode="out-in">
            <div :key="grid.title" class="dr__days" @pointerleave="hover = null">
              <span v-for="n in grid.lead" :key="`l${n}`" />
              <button
                v-for="day in grid.days"
                :key="day.iso"
                type="button"
                class="dr__day"
                :class="{
                  'dr__day--off': cell(day.iso).off,
                  'dr__day--today': cell(day.iso).today,
                  'dr__day--edge': cell(day.iso).edge,
                  'dr__day--first': cell(day.iso).first,
                  'dr__day--last': cell(day.iso).last,
                  'dr__day--within': cell(day.iso).within,
                }"
                :disabled="cell(day.iso).off"
                @pointerenter="hover = day.iso"
                @click="pickDay(day.iso)"
              >
                <span>{{ day.label }}</span>
              </button>
            </div>
          </Transition>
        </div>

        <p class="dr__note"><i class="pi pi-info-circle" />{{ t('dashboard.period.dailyNote') }}</p>

        <div class="dr__foot">
          <span class="dr__count">{{ pickedDays ? t('dashboard.nDays', { days: pickedDays }) : t('dashboard.period.pickStart') }}</span>
          <button type="button" class="dr__apply" :disabled="!start" @click="apply(close)">{{ t('dashboard.period.apply') }}</button>
        </div>
      </div>
    </template>
  </DashSheet>
</template>

<style scoped>
.drb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  flex: none;
  min-width: 2.25rem;
  height: 2.25rem;
  padding: 0 0.65rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-form-field-border-radius, 0.6rem);
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s,
    border-color 0.2s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.drb:hover {
  color: var(--p-text-color);
}
.drb:active {
  transform: scale(0.95);
}
.drb--on {
  color: var(--p-primary-contrast-color, #fff);
  border-color: transparent;
  background: var(--p-primary-color);
  box-shadow: 0 6px 16px -8px var(--p-primary-color);
}
.drb--on:hover {
  color: var(--p-primary-contrast-color, #fff);
}
.drb__label {
  max-width: 11rem;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drb-label-enter-active {
  transition:
    opacity 0.3s,
    max-width 0.4s cubic-bezier(0.32, 0.72, 0, 1);
}
.drb-label-enter-from {
  opacity: 0;
  max-width: 0;
}

.dr {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.dr__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.dr__preset {
  padding: 0.38rem 0.7rem;
  border: 0;
  border-radius: 999px;
  background: var(--dsh-group);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s,
    transform 0.2s cubic-bezier(0.32, 0.72, 0, 1);
}
.dr__preset:hover {
  background: color-mix(in srgb, var(--p-text-color) 9%, transparent);
}
.dr__preset:active {
  transform: scale(0.94);
}
.dr__preset--on,
.dr__preset--on:hover {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
  font-weight: 600;
}
.dr__fields {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dr__field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  padding: 0.45rem 0.7rem;
  border-radius: 0.75rem;
  background: var(--dsh-group);
  box-shadow: inset 0 0 0 1.5px transparent;
  transition: box-shadow 0.25s;
}
.dr__field--active {
  box-shadow: inset 0 0 0 1.5px var(--p-primary-color);
}
.dr__field span {
  font-size: 0.66rem;
  color: var(--p-text-muted-color);
}
.dr__field b {
  overflow: hidden;
  font-size: 0.86rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dr__arrow {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}
html[dir='rtl'] .dr__arrow,
html[dir='rtl'] .dr__step i {
  transform: scaleX(-1);
}
.dr__cal {
  padding: 0.6rem 0.5rem 0.5rem;
  border-radius: 0.95rem;
  background: var(--dsh-group);
}
.dr__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.35rem;
}
.dr__title {
  font-size: 0.9rem;
  font-weight: 650;
}
.dr__step {
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border: 0;
  border-radius: 999px;
  background: none;
  color: var(--p-primary-color);
  cursor: pointer;
}
.dr__step:hover:not(:disabled) {
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.dr__step:disabled {
  color: var(--p-text-muted-color);
  opacity: 0.4;
  cursor: default;
}
.dr__step i {
  font-size: 0.75rem;
}
.dr__week,
.dr__days {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}
.dr__week span {
  padding-block: 0.2rem;
  font-size: 0.66rem;
  font-weight: 600;
  text-align: center;
  color: var(--p-text-muted-color);
}
.dr__days {
  row-gap: 0.15rem;
}
.dr__day {
  position: relative;
  display: grid;
  place-items: center;
  height: 2.25rem;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}
.dr__day span {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 2.05rem;
  height: 2.05rem;
  border-radius: 999px;
  transition:
    background 0.18s,
    color 0.18s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.dr__day:hover:not(:disabled) span {
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.dr__day:active:not(:disabled) span {
  transform: scale(0.88);
}
/* the band between the two days, drawn behind them */
.dr__day--within::before,
.dr__day--first::before,
.dr__day--last::before {
  content: '';
  position: absolute;
  inset-block: 0.1rem;
  inset-inline: 0;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.dr__day--first::before {
  inset-inline-start: 50%;
}
.dr__day--last::before {
  inset-inline-end: 50%;
}
.dr__day--today span {
  color: var(--p-primary-color);
  font-weight: 700;
}
.dr__day--edge span,
.dr__day--edge:hover:not(:disabled) span {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
  font-weight: 650;
  box-shadow: 0 4px 12px -5px var(--p-primary-color);
}
.dr__day--off {
  color: var(--p-text-muted-color);
  opacity: 0.35;
  cursor: default;
}
.dr__note {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}
.dr__note i {
  margin-top: 0.15rem;
  font-size: 0.72rem;
}
.dr__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.dr__count {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.dr__apply {
  min-width: 6.5rem;
  padding: 0.55rem 1.1rem;
  border: 0;
  border-radius: 0.8rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    opacity 0.2s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.dr__apply:active:not(:disabled) {
  transform: scale(0.95);
}
.dr__apply:disabled {
  opacity: 0.4;
  cursor: default;
}
.dr-month-enter-active,
.dr-title-enter-active {
  transition:
    opacity 0.25s ease,
    transform 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.dr-month-leave-active,
.dr-title-leave-active {
  transition: opacity 0.1s ease;
}
.dr-month-enter-from,
.dr-title-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.dr-month-leave-to,
.dr-title-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .dr-month-enter-active,
  .dr-title-enter-active,
  .drb-label-enter-active {
    transition: none;
  }
}
</style>
