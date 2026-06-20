<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="mb-5">
    <h2 class="text-2xl font-semibold m-0">{{ title }}</h2>
    <p v-if="subtitle" class="text-muted-color mt-2 mb-0">{{ subtitle }}</p>
  </div>
</template>
