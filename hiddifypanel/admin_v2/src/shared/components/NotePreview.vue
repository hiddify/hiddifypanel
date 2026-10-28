<script setup lang="ts">
/**
 * A note shown by its first words next to a name ("first three words …"); when it was cut, the whole note opens on a
 * notebook sheet on mouse hover, a tap or Enter, and stays open while the pointer is on the sheet. A short note is
 * shown whole and opens nothing.
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import Popover from 'primevue/popover'
import NoteSheet from '@/shared/components/NoteSheet.vue'

const props = withDefaults(
  defineProps<{
    note: string | null | undefined
    /** The sheet's title: "Note" in the page's own wording */
    label: string
    words?: number
  }>(),
  { words: 3 },
)

const text = computed(() => String(props.note ?? '').trim())
const parts = computed(() => text.value.split(/\s+/).filter(Boolean))
const cut = computed(() => parts.value.length > props.words)
const preview = computed(() => parts.value.slice(0, props.words).join(' '))

const sheet = ref<InstanceType<typeof Popover> | null>(null)
const open = ref(false)
let closing: number | undefined
function show(e: Event) {
  if (!cut.value) return
  window.clearTimeout(closing)
  if (!open.value) sheet.value?.show(e, e.currentTarget as HTMLElement)
}
/** A short delay: the pointer can move from the words onto the sheet (to scroll a long note) without it closing. */
function hideSoon() {
  window.clearTimeout(closing)
  closing = window.setTimeout(() => sheet.value?.hide(), 180)
}
/** Hover is for a mouse only: a tap also sends an emulated mouseenter, which would open the sheet that the tap's click
 * then closes again. On touch the click alone opens and closes it. */
/** A tap, a click, Enter or Space. Not on focus: a tap focuses first, and the click would then close it again. */
function toggle(e: Event) {
  if (!cut.value) return
  if (open.value) sheet.value?.hide()
  else show(e)
}
function hoverIn(e: PointerEvent) {
  if (e.pointerType === 'mouse') show(e)
}
function hoverOut(e: PointerEvent) {
  if (e.pointerType === 'mouse') hideSoon()
}
onBeforeUnmount(() => window.clearTimeout(closing))
</script>

<template>
  <span
    v-if="text"
    class="note-preview"
    :class="{ 'note-preview--open': open, 'note-preview--cut': cut }"
    :tabindex="cut ? 0 : undefined"
    :role="cut ? 'button' : undefined"
    :aria-haspopup="cut ? 'dialog' : undefined"
    :aria-expanded="cut ? open : undefined"
    :aria-label="cut ? `${label}: ${text}` : undefined"
    @pointerenter="hoverIn"
    @pointerleave="hoverOut"
    @blur="hideSoon"
    @click.stop="toggle"
    @keydown.enter.prevent="toggle"
    @keydown.space.prevent="toggle"
  >
    <slot :text="preview">{{ preview }}</slot><span v-if="cut" class="note-preview__more" aria-hidden="true"> …</span>
  </span>
  <Popover v-if="cut" ref="sheet" class="note-pop" @show="open = true" @hide="open = false">
    <div @pointerenter="hoverIn" @pointerleave="hoverOut">
      <NoteSheet :label="label" :text="text" />
    </div>
  </Popover>
</template>

<style scoped>
.note-preview {
  border-radius: 4px;
  outline-offset: 1px;
}
.note-preview--cut {
  cursor: help;
}
.note-preview--cut:hover,
.note-preview--open {
  color: #b45309;
}
.note-preview:focus-visible {
  outline: 2px solid var(--p-primary-color);
}
.note-preview__more {
  font-weight: 700;
  letter-spacing: 0.05em;
}
</style>
