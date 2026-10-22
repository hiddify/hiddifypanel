<script setup lang="ts">
/**
 * Editor of a CDN IP field: a table of "address + operators" rows (like ip-format.hiddify.com), or the raw text on
 * request. A row is for one or more operators ("1.1.1.1 AS254,MKH"); none picked: every operator without its own.
 * v-model is the field's text.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import AddressChips from '@/shared/components/AddressChips.vue'
import OperatorPicker from '@/shared/components/OperatorPicker.vue'
import {
  addressesOf,
  isAddress,
  ircfDefaults,
  parseOperatorIps,
  serializeOperatorIps,
  type OperatorIpRow,
  type OperatorKey,
} from '@/shared/utils/operator-ips'

const props = defineProps<{ invalid?: boolean }>()
const model = defineModel<string>({ required: true })
const { t } = useI18n()

const rows = ref<OperatorIpRow[]>([])
const mode = ref<'table' | 'text'>('table')
function load(text: string) {
  const parsed = parseOperatorIps(text)
  rows.value = parsed.length ? parsed : [{ host: '', operators: [] }]
}
load(model.value)

// A change from outside (a rebuild, a reset) shows in the table; our own edits are already there.
watch(model, (text) => {
  if (text !== serializeOperatorIps(rows.value)) load(text)
})
watch(rows, (value) => {
  if (mode.value === 'table') model.value = serializeOperatorIps(value)
}, { deep: true })

const missingDefaults = computed(() => {
  const used = new Set(rows.value.filter((r) => r.host.trim()).flatMap((r) => r.operators))
  return ircfDefaults().filter((r) => !r.operators.some((c) => used.has(c)))
})

/** What is typed in an address field and is not an IP, a range or a host name. */
function badAddresses(host: string): string[] {
  return addressesOf(host).filter((a) => !isAddress(a))
}

function addRow(operators: OperatorKey[] = []) {
  rows.value.push({ host: '', operators })
}
function removeRow(index: number) {
  rows.value.splice(index, 1)
  if (!rows.value.length) addRow()
}
/** Every operator without an address gets its ircf.space one. */
function fillDefaults() {
  rows.value = [...rows.value.filter((r) => r.host.trim()), ...missingDefaults.value]
}
function showTable() {
  load(model.value)
  mode.value = 'table'
}
</script>

<template>
  <div class="oip">
    <template v-if="mode === 'table'">
      <TransitionGroup name="oip-row" tag="div" class="oip__rows">
        <div v-for="(row, index) in rows" :key="index" class="oip__row">
          <span class="oip__num">{{ index + 1 }}</span>
          <div class="oip__main">
            <AddressChips
              v-model="row.host"
              class="oip__host"
              :placeholder="t('operatorIps.host')"
              :aria-label="t('operatorIps.host')"
              :invalid="props.invalid || badAddresses(row.host).length > 0"
            />
            <small v-if="badAddresses(row.host).length" class="oip__bad">{{ t('operatorIps.badAddress', { list: badAddresses(row.host).slice(0, 3).join(', ') }) }}</small>
            <small v-else-if="addressesOf(row.host).length > 1" class="oip__count">{{ t('operatorIps.addressCount', { count: addressesOf(row.host).length }) }}</small>
            <div class="oip__for">
              <span class="oip__for-label">{{ t('operatorIps.for') }}</span>
              <OperatorPicker v-model="row.operators" class="oip__operator" />
            </div>
          </div>
          <Button icon="pi pi-trash" severity="danger" text rounded size="small" class="oip__del" :aria-label="t('operatorIps.remove')" @click="removeRow(index)" />
        </div>
      </TransitionGroup>
      <div class="oip__actions">
        <Button :label="t('operatorIps.add')" icon="pi pi-plus" size="small" severity="secondary" @click="addRow()" />
        <Button
          v-if="missingDefaults.length"
          v-tooltip.top="t('operatorIps.defaultsHint')"
          :label="t('operatorIps.defaults')"
          icon="pi pi-bolt"
          size="small"
          severity="secondary"
          text
          @click="fillDefaults"
        />
        <Button :label="t('operatorIps.asText')" icon="pi pi-align-left" size="small" text class="oip__switch" @click="mode = 'text'" />
      </div>
    </template>

    <template v-else>
      <Textarea v-model="model" dir="ltr" rows="3" auto-resize spellcheck="false" :invalid="props.invalid" fluid class="oip__text" />
      <div class="oip__actions">
        <Button :label="t('operatorIps.asTable')" icon="pi pi-table" size="small" text class="oip__switch" @click="showTable" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.oip {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.oip__rows {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
/* one address: a small card (number, address, who it is for, delete) */
.oip__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.6rem;
  padding: 0.6rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: var(--p-content-background);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.oip__row:focus-within {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, var(--p-content-border-color));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.oip__num {
  inline-size: 1.6rem;
  block-size: 1.6rem;
  margin-top: 0.45rem;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
}
.oip__main {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-width: 0;
}
.oip__for {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.oip__bad,
.oip__count {
  margin-top: -0.2rem;
  font-size: 0.74rem;
}
.oip__bad {
  color: var(--p-red-500);
}
.oip__count {
  color: var(--p-text-muted-color);
}
.oip__for-label {
  flex: none;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.oip__operator {
  flex: 1;
  min-width: 0;
}
.oip__del {
  margin-top: 0.15rem;
}
.oip-row-enter-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.oip-row-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
@media (max-width: 575px) {
  .oip__num {
    display: none;
  }
  .oip__row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .oip__for {
    flex-direction: column;
    align-items: stretch;
  }
}
/* addresses and codes: Latin digits, aligned */
.oip__text {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 0.85rem;
}
.oip__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.oip__switch {
  margin-inline-start: auto;
}
</style>
