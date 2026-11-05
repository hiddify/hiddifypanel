<script setup lang="ts">
/**
 * A number field with − and + buttons that works the same with a finger as with a mouse.
 *
 * PrimeVue's InputNumber steps on `mousedown` and focuses its input first: on a phone that opens the keyboard, the
 * dialog resizes and the tap misses, so the buttons need several taps. It also types through `keypress`, which
 * Android keyboards don't send, so typed digits mix with its formatting. Here the buttons step on `click` without
 * taking the focus, and the field is a plain text input that reads what was typed on every change.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{
    min?: number
    max?: number
    step?: number
    /** Decimals allowed when typing (0: whole numbers). */
    fractionDigits?: number
    /** Shown after the number, e.g. "GB". */
    suffix?: string
    placeholder?: string
    invalid?: boolean
    disabled?: boolean
    inputId?: string
  }>(),
  { min: undefined, max: undefined, step: 1, fractionDigits: 0, suffix: '', placeholder: '', inputId: undefined },
)
const model = defineModel<number | null>({ default: null })

const { t } = useI18n()

const text = ref('')
const editing = ref(false)

function round(value: number): number {
  const p = 10 ** props.fractionDigits
  return Math.round(value * p) / p
}
function clamp(value: number): number {
  if (props.min !== undefined && value < props.min) return props.min
  if (props.max !== undefined && value > props.max) return props.max
  return value
}
function show(value: number | null): string {
  return value === null || value === undefined ? '' : String(round(value))
}

// What the model holds, unless the admin is typing (then their text stays as typed).
watch(
  model,
  (value) => {
    if (!editing.value) text.value = show(value)
  },
  { immediate: true },
)

/** Keeps digits (Persian and Arabic ones too) and one decimal point, with at most `fractionDigits` decimals. */
function clean(raw: string): string {
  let s = raw
    .replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[٫,]/g, '.')
    .replace(/[^\d.]/g, '')
  if (props.fractionDigits <= 0) return s.replace(/\./g, '')
  const dot = s.indexOf('.')
  if (dot >= 0) s = s.slice(0, dot + 1) + s.slice(dot + 1).replace(/\./g, '').slice(0, props.fractionDigits)
  return s
}

function onInput(event: Event) {
  const input = event.target as HTMLInputElement
  const cleaned = clean(input.value)
  if (cleaned !== input.value) input.value = cleaned
  text.value = cleaned
  const value = Number.parseFloat(cleaned)
  model.value = Number.isFinite(value) ? round(value) : null
}

// The model reads back its old value until the parent re-renders, so the new one is kept in a local first.
function set(value: number | null) {
  if (value !== model.value) model.value = value
  text.value = show(value)
}

function onBlur() {
  editing.value = false
  set(model.value === null ? null : clamp(round(model.value)))
}

const atMin = computed(() => props.min !== undefined && model.value !== null && model.value <= props.min)
const atMax = computed(() => props.max !== undefined && model.value !== null && model.value >= props.max)

function stepBy(dir: 1 | -1) {
  if (props.disabled) return
  // also while the field is being typed in: the step replaces what was typed
  set(clamp(round((model.value ?? 0) + props.step * dir)))
}
</script>

<template>
  <div class="nstep" :class="{ 'nstep--invalid': invalid, 'nstep--disabled': disabled }">
    <!-- mousedown.prevent: the buttons don't take the focus, so a phone keyboard doesn't open or close under the tap -->
    <button
      type="button"
      class="nstep__btn"
      :aria-label="t('common.decrease')"
      :disabled="disabled || atMin"
      :aria-controls="inputId"
      @mousedown.prevent
      @click="stepBy(-1)"
    >
      <span class="pi pi-minus" aria-hidden="true" />
    </button>
    <label class="nstep__box">
      <input
        :id="inputId"
        class="nstep__input"
        type="text"
        :inputmode="fractionDigits > 0 ? 'decimal' : 'numeric'"
        autocomplete="off"
        enterkeyhint="done"
        dir="ltr"
        role="spinbutton"
        :aria-valuemin="min"
        :aria-valuemax="max"
        :aria-valuenow="model ?? undefined"
        :aria-invalid="invalid || undefined"
        :value="text"
        :placeholder="placeholder"
        :disabled="disabled"
        :size="Math.max(text.length, 1)"
        @focus="editing = true"
        @input="onInput"
        @blur="onBlur"
        @keydown.up.prevent="stepBy(1)"
        @keydown.down.prevent="stepBy(-1)"
      />
      <span v-if="suffix && text" class="nstep__suffix">{{ suffix }}</span>
    </label>
    <button
      type="button"
      class="nstep__btn"
      :aria-label="t('common.increase')"
      :disabled="disabled || atMax"
      :aria-controls="inputId"
      @mousedown.prevent
      @click="stepBy(1)"
    >
      <span class="pi pi-plus" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.nstep {
  display: flex;
  align-items: stretch;
  width: 100%;
  min-height: 2.75rem;
  border: 1px solid var(--p-inputtext-border-color);
  border-radius: var(--p-inputtext-border-radius, 6px);
  background: var(--p-inputtext-background);
  color: var(--p-inputtext-color);
  box-shadow: var(--p-inputtext-shadow);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.nstep:hover:not(.nstep--disabled) {
  border-color: var(--p-inputtext-hover-border-color);
}
.nstep:focus-within {
  border-color: var(--p-inputtext-focus-border-color);
  box-shadow: 0 0 0 1px var(--p-inputtext-focus-border-color);
}
.nstep--invalid,
.nstep--invalid:hover:not(.nstep--disabled) {
  border-color: var(--p-inputtext-invalid-border-color);
}
.nstep--disabled {
  background: var(--p-inputtext-disabled-background);
  color: var(--p-inputtext-disabled-color);
}
.nstep__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 2.75rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  /* no double-tap zoom delay, no text selection or callout on a long press */
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.nstep__btn:first-child {
  border-inline-end: 1px solid var(--p-inputtext-border-color);
  border-start-start-radius: inherit;
  border-end-start-radius: inherit;
}
.nstep__btn:last-child {
  border-inline-start: 1px solid var(--p-inputtext-border-color);
  border-start-end-radius: inherit;
  border-end-end-radius: inherit;
}
.nstep__btn:hover:not(:disabled) {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
}
.nstep__btn:active:not(:disabled) {
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  color: var(--p-primary-color);
}
.nstep__btn:focus-visible {
  outline: 2px solid var(--p-focus-ring-color, var(--p-primary-color));
  outline-offset: -2px;
}
.nstep__btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.nstep__box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  flex: 1;
  min-width: 0;
  padding: 0 0.5rem;
  cursor: text;
}
.nstep__input {
  /* grows with the number (size), so the suffix sits right after it and the pair stays centred */
  min-width: 1ch;
  max-width: 100%;
  border: 0;
  padding: 0.5rem 0;
  background: transparent;
  color: inherit;
  font: inherit;
  /* 16px: iOS zooms the page into smaller inputs */
  font-size: max(1rem, 16px);
  text-align: center;
  outline: none;
}
.nstep__input:placeholder-shown {
  width: 100%;
}
.nstep__input::placeholder {
  color: var(--p-inputtext-placeholder-color);
}
.nstep__suffix {
  flex: none;
  color: var(--p-text-muted-color);
}
</style>
