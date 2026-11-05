<script setup lang="ts">
/** How often the used data goes back to zero: four equal buttons (2×2 on phones) and what the choice means. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MODE_ICON, USER_MODES, type UserMode } from '@/features/users/api'

const props = withDefaults(
  defineProps<{
    disabled?: boolean
    /** Said after the meaning, e.g. when the next reset is */
    after?: string | null
    /** Translation keys of the meanings (`<hintKey>.<mode>`): admins count their users' traffic, not a package. */
    hintKey?: string
  }>(),
  { after: null, hintKey: 'users.modeHint' },
)
const mode = defineModel<UserMode>({ required: true })
const { t } = useI18n()
const options = computed(() => USER_MODES.map((value) => ({ value, label: t(`users.mode.${value}`), icon: MODE_ICON[value] })))
</script>

<template>
  <div class="rmode">
    <span class="font-medium">{{ t('users.form.mode') }}</span>
    <div class="rmode__options" role="radiogroup" :aria-label="t('users.form.mode')">
      <button
        v-for="m in options"
        :key="m.value"
        type="button"
        role="radio"
        class="rmode__option"
        :class="{ 'rmode__option--on': mode === m.value }"
        :aria-checked="mode === m.value"
        :disabled="disabled"
        @click="mode = m.value"
      >
        <i :class="m.icon" /><span>{{ m.label }}</span>
      </button>
    </div>
    <small class="text-muted-color">
      {{ t(`${props.hintKey}.${mode}`) }}
      <template v-if="after"> · {{ after }}</template>
    </small>
  </div>
</template>

<style scoped>
.rmode {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.rmode__options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.35rem;
  padding: 0.25rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.rmode__option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: 0;
  padding: 0.45rem 0.4rem;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}
.rmode__option span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rmode__option i {
  font-size: 0.8rem;
}
.rmode__option--on {
  color: var(--p-primary-color);
  font-weight: 600;
  background: var(--p-content-background);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
}
@media (max-width: 640px) {
  .rmode__options {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
