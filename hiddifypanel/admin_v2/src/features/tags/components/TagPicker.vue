<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { isSuperAdmin } from '@/core/panelShell'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { COLOR_ORDER, TAG_COLORS, useTags } from '../useTags'
import type { Tag, TagColor } from '../api'

defineProps<{
  /** Tags the account(s) have. */
  selected: number[]
  /** Some, but not all, of the selected accounts have these (bulk). */
  partial?: number[]
  title?: string
  hint?: string
}>()
const emit = defineEmits<{ toggle: [id: number, on: boolean]; create: [id: number] }>()

const { t } = useI18n()
const { tags, label, color, create, update, remove } = useTags()
const dangerConfirm = useDangerConfirm()

const name = ref('')
const newColor = ref<TagColor>('blue')
const busy = ref(false)
const error = ref('')

// Only a super admin changes a tag's name or color (anyone can make a new one).
const editing = ref<number | null>(null)
const editName = ref('')
const editColor = ref<TagColor>('blue')
function startEdit(tag: Tag) {
  editing.value = tag.id
  editName.value = label(tag)
  editColor.value = tag.color
  error.value = ''
}
async function saveEdit() {
  if (editing.value === null || !editName.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await update(editing.value, editName.value.trim(), editColor.value)
    editing.value = null
  } catch (err) {
    error.value = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? t('tags.saveFailed')
  } finally {
    busy.value = false
  }
}
function askDelete(tag: Tag) {
  dangerConfirm({
    header: t('tags.delete'),
    message: t('tags.deleteConfirm', { name: label(tag) }),
    acceptLabel: t('tags.delete'),
    accept: async () => {
      await remove(tag.id)
      editing.value = null
    },
  })
}

async function add() {
  const text = name.value.trim()
  if (!text || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const id = await create(text, newColor.value)
    name.value = ''
    emit('create', id)
  } catch (err) {
    error.value = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? t('tags.saveFailed')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="picker">
    <p class="picker__title">{{ title ?? t('tags.pick') }}</p>
    <p class="picker__hint">{{ hint ?? t('tags.pickHint') }}</p>

    <ul class="picker__list" role="group" :aria-label="title ?? t('tags.pick')">
      <li v-for="tag in tags" :key="tag.id" class="picker__item">
        <form v-if="editing === tag.id" class="picker__edit" @submit.prevent="saveEdit">
          <div class="picker__swatches" role="radiogroup" :aria-label="t('tags.color')">
            <button
              v-for="c in COLOR_ORDER"
              :key="c"
              type="button"
              class="picker__swatch"
              :class="{ 'picker__swatch--on': editColor === c }"
              :style="{ '--c': TAG_COLORS[c] }"
              role="radio"
              :aria-checked="editColor === c"
              :aria-label="t(`tags.colors.${c}`)"
              @click="editColor = c"
            />
          </div>
          <div class="picker__create">
            <InputText v-model="editName" size="small" maxlength="60" class="picker__input" :aria-label="t('tags.rename')" autofocus />
            <Button type="submit" icon="pi pi-check" size="small" rounded :loading="busy" :disabled="!editName.trim()" :aria-label="t('tags.save')" />
            <Button v-if="!tag.is_default" type="button" icon="pi pi-trash" size="small" rounded text severity="danger" :aria-label="t('tags.delete')" @click="askDelete(tag)" />
            <Button type="button" icon="pi pi-times" size="small" rounded text severity="secondary" :aria-label="t('common.cancel')" @click="editing = null" />
          </div>
        </form>
        <template v-else>
        <button
          type="button"
          class="picker__row"
          :class="{ 'picker__row--on': selected.includes(tag.id) }"
          role="checkbox"
          :aria-checked="selected.includes(tag.id) ? 'true' : partial?.includes(tag.id) ? 'mixed' : 'false'"
          @click="emit('toggle', tag.id, !selected.includes(tag.id))"
        >
          <span class="picker__dot" :class="{ 'picker__dot--on': selected.includes(tag.id), 'picker__dot--part': partial?.includes(tag.id) }" :style="{ '--c': color(tag) }">
            <i v-if="selected.includes(tag.id)" class="pi pi-check" />
            <i v-else-if="partial?.includes(tag.id)" class="pi pi-minus" />
          </span>
          <span class="picker__name">{{ label(tag) }}</span>
          <span v-if="tag.count" class="picker__count">{{ tag.count }}</span>
        </button>
        <Button v-if="isSuperAdmin" icon="pi pi-pencil" text rounded size="small" severity="secondary" class="picker__pencil" :aria-label="t('tags.edit')" v-tooltip.top="t('tags.edit')" @click.stop="startEdit(tag)" />
        </template>
      </li>
    </ul>

    <form class="picker__new" @submit.prevent="add">
      <div class="picker__swatches" role="radiogroup" :aria-label="t('tags.color')">
        <button
          v-for="c in COLOR_ORDER"
          :key="c"
          type="button"
          class="picker__swatch"
          :class="{ 'picker__swatch--on': newColor === c }"
          :style="{ '--c': TAG_COLORS[c] }"
          role="radio"
          :aria-checked="newColor === c"
          :aria-label="t(`tags.colors.${c}`)"
          :title="t(`tags.colors.${c}`)"
          @click="newColor = c"
        />
      </div>
      <div class="picker__create">
        <InputText v-model="name" size="small" maxlength="60" class="picker__input" :placeholder="t('tags.namePlaceholder')" :aria-label="t('tags.newTag')" />
        <Button type="submit" icon="pi pi-plus" size="small" rounded :loading="busy" :disabled="!name.trim()" :aria-label="t('tags.create')" />
      </div>
      <small v-if="error" class="picker__error">{{ error }}</small>
    </form>
  </div>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  width: min(18rem, calc(100vw - 2rem));
}
.picker__title {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 700;
}
.picker__hint {
  margin: 0 0 0.25rem;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.picker__list {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  max-height: 15rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}
.picker__item {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}
.picker__item > .picker__row {
  flex: 1;
  min-width: 0;
}
.picker__edit {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.4rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--p-text-color) 5%, transparent);
}
.picker__pencil {
  flex: none;
  opacity: 0.55;
}
.picker__item:hover .picker__pencil,
.picker__pencil:focus-visible {
  opacity: 1;
}
.picker__row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: 100%;
  padding: 0.5rem 0.55rem;
  border: none;
  border-radius: 0.6rem;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.88rem;
  text-align: start;
  cursor: pointer;
  transition: background 0.15s ease;
}
.picker__row:hover,
.picker__row:focus-visible {
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
  outline: none;
}
.picker__dot {
  display: inline-grid;
  place-items: center;
  flex: none;
  width: 1.15rem;
  height: 1.15rem;
  border: 2px solid var(--c);
  border-radius: 999px;
  color: #fff;
  font-size: 0.55rem;
  transition: background 0.15s ease, transform 0.15s ease;
}
.picker__dot--on {
  background: var(--c);
}
.picker__dot--part {
  background: color-mix(in srgb, var(--c) 45%, transparent);
}
.picker__row:active .picker__dot {
  transform: scale(0.88);
}
.picker__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker__count {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.picker__new {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.3rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--p-content-border-color);
}
.picker__swatches {
  display: flex;
  gap: 0.55rem;
  padding-inline: 0.2rem;
}
.picker__swatch {
  width: 1.3rem;
  height: 1.3rem;
  border: 2px solid transparent;
  border-radius: 999px;
  background: var(--c);
  box-shadow: inset 0 0 0 2px var(--p-content-background);
  cursor: pointer;
  transition: transform 0.15s ease;
}
.picker__swatch:hover {
  transform: scale(1.12);
}
.picker__swatch--on {
  border-color: var(--c);
  transform: scale(1.12);
}
.picker__create {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.picker__input {
  flex: 1;
  min-width: 0;
}
.picker__error {
  color: var(--p-red-500);
}
</style>
