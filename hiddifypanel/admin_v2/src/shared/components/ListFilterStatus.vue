<script setup lang="ts">
/** Shown above a list while it is filtered: how much of it is visible, and a way back to the full list. */
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps<{
  /** Rows that pass the filters. */
  shown: number
  /** Rows in the whole list. */
  total: number
  /** Any filter or search is on. */
  active: boolean
}>()
defineEmits<{ reset: [] }>()
const { t } = useI18n()
</script>

<template>
  <div v-if="active" class="lfs" :class="{ 'lfs--none': shown === 0 }" role="status">
    <i :class="shown === 0 ? 'pi pi-filter-slash' : 'pi pi-filter'" />
    <span class="lfs__text">
      <b>{{ shown === 0 ? t('common.noMatch') : t('common.filteredOf', { n: shown, total }) }}</b>
      <small v-if="shown === 0">{{ t('common.filteredOf', { n: 0, total }) }}</small>
    </span>
    <Button icon="pi pi-times" :label="t('common.resetFilters')" size="small" severity="secondary" outlined @click="$emit('reset')" />
  </div>
</template>

<style scoped>
.lfs {
  --tone: var(--p-primary-color);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.85rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid color-mix(in srgb, var(--tone) 45%, var(--p-content-border-color));
  border-radius: 12px;
  background: color-mix(in srgb, var(--tone) 8%, var(--p-content-background));
}
.lfs--none {
  --tone: var(--p-amber-500, #f59e0b);
}
.lfs > i {
  color: var(--tone);
}
.lfs__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}
.lfs__text small {
  color: var(--p-text-muted-color);
}
</style>
