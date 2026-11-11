<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * A drawer under a package card: closed, only its handle shows (a live chevron that says "there is more below");
 * a tap, or pulling the handle down, opens it smoothly and scrolls the page to it. While pulled, the handle stays
 * under the finger: the drawer grows by exactly the distance pulled.
 */
defineProps<{ count: number; attention?: boolean }>()

const { t } = useI18n()
const open = ref(false)
const body = ref<HTMLElement | null>(null)
const OPEN_EASE = 'height 0.6s cubic-bezier(0.22, 1, 0.36, 1)'
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Animate the height from `from` (the current one by default) to open or closed. */
function animate(toOpen: boolean, from?: number) {
  const el = body.value
  if (!el) return
  const start = from ?? el.getBoundingClientRect().height
  const end = toOpen ? el.scrollHeight : 0
  el.style.transition = 'none'
  el.style.height = `${start}px`
  void el.offsetHeight // apply the start height before the transition
  open.value = toOpen
  if (reduced() || start === end) {
    el.style.height = toOpen ? 'auto' : '0px'
  } else {
    el.style.transition = OPEN_EASE
    el.style.height = `${end}px`
    el.addEventListener(
      'transitionend',
      () => {
        if (open.value) el.style.height = 'auto' // follows its content (a conversation opened, the list filtered)
      },
      { once: true },
    )
  }
  if (toOpen) nextTick(() => el.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' }))
}

function toggle() {
  animate(!open.value)
}

// Pulling the handle: the drawer follows the finger; let go past a short distance and it finishes the move.
let startY = 0
let startH = 0
let dragging = false
let pointerId: number | null = null
let swallowClick = false

function onDown(e: PointerEvent) {
  if (!body.value || (e.pointerType === 'mouse' && e.button !== 0)) return
  pointerId = e.pointerId
  swallowClick = false // a touch pull is not followed by a click: the flag must not eat the next tap
  // From the first touch: a quick finger is off the handle before it has moved far enough to count as a pull.
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  startY = e.clientY
  startH = body.value.getBoundingClientRect().height
  dragging = false
}
function onMove(e: PointerEvent) {
  const el = body.value
  if (!el || e.pointerId !== pointerId) return
  const dy = e.clientY - startY
  if (!dragging) {
    if (Math.abs(dy) < 6) return
    dragging = true
    el.style.transition = 'none'
  }
  el.style.height = `${Math.min(Math.max(startH + dy, 0), el.scrollHeight)}px`
}
function onUp(e: PointerEvent) {
  const el = body.value
  if (!el || e.pointerId !== pointerId) return
  pointerId = null
  if (!dragging) return
  dragging = false
  swallowClick = true // the click that follows a pull is not a tap
  const height = el.getBoundingClientRect().height
  const pulled = height - startH
  animate(open.value ? pulled > -70 : pulled > 50, height)
}
function onClick() {
  if (swallowClick) {
    swallowClick = false
    return
  }
  toggle()
}
</script>

<template>
  <div class="pd" :class="{ 'pd--open': open }">
    <div ref="body" class="pd-body" style="height: 0px" :aria-hidden="!open">
      <div class="pd-inner"><slot /></div>
    </div>
    <button
      type="button"
      class="pd-handle"
      :aria-expanded="open"
      :aria-label="open ? t('inbox.drawer.close') : t('inbox.drawer.open')"
      :title="open ? t('inbox.drawer.close') : t('inbox.drawer.open')"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
      @click="onClick"
    >
      <i class="pi pi-comments" aria-hidden="true" />
      <span class="pd-count">{{ count }}</span>
      <span v-if="attention && !open" class="pd-dot" aria-hidden="true" />
      <i class="pi pi-chevron-down pd-chevron" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.pd {
  display: flex;
  flex-direction: column;
}
.pd-body {
  overflow: hidden;
  /* where the page stops when it scrolls to the opened list: clear of the top bar */
  scroll-margin-top: 6rem;
}
.pd-inner {
  padding-top: 0.9rem;
}
.pd-handle {
  position: relative;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  align-self: center;
  margin-top: -0.95rem;
  padding: 0.35rem 0.9rem;
  border: 1px solid color-mix(in srgb, var(--p-text-color) 18%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-content-background) 88%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  box-shadow: 0 6px 16px -8px rgb(0 0 0 / 0.35);
  color: var(--text-color-secondary);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: grab;
  /* the handle is pulled, not the page */
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -webkit-tap-highlight-color: transparent;
  transition:
    color 0.2s,
    border-color 0.2s,
    margin-top 0.3s;
}
.pd--open .pd-handle {
  margin-top: 0.6rem;
}
.pd-handle:hover,
.pd-handle:focus-visible {
  color: var(--primary-color);
  border-color: color-mix(in srgb, var(--primary-color) 45%, transparent);
}
.pd-handle:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.pd-handle:active {
  cursor: grabbing;
}
.pd-chevron {
  font-size: 0.8rem;
  color: var(--primary-color);
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.pd-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--p-red-500);
}
/* Closed: the chevron bobs down and a soft ring breathes round the handle, so it reads as "more below". */
.pd:not(.pd--open) .pd-chevron {
  animation: pd-bob 1.5s ease-in-out infinite;
}
.pd:not(.pd--open) .pd-handle {
  animation: pd-ring 2.4s ease-out infinite;
}
.pd--open .pd-chevron {
  transform: rotate(180deg);
}
@keyframes pd-bob {
  0%,
  100% {
    transform: translateY(-1px);
  }
  50% {
    transform: translateY(3px);
  }
}
@keyframes pd-ring {
  0% {
    box-shadow:
      0 6px 16px -8px rgb(0 0 0 / 0.35),
      0 0 0 0 color-mix(in srgb, var(--primary-color) 40%, transparent);
  }
  70%,
  100% {
    box-shadow:
      0 6px 16px -8px rgb(0 0 0 / 0.35),
      0 0 0 10px color-mix(in srgb, var(--primary-color) 0%, transparent);
  }
}
@media (prefers-reduced-motion: reduce) {
  .pd-chevron,
  .pd-handle {
    animation: none !important;
    transition: none;
  }
}
</style>
