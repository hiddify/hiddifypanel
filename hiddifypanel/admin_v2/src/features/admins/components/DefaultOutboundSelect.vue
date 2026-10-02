<script setup lang="ts">
/** The outbound an admin's users (and its sub-admins' users) leave through unless they choose another. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import type { OutboundOption } from '@/features/admins/api'

const props = defineProps<{ outbounds: OutboundOption[]; inherited: number | null; disabled?: boolean; inputId?: string }>()
const model = defineModel<number | null>({ required: true })
// PrimeVue treats null as "nothing selected" (blank), so "automatic" is 0 inside the select.
const inner = computed<number>({
  get: () => model.value ?? 0,
  set: (v) => (model.value = v || null),
})
const { t } = useI18n()

const inheritedName = computed(() => props.outbounds.find((o) => o.id === props.inherited)?.name)
const options = computed(() => [
  { id: 0, name: inheritedName.value ? t('admins.outbound.inherit', { name: inheritedName.value }) : t('admins.outbound.auto'), mode: '', enabled: true },
  ...props.outbounds,
])
</script>

<template>
  <Select v-model="inner" :options="options" option-label="name" option-value="id" :input-id="inputId" :disabled="disabled" class="w-full">
    <template #option="{ option }">
      <div class="flex items-center gap-2">
        <span>{{ option.name }}</span>
        <small v-if="option.mode" class="text-muted-color">{{ t(`outbounds.mode.${option.mode}`) }}</small>
        <small v-if="!option.enabled" class="text-muted-color">· {{ t('users.form.outboundOff') }}</small>
      </div>
    </template>
  </Select>
</template>
