<script setup lang="ts">
/**
 * A paged DataTable's pager in the Users page's style: PageScrubber (the bar to drag through the pages, the page
 * numbers, Previous / Next, "page [n] of N") and a small rows-per-page choice. Goes in DataTable's
 * #paginatorcontainer slot, which keeps the table's own paging (sorting, filtering) as it is:
 *
 *   <template #paginatorcontainer="p">
 *     <TablePager :first="p.page * p.rows" :rows="p.rows" :total-records="p.totalRecords ?? 0" :options="[10, 25, 50]"
 *       @page="p.changePageCallback" @rows="p.rowChangeCallback" />
 *   </template>
 *
 * (The slot's own ``first`` counts from 1: the 0-based first row is ``page * rows``.) Nothing shows, not even the
 * table's pager frame, while every row fits on the smallest page.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import PageScrubber from './PageScrubber.vue'

const props = defineProps<{ first: number; rows: number; totalRecords: number; options?: number[] }>()
const emit = defineEmits<{ page: [page: number]; rows: [rows: number] }>()
const { t } = useI18n()

const pageCount = computed(() => Math.ceil(props.totalRecords / Math.max(1, props.rows)))
const showSize = computed(() => !!props.options?.length && props.totalRecords > Math.min(...props.options))
</script>

<template>
  <div class="table-pager" :class="{ 'table-pager--empty': pageCount <= 1 && !showSize }">
    <PageScrubber
      v-if="pageCount > 1"
      :first="first"
      :rows="rows"
      :total-records="totalRecords"
      @update:first="(f: number) => emit('page', Math.floor(f / Math.max(1, rows)))"
    />
    <label v-if="showSize" class="table-pager__size">
      <span>{{ t('common.rowsPerPage') }}</span>
      <Select :model-value="rows" :options="options" size="small" :aria-label="t('common.rowsPerPage')" @update:model-value="(v: number) => emit('rows', v)" />
    </label>
  </div>
</template>

<style scoped>
.table-pager {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  width: 100%;
  padding: 0.5rem 0.25rem 0.25rem;
}
.table-pager--empty {
  display: none;
}
/* the table's pager frame around an empty pager: gone too (no bare bar under a one-page list) */
:global(.p-datatable-paginator-bottom:has(.table-pager--empty)) {
  display: none;
}
.table-pager__size {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
</style>
