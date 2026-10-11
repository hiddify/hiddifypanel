<template>
  <div class="relative">
    <Button icon="pi pi-copy" text rounded size="small" class="!absolute top-1 end-1" :aria-label="t('common.copy')" @click="copy" />
    <pre class="cb" dir="ltr">{{ text }}</pre>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'

const props = defineProps<{ text: string }>()
const { t } = useI18n()
const toast = useToast()

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
    toast.add({ severity: 'success', summary: t('common.copy'), life: 1500 })
  } catch {
    /* clipboard blocked: the text is selectable */
  }
}
</script>

<style scoped>
.cb {
  margin: 0;
  max-height: 60vh;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
