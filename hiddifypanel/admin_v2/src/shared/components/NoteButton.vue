<script setup lang="ts">
/**
 * A notebook button that shows a note on a small ruled sheet below it (Admins and Users rows, next to Edit).
 * Renders nothing when there is no note.
 */
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Popover from 'primevue/popover'

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
      <div class="note-sheet" role="dialog" :aria-label="label">
        <div class="note-sheet__title"><i class="pi pi-book" aria-hidden="true" />{{ label }}</div>
        <p class="note-sheet__text" dir="auto">{{ text }}</p>
      </div>
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
/* A leaf of a notebook: very pale yellow, ruled lines the text sits on, a red margin line at the start. */
.note-sheet {
  --line: 1.6rem;
  position: relative;
  width: min(20rem, calc(100vw - 2.5rem));
  max-height: 16rem;
  overflow: auto;
  padding: 0.35rem 0.9rem 0.6rem 2.2rem;
  border-radius: 6px;
  color: #3f3a2c;
  background-color: #fffdf0;
  background-image:
    linear-gradient(to right, transparent 1.6rem, rgb(239 68 68 / 35%) 1.6rem, rgb(239 68 68 / 35%) calc(1.6rem + 1px), transparent calc(1.6rem + 1px)),
    repeating-linear-gradient(to bottom, transparent 0, transparent calc(var(--line) - 1px), rgb(96 165 250 / 28%) calc(var(--line) - 1px), rgb(96 165 250 / 28%) var(--line));
  background-attachment: local;
  background-position: 0 0.35rem;
}
:global([dir='rtl']) .note-sheet {
  padding: 0.35rem 2.2rem 0.6rem 0.9rem;
  background-image:
    linear-gradient(to left, transparent 1.6rem, rgb(239 68 68 / 35%) 1.6rem, rgb(239 68 68 / 35%) calc(1.6rem + 1px), transparent calc(1.6rem + 1px)),
    repeating-linear-gradient(to bottom, transparent 0, transparent calc(var(--line) - 1px), rgb(96 165 250 / 28%) calc(var(--line) - 1px), rgb(96 165 250 / 28%) var(--line));
}
.note-sheet__title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  height: var(--line);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: #b45309;
}
.note-sheet__title i {
  font-size: 0.75rem;
}
.note-sheet__text {
  margin: 0;
  font-size: 0.9rem;
  line-height: var(--line);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>

<style>
/* The popover's own frame: the sheet is the content, no padding around it */
.note-pop.p-popover {
  --p-popover-content-padding: 0;
  border-color: #eadfa8;
  box-shadow: 0 12px 28px -14px rgb(120 90 20 / 45%);
}
.note-pop .p-popover-content {
  padding: 0;
}
.note-pop.p-popover::before {
  border-bottom-color: #eadfa8;
}
.note-pop.p-popover::after {
  border-bottom-color: #fffdf0;
}
</style>
