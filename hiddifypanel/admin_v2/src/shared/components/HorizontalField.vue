<script setup lang="ts">
defineProps<{
  label: string
  inputId?: string
  hint?: string
}>()
</script>

<template>
  <div class="flex flex-col md:flex-row md:items-start gap-2 mb-4">
    <label :for="inputId" class="md:w-48 md:pt-2 font-semibold shrink-0">{{ label }}</label>
    <div class="flex-auto min-w-0">
      <slot />
      <small v-if="hint" class="block mt-1 text-muted-color">{{ hint }}</small>
    </div>
  </div>
</template>
