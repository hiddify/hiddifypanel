<script setup lang="ts">
/**
 * A notebook button that shows a note on a small ruled sheet below it (Admins and Users rows, next to Edit).
 * Renders nothing when there is no note.
 */
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import NoteSheet from '@/shared/components/NoteSheet.vue'

const props = defineProps<{
  note: string | null | undefined
  /** The button's label (and the sheet's title): "Note" in the page's own wording */
  label: string
}>()

const sheet = ref<InstanceType<typeof Popover> | null>(null)
const open = ref(false)
const text = computed(() => String(props.note ?? '').trim())
</script>

<template>
  <template v-if="text">
    <Button
      icon="pi pi-book"
      text
      rounded
      size="small"
      class="note-btn"
      :class="{ 'note-btn--open': open }"
      :aria-label="label"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="(e: Event) => sheet?.toggle(e)"
    />
    <Popover ref="sheet" class="note-pop" @show="open = true" @hide="open = false">
      <NoteSheet :label="label" :text="text" />
    </Popover>
  </template>
</template>

<style scoped>
.note-btn {
  color: #b45309;
}
.note-btn--open {
  background: color-mix(in srgb, #f59e0b 16%, transparent);
}
</style>
