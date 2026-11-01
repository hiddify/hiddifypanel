<script setup lang="ts">
/** Full mode's template gallery: ready-made support box designs, inserted at the caret or replacing the text. */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import EditorIcon from './EditorIcon.vue'
import SupportFrame from './SupportFrame.vue'
import { TEMPLATES, type SupportTemplate } from './templates'

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ pick: [html: string, replace: boolean] }>()

const { t } = useI18n()
const chosen = ref<SupportTemplate>(TEMPLATES[0])

function pick(replace: boolean) {
  emit('pick', chosen.value.html, replace)
  visible.value = false
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :style="{ width: 'min(60rem, calc(100vw - 2rem))' }" :breakpoints="{ '720px': '100vw' }">
    <template #header>
      <div class="tg-head">
        <span class="tg-head__icon" aria-hidden="true"><EditorIcon name="template" /></span>
        <div>
          <div class="tg-head__title">{{ t('settings.htmlEditor.templates.title') }}</div>
          <div class="tg-head__sub">{{ t('settings.htmlEditor.templates.note') }}</div>
        </div>
      </div>
    </template>
    <div class="tg">
      <div class="tg__list" role="listbox" :aria-label="t('settings.htmlEditor.templates.title')">
        <button
          v-for="tpl in TEMPLATES"
          :key="tpl.id"
          type="button"
          role="option"
          class="tg__item"
          :class="{ 'tg__item--on': chosen.id === tpl.id }"
          :aria-selected="chosen.id === tpl.id"
          @click="chosen = tpl"
          @dblclick="pick(false)"
        >
          {{ t(`settings.htmlEditor.templates.names.${tpl.id}`) }}
        </button>
      </div>
      <div class="tg__preview">
        <SupportFrame :key="chosen.id" :html="chosen.html" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('settings.htmlEditor.cancel')" severity="secondary" text @click="visible = false" />
      <Button :label="t('settings.htmlEditor.templates.replace')" icon="pi pi-sync" severity="secondary" outlined @click="pick(true)" />
      <Button :label="t('settings.htmlEditor.templates.insert')" icon="pi pi-plus" autofocus @click="pick(false)" />
    </template>
  </Dialog>
</template>

<style scoped>
.tg-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.tg-head__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #f59f00, #e8590c);
  box-shadow: 0 6px 16px -8px #e8590c;
}
.tg-head__title {
  font-size: 1.1rem;
  font-weight: 700;
}
.tg-head__sub {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.tg {
  display: grid;
  grid-template-columns: 14rem minmax(0, 1fr);
  gap: 1rem;
  height: min(60vh, 34rem);
}
.tg__list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
}
.tg__item {
  padding: 0.6rem 0.8rem;
  border: 1px solid transparent;
  border-radius: 10px;
  font: inherit;
  font-size: 0.875rem;
  text-align: start;
  color: var(--p-text-color);
  background: transparent;
  cursor: pointer;
  transition: background-color 0.15s;
}
.tg__item:hover {
  background: color-mix(in srgb, var(--p-text-color) 6%, transparent);
}
.tg__item--on {
  font-weight: 600;
  color: var(--p-primary-color);
  border-color: color-mix(in srgb, var(--p-primary-color) 35%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.tg__preview {
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
  overflow: hidden;
}
@media (max-width: 720px) {
  .tg {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    height: calc(100dvh - 12rem);
  }
  .tg__list {
    flex-direction: row;
    overflow-x: auto;
  }
  .tg__item {
    white-space: nowrap;
  }
}
</style>
