<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Popover from 'primevue/popover'
import { useToast } from 'primevue/usetoast'
import { tagsApi, type TagKind } from '../api'
import { useTags } from '../useTags'
import TagPicker from './TagPicker.vue'

const props = defineProps<{ kind: TagKind; uuid: string; ids: number[] }>()
const emit = defineEmits<{ changed: [ids: number[]] }>()

const { t } = useI18n()
const toast = useToast()
const { byId, label, color, bump } = useTags()
const pop = ref<InstanceType<typeof Popover> | null>(null)

const MAX_SHOWN = 3
const mine = computed(() => props.ids.map((id) => byId.value.get(id)).filter((tag) => !!tag))
const shown = computed(() => mine.value.slice(0, MAX_SHOWN))
const names = computed(() => mine.value.map((tag) => label(tag!)).join(', '))

async function save(next: number[], added: number[], removed: number[]) {
  const before = props.ids
  emit('changed', next)
  bump(added, removed)
  try {
    emit('changed', await tagsApi.assign(props.kind, props.uuid, next))
  } catch {
    emit('changed', before)
    bump(removed, added)
    toast.add({ severity: 'error', summary: t('tags.saveFailed'), life: 4000 })
  }
}
function toggle(id: number, on: boolean) {
  void save(on ? [...props.ids, id] : props.ids.filter((x) => x !== id), on ? [id] : [], on ? [] : [id])
}
/** A tag just created for this account is put on it right away. */
function created(id: number) {
  if (!props.ids.includes(id)) toggle(id, true)
}
</script>

<template>
  <span class="dots">
    <button
      type="button"
      class="dots__btn"
      :class="{ 'dots__btn--empty': !shown.length }"
      :aria-label="shown.length ? `${t('tags.editTags')}: ${names}` : t('tags.addTag')"
      aria-haspopup="dialog"
      :title="shown.length ? names : t('tags.addTag')"
      @click.stop="pop?.toggle($event)"
    >
      <span v-if="!shown.length" class="dots__ring" />
      <span v-for="(tag, i) in shown" :key="tag!.id" class="dots__dot" :style="{ '--c': color(tag!), zIndex: MAX_SHOWN - i }" />
      <span v-if="mine.length > MAX_SHOWN" class="dots__more">+{{ mine.length - MAX_SHOWN }}</span>
    </button>
    <Popover ref="pop" append-to="body">
      <TagPicker :selected="ids" @toggle="toggle" @create="created" />
    </Popover>
  </span>
</template>

<style scoped>
.dots {
  display: inline-flex;
  flex: none;
}
.dots__btn {
  display: inline-flex;
  align-items: center;
  min-width: 1.75rem;
  height: 1.75rem;
  padding: 0 0.3rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition: background 0.15s ease;
}
.dots__btn:hover,
.dots__btn:focus-visible {
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
  outline: none;
}
.dots__ring {
  width: 0.95rem;
  height: 0.95rem;
  border: 1.5px solid color-mix(in srgb, var(--p-text-color) 38%, transparent);
  border-radius: 999px;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.dots__btn--empty:hover .dots__ring {
  border-color: var(--p-primary-color);
  transform: scale(1.1);
}
.dots__dot {
  position: relative;
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 999px;
  background: var(--c);
  box-shadow: 0 0 0 2px var(--p-content-background);
}
.dots__dot + .dots__dot {
  margin-inline-start: -0.38rem;
}
.dots__more {
  margin-inline-start: 0.3rem;
  font-size: 0.68rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
