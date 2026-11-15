<script setup lang="ts">
/**
 * A small window for the dashboard's pickers, in the style of iOS: a popover from its button on a wide screen, a
 * bottom sheet on a phone (pulled down to close, as in iOS). Open it with ``open(event)``.
 */
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Popover from 'primevue/popover'

defineProps<{ title: string; icon?: string }>()
const emit = defineEmits<{ hide: [] }>()
const { t } = useI18n()

const phoneQuery = window.matchMedia('(max-width: 575px)')
const isPhone = ref(phoneQuery.matches)
const onPhone = (e: MediaQueryListEvent) => (isPhone.value = e.matches)
phoneQuery.addEventListener('change', onPhone)
onBeforeUnmount(() => phoneQuery.removeEventListener('change', onPhone))

const pop = ref<InstanceType<typeof Popover> | null>(null)
const visible = ref(false)

function open(event: Event) {
  if (isPhone.value) visible.value = true
  else pop.value?.toggle(event)
}
function close() {
  visible.value = false
  pop.value?.hide()
}
defineExpose({ open, close })

// --- a phone: pull the sheet down to close it ------------------------------------------------------------------
const sheet = ref<HTMLElement | null>(null)
const frame = () => sheet.value?.closest<HTMLElement>('.p-dialog') ?? null
let drag: { y: number; dy: number; active: boolean; t: number; v: number } | null = null

function onTouchStart(e: TouchEvent) {
  if (e.touches.length !== 1) return
  const body = sheet.value?.querySelector('.dsh__body')
  if (body?.contains(e.target as Node) && body.scrollTop > 0) return
  drag = { y: e.touches[0]!.clientY, dy: 0, active: false, t: performance.now(), v: 0 }
}
function onTouchMove(e: TouchEvent) {
  if (!drag) return
  const dy = e.touches[0]!.clientY - drag.y
  if (!drag.active) {
    if (Math.abs(dy) < 6) return
    if (dy < 0) {
      drag = null
      return
    }
    drag.active = true
    const el = frame()
    if (el) el.style.transition = 'none'
  }
  if (e.cancelable) e.preventDefault()
  const now = performance.now()
  drag.v = (Math.max(0, dy) - drag.dy) / Math.max(1, now - drag.t)
  drag.t = now
  drag.dy = Math.max(0, dy)
  const el = frame()
  if (el) el.style.transform = `translateY(${drag.dy}px)`
}
function onTouchEnd() {
  const d = drag
  drag = null
  if (!d?.active) return
  const el = frame()
  if (d.dy > Math.min(130, (el?.offsetHeight ?? 500) * 0.25) || d.v > 0.5) {
    visible.value = false
    return
  }
  if (el) {
    el.style.transition = 'transform 0.42s cubic-bezier(0.32, 0.72, 0, 1)'
    el.style.transform = ''
  }
}
</script>

<template>
  <Dialog v-if="isPhone" v-model:visible="visible" modal dismissable-mask :draggable="false" position="bottom" class="dash-sheet" @hide="emit('hide')">
    <template #container="{ closeCallback }">
      <div ref="sheet" class="dsh dsh--sheet" role="document" @touchstart.passive="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd" @touchcancel="onTouchEnd">
        <span class="dsh__grabber" aria-hidden="true" />
        <header class="dsh__head">
          <span class="dsh__side"><slot name="lead" /></span>
          <h3 class="dsh__title">{{ title }}</h3>
          <span class="dsh__side dsh__side--end">
            <button type="button" class="dsh__round dsh__done" :aria-label="t('dashboard.chartStyle.done')" @click="closeCallback"><i class="pi pi-times" /></button>
          </span>
        </header>
        <div class="dsh__body"><slot :close="close" /></div>
      </div>
    </template>
  </Dialog>
  <Popover v-else ref="pop" class="dash-pop" @hide="emit('hide')">
    <div class="dsh" role="dialog" :aria-label="title">
      <header class="dsh__head">
        <span class="dsh__side"><slot name="lead" /></span>
        <h3 class="dsh__title">{{ title }}</h3>
        <span class="dsh__side dsh__side--end">
          <button type="button" class="dsh__round dsh__done" :aria-label="t('dashboard.chartStyle.done')" @click="close"><i class="pi pi-times" /></button>
        </span>
      </header>
      <div class="dsh__body"><slot :close="close" /></div>
    </div>
  </Popover>
</template>

<style scoped>
/* iOS 27: a sheet of glass that floats a little off the edges, a centred title between two round glass buttons */
.dsh {
  --dsh-group: color-mix(in srgb, var(--p-text-color) 5%, transparent);
  --dsh-hair: color-mix(in srgb, var(--p-text-color) 10%, transparent);
  display: flex;
  flex-direction: column;
  width: min(24rem, calc(100vw - 2rem));
  max-height: min(38rem, calc(100vh - 7rem));
  color: var(--p-text-color);
}
.dsh--sheet {
  width: calc(100vw - 1rem);
  max-height: calc(92vh - env(safe-area-inset-bottom));
  margin: 0 0.5rem calc(0.5rem + env(safe-area-inset-bottom));
  border-radius: 2.1rem;
  background: color-mix(in srgb, var(--p-content-background) 78%, transparent);
  -webkit-backdrop-filter: blur(30px) saturate(1.8);
  backdrop-filter: blur(30px) saturate(1.8);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.35),
    inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 12%, transparent),
    0 22px 60px -18px rgb(0 0 0 / 0.45);
  overflow: hidden;
}
.dsh__grabber {
  align-self: center;
  width: 2.3rem;
  height: 0.3rem;
  margin: 0.5rem 0 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 25%, transparent);
}
.dsh__head {
  display: grid;
  grid-template-columns: 2.4rem minmax(0, 1fr) 2.4rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.85rem 0.6rem;
}
.dsh--sheet .dsh__head {
  padding: 0.45rem 1rem 0.7rem;
  touch-action: none;
}
.dsh__side {
  display: flex;
}
.dsh__side--end {
  justify-content: flex-end;
}
.dsh__title {
  margin: 0;
  overflow: hidden;
  font-size: 1.02rem;
  font-weight: 650;
  letter-spacing: -0.015em;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* the round glass button (also given to the lead slot's button by its owner) */
.dsh__round,
.dsh__side :slotted(.dsh-round) {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  border: 0;
  border-radius: 999px;
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.4),
    inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 10%, transparent);
  cursor: pointer;
  transition:
    transform 0.3s cubic-bezier(0.32, 0.72, 0, 1),
    background 0.2s;
}
.dsh__round i,
.dsh__side :slotted(.dsh-round) i {
  font-size: 0.8rem;
  font-weight: 700;
}
.dsh__round:hover,
.dsh__side :slotted(.dsh-round:hover) {
  background: color-mix(in srgb, var(--p-text-color) 13%, transparent);
}
.dsh__round:active,
.dsh__side :slotted(.dsh-round:active) {
  transform: scale(0.88);
}
.dsh__body {
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0 0.85rem 1rem;
}
.dsh--sheet .dsh__body {
  padding: 0 1rem 1.15rem;
}
</style>

<style>
html.app-dark .p-dialog.dash-sheet .dsh--sheet {
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.08),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.1),
    0 22px 60px -18px rgb(0 0 0 / 0.7);
}
/* The popover's frame: rounder, softer, the iOS shadow; glass in the glass theme */
.dash-pop.p-popover {
  --p-popover-content-padding: 0;
  border-radius: 1.6rem;
  background: color-mix(in srgb, var(--p-content-background) 80%, transparent);
  -webkit-backdrop-filter: blur(30px) saturate(1.8);
  backdrop-filter: blur(30px) saturate(1.8);
  border-color: color-mix(in srgb, var(--p-text-color) 9%, transparent);
  box-shadow:
    0 24px 60px -18px rgb(15 23 42 / 0.38),
    0 2px 8px -2px rgb(15 23 42 / 0.12);
  overflow: hidden;
}
.dash-pop.p-popover::before,
.dash-pop.p-popover::after {
  display: none;
}
.dash-pop .p-popover-content {
  padding: 0;
}
.dash-pop.p-popover.p-popover-enter-active {
  animation: dash-pop-in 0.34s cubic-bezier(0.32, 0.72, 0, 1);
}
@keyframes dash-pop-in {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.94);
  }
}
/* Smart Caddy: its page colour is a thin glass (half white), so the window takes the theme's strong glass, bright
   like the Liquid theme's, not a grey see-through of the dimmed page */
html.theme-caddy .dash-pop.p-popover,
html.theme-caddy .p-dialog.dash-sheet .dsh--sheet {
  background: var(--caddy-glass-strong);
}
html.theme-caddy .dsh .cs__type--on {
  background: var(--caddy-glass-strong);
}
html.theme-liquid .dash-pop.p-popover,
html.theme-liquid .p-dialog.dash-sheet .dsh {
  background: rgb(var(--lg-tint) / 0.74);
  -webkit-backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    var(--lg-shadow-float);
}
.p-dialog.dash-sheet {
  border: 0;
  background: transparent;
  box-shadow: none;
  max-height: none;
}
.p-dialog-bottom .p-dialog.dash-sheet {
  margin: 0;
}
.p-dialog.dash-sheet.p-dialog-enter-active {
  animation: dash-sheet-up 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.p-dialog.dash-sheet.p-dialog-leave-active {
  animation: dash-sheet-down 0.3s cubic-bezier(0.4, 0, 1, 1) forwards;
}
@keyframes dash-sheet-up {
  from {
    transform: translateY(100%);
  }
}
@keyframes dash-sheet-down {
  to {
    transform: translateY(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .dash-pop.p-popover.p-popover-enter-active,
  .p-dialog.dash-sheet.p-dialog-enter-active,
  .p-dialog.dash-sheet.p-dialog-leave-active {
    animation-duration: 0.01s;
  }
}
</style>
