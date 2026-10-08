<script setup lang="ts">
/** Empty state of a list whose filters hide everything. */
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineEmits<{ reset: [] }>()
const { t } = useI18n()
</script>

<template>
  <div class="lnm" role="status">
    <i class="pi pi-filter-slash" />
    <strong>{{ t('common.noMatch') }}</strong>
    <span>{{ t('common.noMatchHint') }}</span>
    <Button icon="pi pi-times" :label="t('common.resetFilters')" size="small" severity="secondary" outlined @click="$emit('reset')" />
  </div>
</template>

<style scoped>
.lnm {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 1.5rem 1rem;
  text-align: center;
  color: var(--p-text-muted-color);
}
.lnm > i {
  font-size: 1.8rem;
  color: var(--p-amber-500, #f59e0b);
}
.lnm strong {
  color: var(--p-text-color);
}
.lnm .p-button {
  margin-top: 0.5rem;
}
</style>
