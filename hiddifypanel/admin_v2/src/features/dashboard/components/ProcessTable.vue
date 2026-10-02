<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardProcess } from '@/core/api/generated'
import MetricBar from './MetricBar.vue'

const props = withDefaults(
  defineProps<{
    processes: DashboardProcess[]
    color: string
    /** Formats the trailing reading for each row. */
    formatter: (process: DashboardProcess) => string
    limit?: number
  }>(),
  { limit: 12 },
)

const rows = computed(() => props.processes.filter((row) => row.name.trim()).slice(0, props.limit))
const scale = computed(() => Math.max(1, ...rows.value.map((row) => row.percent)))
</script>

<template>
  <div class="processes">
    <MetricBar
      v-for="row in rows"
      :key="row.name"
      :label="row.name"
      :percent="(row.percent / scale) * 100"
      :value="formatter(row)"
      :color="color"
      compact
    />
  </div>
</template>

<style scoped>
.processes {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
</style>
