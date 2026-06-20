<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

defineProps<{
  customized?: boolean
  iconOnly?: boolean
}>()

const { t } = useI18n()
</script>

<template>
  <Tag
    :severity="customized ? 'warn' : 'secondary'"
    class="sys-badge"
    v-tooltip.top="customized ? t('template.builtinCustomized') : t('template.sysTooltip')"
  >
    <span class="sys-badge__inner">
      <i class="pi pi-briefcase" aria-hidden="true" />
      <span v-if="!iconOnly" class="sys-badge__label">SYS</span>
    </span>
  </Tag>
</template>

<style scoped>
.sys-badge :deep(.p-tag) {
  padding: 0.1rem 0.35rem;
}
.sys-badge__inner {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.65rem;
  font-weight: 600;
  line-height: 1;
}
.sys-badge__label {
  letter-spacing: 0.02em;
}
</style>
