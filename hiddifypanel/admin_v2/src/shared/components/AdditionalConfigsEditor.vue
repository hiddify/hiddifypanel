<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { CONFIG_TARGETS, configRowProblem, type AdditionalConfig, type ConfigKind } from '@/shared/utils/additional-configs'

/**
 * Rows of additional configs: offline (pasted) or subscription (URL), each for one app format or all.
 * `showErrors`: mark empty / bad rows (after a save attempt). `inherited`: rows coming from admins above.
 */
const rows = defineModel<AdditionalConfig[]>({ required: true })
defineProps<{ disabled?: boolean; showErrors?: boolean; inherited?: number }>()

const { t } = useI18n()

const kindOptions = computed(() => (['offline', 'subscription'] as ConfigKind[]).map((k) => ({ value: k, label: t(`users.configs.kind.${k}`) })))
const targetOptions = computed(() => CONFIG_TARGETS.map((x) => ({ value: x, label: t(`users.configs.target.${x}`) })))

function add(kind: ConfigKind) {
  rows.value = [...rows.value, [kind, 'auto', '']]
}
function remove(i: number) {
  rows.value = rows.value.filter((_, j) => j !== i)
}
</script>

<template>
  <div class="ace">
    <p v-if="inherited" class="ace__inherited"><i class="pi pi-sitemap" />{{ t('users.configs.inherited', { n: inherited }, inherited) }}</p>
    <TransitionGroup name="ace-row" tag="div" class="ace__rows">
      <div v-for="(row, i) in rows" :key="i" class="ace__row">
        <div class="ace__head">
          <SelectButton v-model="row[0]" :options="kindOptions" option-label="label" option-value="value" :allow-empty="false" size="small" :disabled="disabled" />
          <Select v-model="row[1]" :options="targetOptions" option-label="label" option-value="value" size="small" :disabled="disabled" class="ace__target" />
          <Button type="button" icon="pi pi-trash" text rounded severity="danger" size="small" :aria-label="t('common.delete')" :disabled="disabled" @click="remove(i)" />
        </div>
        <InputText
          v-if="row[0] === 'subscription'"
          v-model="row[2]"
          dir="ltr"
          class="w-full font-mono text-sm"
          :placeholder="t('users.configs.urlPlaceholder')"
          :invalid="showErrors && !!configRowProblem(row)"
          :disabled="disabled"
        />
        <Textarea
          v-else
          v-model="row[2]"
          dir="ltr"
          rows="3"
          class="w-full ace__mono"
          :placeholder="t('users.configs.offlinePlaceholder')"
          :invalid="showErrors && !!configRowProblem(row)"
          :disabled="disabled"
        />
        <small v-if="showErrors && configRowProblem(row)" class="ace__error">{{ t(configRowProblem(row)!) }}</small>
      </div>
    </TransitionGroup>
    <div class="flex flex-wrap gap-2">
      <Button type="button" icon="pi pi-link" :label="t('users.configs.addSubscription')" size="small" severity="secondary" outlined :disabled="disabled" @click="add('subscription')" />
      <Button type="button" icon="pi pi-file" :label="t('users.configs.addOffline')" size="small" severity="secondary" outlined :disabled="disabled" @click="add('offline')" />
    </div>
  </div>
</template>

<style scoped>
.ace {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ace__inherited {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.ace__rows {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ace__row {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.65rem;
  border-radius: 12px;
  border: 1px dashed var(--p-content-border-color);
}
.ace__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.ace__target {
  min-width: 9rem;
  flex: 1;
}
.ace__mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
}
.ace__error {
  color: var(--p-red-500, #ef4444);
}
.ace-row-enter-active,
.ace-row-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.ace-row-enter-from,
.ace-row-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
