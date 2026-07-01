<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'

const props = defineProps<{
  overridden?: boolean
  disabled?: boolean
  fieldId?: string
}>()

const emit = defineEmits<{
  'update:overridden': [value: boolean]
  reset: []
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex items-center gap-2 shrink-0">
    <Checkbox
      :input-id="`override-${fieldId ?? 'field'}`"
      :model-value="overridden"
      :disabled="disabled"
      binary
      @update:model-value="emit('update:overridden', $event)"
    />
    <label class="text-sm text-muted-color whitespace-nowrap" :for="`override-${fieldId ?? 'field'}`">
      {{ t('proxy.fieldOverride') }}
    </label>
    <Button
      v-if="overridden"
      icon="pi pi-refresh"
      text
      rounded
      severity="secondary"
      :aria-label="t('proxy.resetToBuiltin')"
      :disabled="disabled"
      @click="emit('reset')"
    />
  </div>
</template>
