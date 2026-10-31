<script setup lang="ts">
/** "View": the support box as users see it, nothing to edit. */
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import EditorIcon from './EditorIcon.vue'
import SupportFrame from './SupportFrame.vue'

defineProps<{ html: string; title: string }>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :style="{ width: 'min(30rem, calc(100vw - 2rem))' }" :breakpoints="{ '540px': '100vw' }">
    <template #header>
      <div class="hpv-head">
        <span class="hpv-head__icon" aria-hidden="true"><EditorIcon name="eye" /></span>
        <div class="min-w-0">
          <div class="hpv-head__title">{{ t('settings.htmlEditor.previewTitle') }}</div>
          <div class="hpv-head__sub">{{ title }}</div>
        </div>
      </div>
    </template>
    <div class="hpv">
      <SupportFrame :html="html" />
    </div>
    <p class="hpv-note"><i class="pi pi-info-circle" />{{ t('settings.htmlEditor.previewNote') }}</p>
    <template #footer>
      <Button :label="t('settings.htmlEditor.close')" severity="secondary" autofocus @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.hpv-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.hpv-head__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  border-radius: 12px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.hpv-head__title {
  font-size: 1.1rem;
  font-weight: 700;
}
.hpv-head__sub {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.hpv {
  height: min(60vh, 32rem);
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
  overflow: hidden;
}
.hpv-note {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.75rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
</style>
