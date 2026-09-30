<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  inputId: string
  placeholder?: string
  /** domain -> error message (from the server). */
  errors?: Record<string, string>
  invalid?: boolean
  disabled?: boolean
}>()

const model = defineModel<string[]>({ required: true })

const { t } = useI18n()
const draft = ref('')
const input = ref<HTMLInputElement | null>(null)

const errorList = computed(() => Object.entries(props.errors ?? {}).filter(([domain]) => model.value.includes(domain)))

function normalize(value: string): string {
  return value.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '')
}

function add(raw: string) {
  const names = raw.split(/[\s,;]+/).map(normalize).filter(Boolean)
  const next = [...model.value]
  for (const name of names) if (!next.includes(name)) next.push(name)
  if (next.length !== model.value.length) model.value = next
  draft.value = ''
}

function remove(name: string) {
  model.value = model.value.filter((domain) => domain !== name)
  input.value?.focus()
}

function onKeydown(event: KeyboardEvent) {
  if (['Enter', ',', ' ', 'Tab'].includes(event.key) && draft.value.trim()) {
    event.preventDefault()
    add(draft.value)
  } else if (event.key === 'Backspace' && !draft.value && model.value.length) {
    remove(model.value[model.value.length - 1]!)
  }
}

function onPaste(event: ClipboardEvent) {
  const text = event.clipboardData?.getData('text') ?? ''
  if (/[\s,;]/.test(text.trim())) {
    event.preventDefault()
    add(text)
  }
}
</script>

<template>
  <div>
    <div
      class="chips"
      :class="{ 'chips--invalid': invalid || errorList.length, 'chips--disabled': disabled }"
      dir="ltr"
      @click="input?.focus()"
    >
      <TransitionGroup name="chip">
        <span
          v-for="name in model"
          :key="name"
          class="chip"
          :class="{ 'chip--error': errors?.[name] }"
          :title="errors?.[name] || name"
        >
          <i v-if="errors?.[name]" class="pi pi-exclamation-circle" />
          {{ name }}
          <button type="button" class="chip__remove" :aria-label="t('quickSetup.domains.remove', { name })" :disabled="disabled" @click.stop="remove(name)">
            <i class="pi pi-times" />
          </button>
        </span>
      </TransitionGroup>
      <input
        :id="inputId"
        ref="input"
        v-model="draft"
        class="chips__input"
        :placeholder="model.length ? '' : placeholder"
        :disabled="disabled"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        inputmode="url"
        @keydown="onKeydown"
        @paste="onPaste"
        @blur="draft.trim() && add(draft)"
      />
    </div>
    <TransitionGroup name="chip-error" tag="ul" class="chips__errors">
      <li v-for="[domain, message] in errorList" :key="domain">
        <strong dir="ltr">{{ domain }}</strong>: {{ message }}
      </li>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.75rem;
  padding: 0.4rem 0.5rem;
  border-radius: var(--p-inputtext-border-radius, 8px);
  border: 1px solid var(--p-inputtext-border-color, var(--p-content-border-color));
  background: var(--p-inputtext-background, var(--p-content-background));
  cursor: text;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.chips:focus-within {
  border-color: var(--p-primary-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 20%, transparent);
}
.chips--invalid {
  border-color: var(--p-red-500, #ef4444);
}
.chips--disabled {
  opacity: 0.6;
  pointer-events: none;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  max-width: 100%;
  padding: 0.2rem 0.3rem 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.85rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  overflow-wrap: anywhere;
}
.chip--error {
  color: var(--p-red-600, #dc2626);
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 12%, transparent);
}
.chip__remove {
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.chip__remove:hover {
  background: color-mix(in srgb, currentColor 16%, transparent);
}
.chip__remove i {
  font-size: 0.65rem;
}
.chips__input {
  flex: 1 1 8rem;
  min-width: 6rem;
  border: 0;
  outline: none;
  background: transparent;
  color: inherit;
  font: inherit;
  padding: 0.25rem;
}
.chips__errors {
  margin: 0.4rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.82rem;
  color: var(--p-red-500, #ef4444);
}
.chips__errors li + li {
  margin-top: 0.2rem;
}
.chip-enter-active,
.chip-leave-active,
.chip-error-enter-active,
.chip-error-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.chip-enter-from,
.chip-leave-to {
  opacity: 0;
  transform: scale(0.85);
}
.chip-error-enter-from,
.chip-error-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
</style>
