<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiSelect from 'primevue/multiselect'
import { ANY_TAG, useTags } from '../useTags'

const props = defineProps<{
  /** The tag ids of every row on the page, to count each option. */
  items: { tags: number[] }[]
}>()
/** Picked tag ids; `ANY_TAG` (0) means "has at least one tag". */
const picked = defineModel<number[]>({ required: true })

const { t } = useI18n()
const { tags, load, label, color } = useTags()
onMounted(() => void load())

const options = computed(() => {
  const counts = new Map<number, number>()
  for (const item of props.items) for (const id of item.tags) counts.set(id, (counts.get(id) ?? 0) + 1)
  return [
    { id: ANY_TAG, label: t('tags.tagged'), color: '', count: props.items.filter((item) => item.tags.length).length },
    ...tags.value.map((tag) => ({ id: tag.id, label: label(tag), color: color(tag), count: counts.get(tag.id) ?? 0 })),
  ]
})
const byId = computed(() => new Map(options.value.map((o) => [o.id, o])))
</script>

<template>
  <MultiSelect
    v-model="picked"
    :options="options"
    option-label="label"
    option-value="id"
    :show-toggle-all="false"
    :max-selected-labels="0"
    :placeholder="t('tags.filterLabel')"
    :aria-label="t('tags.filterLabel')"
    class="tag-filter"
    :class="{ 'tag-filter--on': picked.length }"
    :pt="{ overlay: { class: 'tag-filter__overlay' } }"
  >
    <!-- Nothing picked: the placeholder says what this is -->
    <template v-if="picked.length" #value="{ value }">
      <span class="tag-filter__value">
        <i class="pi pi-tag" />
        <template v-if="value?.length">
          <span class="tag-filter__dots">
            <template v-for="id in (value as number[]).slice(0, 3)" :key="id">
              <i v-if="id === ANY_TAG" class="pi pi-star-fill tag-filter__star" />
              <span v-else class="tag-filter__dot" :style="{ '--c': byId.get(id)?.color }" />
            </template>
          </span>
          <span v-if="value.length === 1">{{ byId.get(value[0])?.label }}</span>
          <b v-else>{{ value.length }}</b>
        </template>
      </span>
    </template>
    <template #option="{ option }">
      <span class="tag-filter__option">
        <i v-if="option.id === ANY_TAG" class="pi pi-star-fill tag-filter__star" />
        <span v-else class="tag-filter__dot" :style="{ '--c': option.color }" />
        <span class="tag-filter__label">{{ option.label }}</span>
        <small>{{ option.count }}</small>
      </span>
    </template>
  </MultiSelect>
</template>

<style scoped>
.tag-filter {
  min-width: 10.5rem;
  max-width: 100%;
}
.tag-filter--on {
  border-color: var(--p-primary-color);
}
.tag-filter__value {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.tag-filter__value > .pi-tag {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.tag-filter__dots {
  display: inline-flex;
}
.tag-filter__dots .tag-filter__dot + .tag-filter__dot,
.tag-filter__dots .tag-filter__star + .tag-filter__dot {
  margin-inline-start: -0.3rem;
}
.tag-filter__dot {
  display: inline-block;
  flex: none;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 999px;
  background: var(--c);
  box-shadow: 0 0 0 2px var(--p-content-background);
}
.tag-filter__star {
  color: #ffbe0b;
  font-size: 0.8rem;
}
.tag-filter__option {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}
.tag-filter__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tag-filter__option small {
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
</style>
