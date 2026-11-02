<script setup lang="ts">
/**
 * A form's error from the server, where the admin sees it: each new error scrolls into view and takes the focus
 * (screen readers read it), so a long dialog on a phone does not fail out of sight below the fold.
 */
import { nextTick, ref, watch } from 'vue'
import Message from 'primevue/message'

const props = defineProps<{ error: string | null; title?: string }>()
const box = ref<HTMLElement | null>(null)

watch(
  () => props.error,
  async (error) => {
    if (!error) return
    await nextTick()
    box.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    box.value?.focus({ preventScroll: true })
  },
)
</script>

<template>
  <div v-if="error" ref="box" class="form-error" role="alert" tabindex="-1">
    <Message severity="error" :closable="false" icon="pi pi-exclamation-circle">
      <div class="form-error__body">
        <b v-if="title">{{ title }}</b>
        <span class="whitespace-pre-line">{{ error }}</span>
      </div>
    </Message>
  </div>
</template>

<style scoped>
.form-error {
  outline: none;
  scroll-margin-block: 1rem;
}
.form-error__body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
</style>
