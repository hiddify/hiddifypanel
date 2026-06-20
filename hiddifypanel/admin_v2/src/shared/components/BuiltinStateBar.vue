<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import ToggleSwitch from 'primevue/toggleswitch'
import SysBadge from '@/shared/components/SysBadge.vue'

const props = defineProps<{
  showToggle?: boolean
  override?: boolean
  defaultLabel?: string
  customizedLabel?: string
}>()

const emit = defineEmits<{
  'update:override': [value: boolean]
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 mb-3">
    <SysBadge :customized="override" />
    <span class="text-sm text-muted-color">
      {{
        override
          ? (customizedLabel || t('template.builtinCustomized'))
          : (defaultLabel || t('template.builtinDefault'))
      }}
    </span>
    <div v-if="showToggle" class="flex items-center gap-2 ml-auto">
      <label class="text-sm text-muted-color cursor-pointer" for="builtin-override-toggle">
        {{ t('template.customContent') }}
      </label>
      <ToggleSwitch
        id="builtin-override-toggle"
        :model-value="override"
        @update:model-value="emit('update:override', $event)"
      />
    </div>
  </div>
</template>
