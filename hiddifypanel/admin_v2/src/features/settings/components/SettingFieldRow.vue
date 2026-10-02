<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { displayConfigLabel } from '@/shared/utils/config-labels'
import type { SettingField, SettingValue } from '@/features/settings/api'

const props = defineProps<{
  field: SettingField
  /** Messages from the server or the local pattern check. */
  errors?: string[]
  changed?: boolean
  /** Deep-link target: briefly highlighted. */
  highlighted?: boolean
  /** Show the "advanced" badge (only when advanced items are mixed with essential ones). */
  markAdvanced?: boolean
}>()

const model = defineModel<SettingValue>({ required: true })

const { t } = useI18n()

const inputId = computed(() => `setting-${props.field.key}`)
const label = computed(() => displayConfigLabel(props.field.label))
const wide = computed(() => props.field.type === 'textarea' || props.field.type === 'html')
const text = computed({
  get: () => String(model.value ?? ''),
  set: (value: string) => {
    model.value = value
  },
})
const checked = computed({
  get: () => Boolean(model.value),
  set: (value: boolean) => {
    model.value = value
  },
})
</script>

<template>
  <div
    :id="`setting-row-${field.key}`"
    class="setting-row"
    :class="{
      'setting-row--wide': wide,
      'setting-row--changed': changed,
      'setting-row--error': errors?.length,
      'setting-row--highlight': highlighted,
    }"
  >
    <div class="setting-row__info">
      <label :for="inputId" class="setting-row__label">
        {{ label }}
        <span v-if="markAdvanced && !field.essential" class="setting-badge">{{ t('settings.advancedBadge') }}</span>
        <span v-if="field.apply_mode === 'reinstall'" class="setting-badge setting-badge--warn" :title="t('settings.reinstallHint')">
          <i class="pi pi-refresh" />{{ t('settings.reinstallBadge') }}
        </span>
        <Transition name="setting-fade">
          <span v-if="changed" class="setting-badge setting-badge--changed"><i class="pi pi-pencil" />{{ t('settings.changed') }}</span>
        </Transition>
      </label>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitized server-side -->
      <p v-if="field.description" class="setting-row__desc" v-html="field.description" />
    </div>

    <div class="setting-row__control">
      <ToggleSwitch v-if="field.type === 'bool'" v-model="checked" :input-id="inputId" />
      <Select
        v-else-if="field.type === 'select'"
        v-model="text"
        :input-id="inputId"
        :options="field.choices ?? []"
        option-label="label"
        option-value="value"
        class="w-full"
        :invalid="Boolean(errors?.length)"
      />
      <Textarea
        v-else-if="wide"
        :id="inputId"
        v-model="text"
        class="w-full setting-row__textarea"
        :class="{ 'font-mono': field.type === 'html' || field.type === 'textarea' }"
        :rows="field.type === 'html' ? 6 : 4"
        auto-resize
        dir="ltr"
        :maxlength="field.maxlength"
        :invalid="Boolean(errors?.length)"
        spellcheck="false"
      />
      <InputText
        v-else
        :id="inputId"
        v-model="text"
        class="w-full"
        dir="ltr"
        :maxlength="field.maxlength"
        :invalid="Boolean(errors?.length)"
        spellcheck="false"
        autocomplete="off"
      />
      <Transition name="setting-fade">
        <ul v-if="errors?.length" class="setting-row__errors">
          <li v-for="error in errors" :key="error"><i class="pi pi-exclamation-circle" />{{ error }}</li>
        </ul>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.setting-row {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 20rem);
  gap: 0.5rem 1.5rem;
  align-items: start;
  padding: 0.9rem 0.75rem;
  border-radius: 12px;
  transition: background-color 0.25s ease;
}
.setting-row + .setting-row {
  border-top: 1px solid var(--p-content-border-color);
}
.setting-row:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.05));
}
.setting-row--wide {
  grid-template-columns: minmax(0, 1fr);
}
.setting-row--changed::before {
  content: '';
  position: absolute;
  inset-block: 0.75rem;
  inset-inline-start: 0;
  width: 3px;
  border-radius: 3px;
  background: var(--p-orange-400, #fb923c);
}
.setting-row--error::before {
  background: var(--p-red-500, #ef4444);
}
.setting-row--highlight {
  animation: setting-highlight 1.8s ease;
}
.setting-row__label {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  line-height: 1.35;
}
.setting-row__desc {
  margin: 0.3rem 0 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.setting-row__desc :deep(a) {
  color: var(--p-primary-color);
}
.setting-row__control {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.35rem;
  min-width: 0;
}
.setting-row:not(.setting-row--wide) .setting-row__control:has(> .p-toggleswitch) {
  align-items: flex-end;
}
.setting-row__textarea {
  font-size: 0.85rem;
}
.setting-row__errors {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.8rem;
  color: var(--p-red-500, #ef4444);
}
.setting-row__errors li {
  display: flex;
  gap: 0.35rem;
  align-items: baseline;
}
.setting-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.setting-badge i {
  font-size: 0.6rem;
}
.setting-badge--warn {
  color: var(--p-orange-600, #c2410c);
  background: color-mix(in srgb, var(--p-orange-400, #fb923c) 18%, transparent);
}
.setting-badge--changed {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.setting-fade-enter-active,
.setting-fade-leave-active {
  transition: opacity 0.2s ease;
}
.setting-fade-enter-from,
.setting-fade-leave-to {
  opacity: 0;
}
@keyframes setting-highlight {
  0%,
  30% {
    background: color-mix(in srgb, var(--p-primary-color) 18%, transparent);
  }
  100% {
    background: transparent;
  }
}
@media (max-width: 720px) {
  .setting-row {
    grid-template-columns: minmax(0, 1fr);
    padding-inline: 0.5rem;
  }
  .setting-row:not(.setting-row--wide):has(.p-toggleswitch) {
    grid-template-columns: minmax(0, 1fr) auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .setting-row--highlight {
    animation: none;
    outline: 2px solid var(--p-primary-color);
  }
}
</style>
