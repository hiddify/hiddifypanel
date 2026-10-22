<script setup lang="ts">
/**
 * Editor of a CDN IP field: a table of "address + operator" rows (like ip-format.hiddify.com), or the raw text on
 * request. An address without an operator is "OTHER" (every operator without its own). v-model is the field's text.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import {
  OPERATORS,
  OTHER,
  ircfDefaults,
  parseOperatorIps,
  serializeOperatorIps,
  type OperatorCode,
  type OperatorIpRow,
} from '@/shared/utils/operator-ips'

const props = defineProps<{ invalid?: boolean }>()
const model = defineModel<string>({ required: true })
const { t } = useI18n()

const rows = ref<OperatorIpRow[]>([])
const mode = ref<'table' | 'text'>('table')

function load(text: string) {
  const parsed = parseOperatorIps(text)
  rows.value = parsed.length ? parsed : [{ host: '', operator: OTHER }]
}
load(model.value)

// A change from outside (a rebuild, a reset) shows in the table; our own edits are already there.
watch(model, (text) => {
  if (text !== serializeOperatorIps(rows.value)) load(text)
})
watch(rows, (value) => {
  if (mode.value === 'table') model.value = serializeOperatorIps(value)
}, { deep: true })

const operatorOptions = computed(() =>
  OPERATORS.map((o) => {
    const name = t(`operatorIps.name.${o.code}`)
    return { code: o.code, label: o.code === OTHER ? name : `${name} (${o.code})` }
  }),
)
const missingDefaults = computed(() => {
  const used = new Set(rows.value.filter((r) => r.host.trim()).map((r) => r.operator))
  return ircfDefaults().filter((r) => !used.has(r.operator))
})

function addRow(operator: OperatorCode = OTHER) {
  rows.value.push({ host: '', operator })
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
      <div v-for="(row, index) in rows" :key="index" class="oip__row">
        <InputText
          v-model="row.host"
          dir="ltr"
          spellcheck="false"
          class="oip__host"
          :placeholder="t('operatorIps.host')"
          :aria-label="t('operatorIps.host')"
          :invalid="props.invalid"
        />
        <Select
          v-model="row.operator"
          :options="operatorOptions"
          option-label="label"
          option-value="code"
          filter
          class="oip__operator"
          :placeholder="t('operatorIps.operator')"
          :aria-label="t('operatorIps.operator')"
        />
        <Button icon="pi pi-trash" severity="danger" text rounded :aria-label="t('operatorIps.remove')" @click="removeRow(index)" />
      </div>
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
      <Textarea v-model="model" dir="ltr" rows="3" auto-resize spellcheck="false" :invalid="props.invalid" fluid class="font-mono text-sm" />
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
.oip__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.oip__host {
  flex: 1 1 14rem;
  min-width: 0;
}
.oip__operator {
  flex: 1 1 10rem;
  min-width: 0;
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
