<script setup lang="ts">
/**
 * Operators to pick, as chips: the named ones, and any AS number typed in the search ("AS254", "AS۲۵۴") with its
 * company (GeoLite2). None picked: every operator without addresses of its own. v-model: the codes.
 */
import { computed, nextTick, ref, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiSelect from 'primevue/multiselect'
import { useAsnNames } from '@/shared/composables/useAsnNames'
import { OPERATORS, OTHER, asCode, type OperatorKey } from '@/shared/utils/operator-ips'

/** ``suggest``: AS numbers offered without typing them (e.g. the admin's own network). */
const props = defineProps<{ suggest?: string[]; invalid?: boolean; ariaLabel?: string }>()
const model = defineModel<OperatorKey[]>({ required: true })
const { t } = useI18n()
const asns = useAsnNames()

/** Longest company name in a chip (the whole one is its tooltip). */
const CHIP_NAME = 22
// What is typed in the search: "AS254" (or "AS۲۵۴") there offers that AS as an operator
const typed = ref('')

const offeredAs = computed(() =>
  [...new Set([...model.value.filter((c) => c.startsWith('AS')), ...(props.suggest ?? []), asCode(typed.value)])].filter(
    (c): c is OperatorKey => !!c && c.startsWith('AS'),
  ),
)
// The companies of the AS numbers shown
watchEffect(() => asns.request(offeredAs.value))

/** "AS254 · Attachmate Corp." once the company is known, else "AS254 (by AS number)". */
function asLabel(code: string): string {
  const name = asns.nameOf(code)
  return name ? `${code} · ${name}` : t('operatorIps.asOption', { code })
}
const options = computed(() => {
  const typedAs = asCode(typed.value)
  // AS numbers first (searchable by what was typed: "AS۲۵۴" finds AS254), then the named operators
  const asList = offeredAs.value.map((code) => ({ code, label: asLabel(code), search: code === typedAs ? typed.value : '' }))
  // none picked is "every other operator": no option for it
  const named = OPERATORS.filter((o) => o.code !== OTHER).map((o) => ({
    code: o.code as OperatorKey,
    label: `${t(`operatorIps.name.${o.code}`)} (${o.code})`,
    search: '',
  }))
  return [...asList, ...named]
})

/** A pick: the list updated, and the search cleared for the next one (MultiSelect has no option for it). */
async function onPick(picked: OperatorKey[]) {
  model.value = picked
  typed.value = ''
  await nextTick()
  const search = document.querySelector<HTMLInputElement>('.p-multiselect-overlay input.p-multiselect-filter')
  if (search?.value) {
    search.value = ''
    search.dispatchEvent(new Event('input', { bubbles: true }))
  }
}

/** A chip's name next to its code: the operator's, or the AS company (shortened). */
function chipName(code: OperatorKey): string {
  if (code.startsWith('AS')) {
    const name = asns.nameOf(code)
    return name.length > CHIP_NAME ? `${name.slice(0, CHIP_NAME - 1)}…` : name
  }
  return t(`operatorIps.name.${code}`)
}
function chipTitle(code: OperatorKey): string {
  return code.startsWith('AS') ? asLabel(code) : `${chipName(code)} (${code})`
}
</script>

<template>
  <MultiSelect
    :model-value="model"
    :options="options"
    option-label="label"
    option-value="code"
    display="chip"
    filter
    :filter-placeholder="t('operatorIps.searchOrAs')"
    :filter-fields="['label', 'search']"
    :show-toggle-all="false"
    :placeholder="t('operatorIps.name.OTHER')"
    :aria-label="props.ariaLabel ?? t('operatorIps.operator')"
    :invalid="props.invalid"
    class="op"
    @update:model-value="onPick"
    @filter="typed = $event.value"
    @show="typed = ''"
  >
    <template #chip="{ value, removeCallback }">
      <span class="op__chip" :class="{ 'op__chip--as': value.startsWith('AS') }" :title="chipTitle(value)">
        <b class="op__chip-code" dir="ltr">{{ value }}</b>
        <bdi v-if="chipName(value)" class="op__chip-name">{{ chipName(value) }}</bdi>
        <i class="pi pi-times op__chip-x" role="button" :aria-label="t('operatorIps.remove')" @click.stop="removeCallback($event, value)" />
      </span>
    </template>
  </MultiSelect>
</template>

<style scoped>
.op {
  min-width: 0;
}
.op :deep(.p-multiselect-label) {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  white-space: normal;
}
/* a chip: the code tag, then the name */
.op__chip {
  --op-tone: var(--p-primary-color);
  /* codes keep Latin digits (the page font shows every digit in Persian) */
  font-family: 'Vazirmatn', 'Lato', sans-serif;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  max-inline-size: 100%;
  padding-block: 0.1rem;
  padding-inline: 0.15rem 0.4rem;
  border-radius: 999px;
  font-size: 0.78rem;
  border: 1px solid color-mix(in srgb, var(--op-tone) 28%, transparent);
  background: color-mix(in srgb, var(--op-tone) 8%, var(--p-content-background));
}
.op__chip--as {
  --op-tone: var(--p-text-muted-color);
}
.op__chip-code {
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.7rem;
  letter-spacing: 0.02em;
  color: var(--p-primary-contrast-color);
  background: var(--op-tone);
}
.op__chip-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--p-text-color);
}
.op__chip-x {
  font-size: 0.55rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.op__chip-x:hover {
  color: var(--p-red-500);
}
</style>
