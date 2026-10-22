<script setup lang="ts">
/**
 * Addresses (IPs, ranges, host names) as chips: what is typed becomes a chip at a space, comma, semicolon or Enter,
 * on a paste or when leaving the box; Backspace in an empty box takes the last one back. v-model: "a, b, c".
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { addressesOf, isAddress } from '@/shared/utils/operator-ips'

const props = defineProps<{ placeholder?: string; invalid?: boolean; ariaLabel?: string }>()
const model = defineModel<string>({ required: true })
const { t } = useI18n()

const draft = ref('')
const input = ref<HTMLInputElement | null>(null)
const chips = computed(() => addressesOf(model.value))

function setChips(list: string[]) {
  model.value = [...new Set(list)].join(', ')
}
/** The typed text (one or more addresses) as chips. */
function commit() {
  const added = addressesOf(draft.value)
  draft.value = ''
  if (added.length) setChips([...chips.value, ...added])
}
function remove(index: number) {
  setChips(chips.value.filter((_, i) => i !== index))
  input.value?.focus()
}

function onKeydown(e: KeyboardEvent) {
  if ([' ', ',', ';', 'Enter', 'Tab'].includes(e.key) && draft.value.trim()) {
    if (e.key !== 'Tab') e.preventDefault()
    commit()
  } else if (e.key === 'Backspace' && !draft.value && chips.value.length) {
    e.preventDefault()
    const last = chips.value[chips.value.length - 1] ?? ''
    setChips(chips.value.slice(0, -1))
    draft.value = last // back to text, to fix it
  }
}
function onPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') ?? ''
  if (!/[\s,;]/.test(text.trim())) return // one address: typed as usual
  e.preventDefault()
  draft.value += text
  commit()
}
</script>

<template>
  <div class="ac" :class="{ 'ac--invalid': props.invalid }" @click="input?.focus()">
    <i class="pi pi-globe ac__icon" />
    <span v-for="(chip, index) in chips" :key="chip" class="ac__chip" :class="{ 'ac__chip--bad': !isAddress(chip) }" :title="isAddress(chip) ? chip : t('operatorIps.badAddress', { list: chip })">
      <bdi dir="ltr">{{ chip }}</bdi>
      <i class="pi pi-times ac__x" role="button" :aria-label="t('operatorIps.remove')" @click.stop="remove(index)" />
    </span>
    <input
      ref="input"
      v-model="draft"
      class="ac__input"
      :dir="draft ? 'ltr' : undefined"
      spellcheck="false"
      autocomplete="off"
      :placeholder="chips.length ? '' : props.placeholder"
      :aria-label="props.ariaLabel"
      @keydown="onKeydown"
      @paste="onPaste"
      @blur="commit"
    />
  </div>
</template>

<style scoped>
.ac {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  min-block-size: 2.5rem;
  padding: 0.3rem 0.55rem;
  border: 1px solid var(--p-inputtext-border-color, var(--p-content-border-color));
  border-radius: var(--p-inputtext-border-radius, 6px);
  background: var(--p-inputtext-background, var(--p-content-background));
  cursor: text;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.ac:hover {
  border-color: var(--p-inputtext-hover-border-color, var(--p-text-muted-color));
}
.ac:focus-within {
  border-color: var(--p-primary-color);
  box-shadow: 0 0 0 1px var(--p-primary-color);
}
.ac--invalid {
  border-color: var(--p-red-400);
}
.ac__icon {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.ac__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding-block: 0.15rem;
  padding-inline: 0.55rem 0.35rem;
  border-radius: 0.45rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  border: 1px solid color-mix(in srgb, var(--p-green-500) 30%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-green-500) 8%, var(--p-content-background));
}
.ac__chip--bad {
  color: var(--p-red-500);
  border-color: color-mix(in srgb, var(--p-red-400) 55%, transparent);
  background: color-mix(in srgb, var(--p-red-400) 10%, var(--p-content-background));
}
.ac__x {
  font-size: 0.55rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.ac__x:hover {
  color: var(--p-red-500);
}
.ac__input {
  flex: 1 1 8rem;
  min-width: 6rem;
  border: 0;
  outline: 0;
  padding: 0.2rem 0.1rem;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
}
.ac__input[dir='ltr'] {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
}
.ac__input::placeholder {
  color: var(--p-inputtext-placeholder-color, var(--p-text-muted-color));
}
</style>
