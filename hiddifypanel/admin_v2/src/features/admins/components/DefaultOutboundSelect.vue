<script setup lang="ts">
/** The outbound an admin's users (and its sub-admins' users) leave through unless they choose another. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import type { OutboundOption } from '@/features/admins/api'
import OutboundModeIcon from '@/features/outbounds/components/OutboundModeIcon.vue'

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
const selected = computed(() => options.value.find((o) => o.id === inner.value) ?? options.value[0])
</script>

<template>
  <Select v-model="inner" :options="options" option-label="name" option-value="id" :input-id="inputId" :disabled="disabled" class="w-full">
    <template #value>
      <div class="flex items-center gap-2 min-w-0">
        <OutboundModeIcon :mode="selected.mode || 'auto'" :off="!selected.enabled" size="1.5rem" />
        <span class="truncate">{{ selected.name }}</span>
      </div>
    </template>
    <template #option="{ option }">
      <div class="flex items-center gap-2">
        <OutboundModeIcon :mode="option.mode || 'auto'" :off="!option.enabled" />
        <span>{{ option.name }}</span>
        <small v-if="!option.enabled" class="text-muted-color">· {{ t('users.form.outboundOff') }}</small>
      </div>
    </template>
  </Select>
</template>
