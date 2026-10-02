<script setup lang="ts">
/** Tags in a form: the same dots as the list; the choice is kept in the form until it is saved. */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Popover from 'primevue/popover'
import { useTags } from '../useTags'
import TagPicker from './TagPicker.vue'

const props = defineProps<{ disabled?: boolean }>()
const picked = defineModel<number[]>({ required: true })

const { t } = useI18n()
const { byId, label, color, load } = useTags()
void load()
const pop = ref<InstanceType<typeof Popover> | null>(null)

const MAX_SHOWN = 3
const mine = computed(() => picked.value.map((id) => byId.value.get(id)).filter((tag) => !!tag))
const names = computed(() => mine.value.map((tag) => label(tag!)).join(', '))

function toggle(id: number, on: boolean) {
  picked.value = on ? [...picked.value, id] : picked.value.filter((x) => x !== id)
}
function created(id: number) {
  if (!picked.value.includes(id)) toggle(id, true)
}
</script>

<template>
  <span class="ts">
    <button
      type="button"
      class="ts__btn"
      :disabled="props.disabled"
      :aria-label="mine.length ? `${t('tags.editTags')}: ${names}` : t('tags.addTag')"
      aria-haspopup="dialog"
      :title="mine.length ? names : t('tags.addTag')"
      @click="pop?.toggle($event)"
    >
      <span v-if="!mine.length" class="ts__ring" />
      <span v-for="(tag, i) in mine.slice(0, MAX_SHOWN)" :key="tag!.id" class="ts__dot" :style="{ '--c': color(tag!), zIndex: MAX_SHOWN - i }" />
      <span v-if="mine.length > MAX_SHOWN" class="ts__more">+{{ mine.length - MAX_SHOWN }}</span>
      <i class="pi pi-angle-down ts__caret" />
    </button>
    <Popover ref="pop" append-to="body">
      <TagPicker :selected="picked" @toggle="toggle" @create="created" />
    </Popover>
  </span>
</template>

<style scoped>
.ts {
  display: inline-flex;
  flex: none;
}
.ts__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.1rem;
  min-height: 2.5rem;
  padding: 0 0.7rem;
  border: 1px solid var(--p-inputtext-border-color, var(--p-content-border-color));
  border-radius: var(--p-inputtext-border-radius, 8px);
  background: var(--p-inputtext-background, var(--p-content-background));
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.ts__btn:hover:not(:disabled),
.ts__btn:focus-visible {
  border-color: var(--p-primary-color);
  outline: none;
}
.ts__btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.ts__ring {
  width: 0.95rem;
  height: 0.95rem;
  border: 1.5px solid color-mix(in srgb, var(--p-text-color) 38%, transparent);
  border-radius: 999px;
}
.ts__dot {
  position: relative;
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 999px;
  background: var(--c);
  box-shadow: 0 0 0 2px var(--p-content-background);
}
.ts__dot + .ts__dot {
  margin-inline-start: -0.38rem;
}
.ts__more {
  margin-inline-start: 0.3rem;
  font-size: 0.68rem;
  font-weight: 600;
}
.ts__caret {
  margin-inline-start: 0.4rem;
  font-size: 0.75rem;
}
</style>
