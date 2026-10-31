<script setup lang="ts">
/** An HTML setting (the users' support box): "View" shows it as users see it, "HTML Editor" opens the panel's editor. */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import EditorIcon from './EditorIcon.vue'
import HtmlEditorDialog from './HtmlEditorDialog.vue'
import HtmlPreviewDialog from './HtmlPreviewDialog.vue'

defineProps<{ inputId: string; title: string; maxlength?: number; invalid?: boolean }>()
const model = defineModel<string>({ required: true })

const { t } = useI18n()
const viewing = ref(false)
const editing = ref(false)
</script>

<template>
  <div class="hfc" :class="{ 'hfc--invalid': invalid }">
    <button type="button" class="hfc__btn hfc__btn--view" @click="viewing = true">
      <EditorIcon name="eye" />
      <span>{{ t('settings.htmlEditor.viewButton') }}</span>
    </button>
    <button :id="inputId" type="button" class="hfc__btn hfc__btn--edit" @click="editing = true">
      <EditorIcon name="code" />
      <span>{{ t('settings.htmlEditor.editButton') }}</span>
    </button>
  </div>
  <HtmlPreviewDialog v-model:visible="viewing" :html="model" :title="title" />
  <HtmlEditorDialog v-model:visible="editing" v-model="model" :title="title" :maxlength="maxlength" />
</template>

<style scoped>
.hfc {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.hfc__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.6rem;
  padding: 0.5rem 0.9rem;
  border-radius: 10px;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    box-shadow 0.15s,
    transform 0.15s;
}
.hfc__btn:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.hfc__btn:active {
  transform: translateY(1px);
}
.hfc__btn--view {
  border: 1px solid var(--p-content-border-color);
  color: var(--p-text-color);
  background: var(--p-content-background);
}
.hfc__btn--view:hover {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
.hfc__btn--edit {
  border: 1px solid transparent;
  color: var(--p-primary-contrast-color);
  background: linear-gradient(135deg, var(--p-primary-500), var(--p-primary-700));
  box-shadow: 0 6px 16px -10px var(--p-primary-600);
}
.hfc__btn--edit:hover {
  box-shadow: 0 8px 20px -10px var(--p-primary-600);
  filter: brightness(1.06);
}
.hfc--invalid .hfc__btn--view {
  border-color: var(--p-red-400, #f87171);
}
</style>
