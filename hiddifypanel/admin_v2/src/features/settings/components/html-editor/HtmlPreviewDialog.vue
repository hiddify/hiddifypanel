<script setup lang="ts">
/** "View": the support box as users see it (and its Full text, shown by "Read More"), nothing to edit. */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import EditorIcon from './EditorIcon.vue'
import SupportFrame from './SupportFrame.vue'
import { fullParts, type BoxParts } from './support-frame'

const props = defineProps<{ html: string; title: string; parts?: BoxParts }>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
const showing = ref<'lite' | 'full'>('lite')
watch(visible, (open) => {
  if (open) showing.value = 'lite'
})
/** The Full text is shown only when there is one. */
const hasFull = () => Boolean(props.parts?.full?.trim())
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
    <div v-if="hasFull()" class="hpv-tabs" role="tablist">
      <button
        v-for="v in (['lite', 'full'] as const)"
        :key="v"
        type="button"
        role="tab"
        class="hpv-tab"
        :class="{ 'hpv-tab--on': showing === v }"
        :aria-selected="showing === v"
        @click="showing = v"
      >
        {{ t(`settings.htmlEditor.variant.${v}`) }} <span class="hpv-tab__hint">· {{ t(`settings.htmlEditor.variant.${v}Hint`) }}</span>
      </button>
    </div>
    <div class="hpv">
      <SupportFrame v-if="showing === 'full' && hasFull()" key="full" :html="parts!.full!" :parts="fullParts(parts)" />
      <SupportFrame v-else key="lite" :html="html" :parts="parts" />
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
.hpv-tabs {
  display: inline-flex;
  margin-bottom: 0.6rem;
  padding: 3px;
  gap: 2px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.hpv-tab {
  padding: 0.35rem 0.8rem;
  border: 0;
  border-radius: 8px;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: transparent;
  cursor: pointer;
}
.hpv-tab--on {
  color: var(--p-primary-color);
  background: var(--p-content-background);
  box-shadow: 0 1px 3px rgb(15 23 42 / 12%);
}
.hpv-tab__hint {
  font-weight: 400;
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
