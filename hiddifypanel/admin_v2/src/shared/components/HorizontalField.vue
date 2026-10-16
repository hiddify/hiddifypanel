<script setup lang="ts">
defineProps<{
  label: string
  inputId?: string
  hint?: string
  /** Label above the input at every width (narrow places such as popovers). */
  stacked?: boolean
}>()
</script>

<template>
  <div class="flex flex-col gap-2 mb-4" :class="{ 'md:flex-row md:items-start': !stacked }">
    <label :for="inputId" class="font-semibold shrink-0" :class="{ 'md:w-48 md:pt-2': !stacked }">{{ label }}</label>
    <div class="flex-auto min-w-0">
      <slot />
      <small v-if="hint" class="block mt-1 text-muted-color">{{ hint }}</small>
    </div>
  </div>
</template>
