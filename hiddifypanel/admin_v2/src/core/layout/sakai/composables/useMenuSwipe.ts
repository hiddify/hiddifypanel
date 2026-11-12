/**
 * Phones and tablets (below the desktop layout): the menu follows the finger.
 *
 * - The menu tab can be dragged: the menu slides with it, and on release it opens or closes by how far it went and how
 *   fast it was flicked (a tap still toggles it, as a button).
 * - A sideways swipe that starts on the start third of the page (the left in LTR, the right in RTL) opens the menu the
 *   same way; on the open menu or its mask, a swipe back closes it. A swipe that is more vertical stays a scroll, and
 *   one that starts on something of its own (a field, a slider, a drag handle, a row that scrolls sideways) is left to
 *   it.
 * - A swipe that starts on the start edge of the screen (EDGE) always opens the menu, whatever it starts on (a field, a
 *   slider, a row that scrolls sideways), as long as no dialog is open. A touch on either edge is never handed to the
 *   browser: iOS reads it as "back" (or "forward") the moment it starts, so it is cancelled at touchstart and a tap
 *   there is replayed as a click.
 *
 * While dragging, the wrapper gets `layout-menu-dragging` and `--menu-drag` (0 closed … 1 open), which the layout's
 * styles use instead of their transitions; on release the class goes and the normal open / closed transition finishes
 * the move from where the finger left it.
 */
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

const PHONE_QUERY = '(max-width: 991px)'
/** Movement before the gesture is decided (a tap below it) */
const SLOP = 10
/** How much more sideways than vertical a swipe has to be */
const SIDEWAYS = 1.3
/** A flick at least this fast (px/ms, over the last moments of the drag) decides by its direction, wherever the menu is */
const FLICK = 0.35
/** The window the release speed is measured over (ms) */
const SPEED_WINDOW = 90
/** Where a swipe that opens may start: this share of the screen, from its start edge */
const START_ZONE = 0.34
/** The strip at each side of the screen (px) whose touches the browser never gets: no swipe back or forward from it */
const EDGE = 28
/** An open dialog or drawer: a swipe from the edge does not open the menu behind it */
const MODAL_OPEN = '.p-dialog-mask, .p-drawer-mask'
/** Things that keep their own touch: no menu swipe from them */
const OWN_GESTURE = 'input, textarea, select, [contenteditable="true"], .p-slider, .ob-row__handle, .menu-tab, .p-dialog, .p-drawer, [data-no-menu-swipe]'

interface Drag {
  pointerId: number | null
  startX: number
  startY: number
  from: number // progress at the start (0 closed, 1 open)
  decided: boolean // the gesture is ours (else still deciding or given up)
  width: number
  samples: { x: number; t: number }[] // recent positions, for the speed at release
  edge: boolean // started on the start edge: opens the menu whatever it started on
}

/** A touch on an edge, held back from the browser: replayed as a click if it was a tap */
interface EdgeTouch {
  target: Element | null
  x: number
  y: number
  moved: boolean
}

export function useMenuSwipe(options: { wrapper: Ref<HTMLElement | null>; isOpen: () => boolean; setOpen: (open: boolean) => void }) {
  const dragging = ref(false)
  /** Just released: the mask eases from where the finger left it (its fade-in animation would start over) */
  const settling = ref(false)
  let settleTimer = 0
  const progress = ref(0)
  let drag: Drag | null = null
  let tabDragged = false
  let edgeTouch: EdgeTouch | null = null
  const phone = window.matchMedia(PHONE_QUERY)

  /** +1 when "open" is towards the right of the screen (LTR), -1 in RTL */
  const sign = () => (document.documentElement.dir === 'rtl' ? -1 : 1)
  const menuWidth = () => (document.querySelector<HTMLElement>('.layout-sidebar')?.offsetWidth || 320)

  function begin(x: number, y: number, pointerId: number | null, edge = false) {
    const open = options.isOpen()
    drag = { pointerId, startX: x, startY: y, from: open ? 1 : 0, decided: false, width: menuWidth(), samples: [{ x, t: performance.now() }], edge }
  }

  function follow(x: number) {
    if (!drag) return
    const now = performance.now()
    drag.samples.push({ x, t: now })
    while (drag.samples.length > 2 && now - drag.samples[1].t > SPEED_WINDOW) drag.samples.shift()
    const p = drag.from + ((x - drag.startX) * sign()) / drag.width
    progress.value = Math.min(1, Math.max(0, p))
    options.wrapper.value?.style.setProperty('--menu-drag', progress.value.toFixed(4))
  }

  function finish(cancelled = false) {
    if (!drag) return
    const wasDragging = dragging.value
    const p = progress.value
    // the speed over the last moments, towards "open"
    const first = drag.samples[0]
    const last = drag.samples[drag.samples.length - 1]
    const v = last.t > first.t ? ((last.x - first.x) * sign()) / (last.t - first.t) : 0
    drag = null
    if (!wasDragging) return
    const open = cancelled ? options.isOpen() : Math.abs(v) >= FLICK ? v > 0 : p > 0.5
    // the mask starts the ease at the opacity the finger left it at
    options.wrapper.value?.style.setProperty('--menu-drag', p.toFixed(4))
    settling.value = true
    dragging.value = false
    options.setOpen(open)
    requestAnimationFrame(() => options.wrapper.value?.style.setProperty('--menu-drag', open ? '1' : '0'))
    window.clearTimeout(settleTimer)
    settleTimer = window.setTimeout(() => {
      settling.value = false
      options.wrapper.value?.style.removeProperty('--menu-drag')
    }, 450)
  }

  // --- The tab: pointer events (finger, pen or mouse) ---
  function onTabPointerDown(e: PointerEvent) {
    if (!phone.matches || (e.pointerType === 'mouse' && e.button !== 0)) return
    tabDragged = false
    begin(e.clientX, e.clientY, e.pointerId)
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }
  function onTabPointerMove(e: PointerEvent) {
    if (!drag || drag.pointerId !== e.pointerId) return
    if (!drag.decided) {
      if (Math.abs(e.clientX - drag.startX) < SLOP) return
      drag.decided = true
      dragging.value = true
      tabDragged = true
    }
    follow(e.clientX)
  }
  function onTabPointerUp(e: PointerEvent) {
    if (!drag || drag.pointerId !== e.pointerId) return
    finish(e.type === 'pointercancel')
  }
  /** The tab's click: a toggle, unless it ended a drag (that already opened or closed the menu) */
  function tabClickToggles(): boolean {
    const toggles = !tabDragged
    tabDragged = false
    return toggles
  }

  // --- The page: touch events (a scroll has to be told apart, and a swipe that is ours must not scroll) ---
  function scrollsSideways(el: Element | null, towardsOpen: number): boolean {
    for (let node = el; node && node !== document.body; node = node.parentElement) {
      if (!(node instanceof HTMLElement) || node.scrollWidth <= node.clientWidth + 1) continue
      const overflow = getComputedStyle(node).overflowX
      if (overflow !== 'auto' && overflow !== 'scroll') continue
      // a swipe towards "open" moves the content back: only a row that can still scroll that way keeps the swipe
      const left = Math.abs(node.scrollLeft)
      const canGoBack = sign() * towardsOpen > 0 ? left > 0 : left < node.scrollWidth - node.clientWidth - 1
      if (canGoBack) return true
    }
    return false
  }

  function onTouchStart(e: TouchEvent) {
    if (!phone.matches || e.touches.length !== 1) return
    const t = e.touches[0]
    const target = e.target as Element | null
    // the edges: the browser must not see this touch, or it swipes back (iOS decides at touchstart)
    const fromStart = sign() > 0 ? t.clientX : window.innerWidth - t.clientX
    const fromEnd = window.innerWidth - fromStart
    edgeTouch = null
    if ((fromStart < EDGE || fromEnd < EDGE) && e.cancelable) {
      e.preventDefault()
      edgeTouch = { target, x: t.clientX, y: t.clientY, moved: false }
    }
    if (drag) return
    const open = options.isOpen()
    if (!open && fromStart < EDGE && !document.querySelector(MODAL_OPEN)) {
      begin(t.clientX, t.clientY, null, true)
      return
    }
    if (target?.closest(OWN_GESTURE)) return
    if (!open) {
      // only from the start part of the screen
      if (fromStart > window.innerWidth * START_ZONE) return
    } else if (!target?.closest('.layout-sidebar, .layout-mask')) {
      return
    }
    begin(t.clientX, t.clientY, null)
  }

  function onTouchMove(e: TouchEvent) {
    const t = e.touches[0]
    if (edgeTouch && Math.hypot(t.clientX - edgeTouch.x, t.clientY - edgeTouch.y) >= SLOP) edgeTouch.moved = true
    if (!drag || drag.pointerId !== null) return
    const dx = t.clientX - drag.startX
    const dy = t.clientY - drag.startY
    if (!drag.decided) {
      if (Math.abs(dx) < SLOP && Math.abs(dy) < SLOP) return
      const towardsOpen = Math.sign(dx * sign())
      const wanted = drag.from === 0 ? towardsOpen > 0 : towardsOpen < 0
      if (Math.abs(dx) < Math.abs(dy) * SIDEWAYS || !wanted || (!drag.edge && scrollsSideways(e.target as Element, towardsOpen))) {
        drag = null // a scroll, or the wrong way: not ours
        return
      }
      drag.decided = true
      dragging.value = true
    }
    if (e.cancelable) e.preventDefault() // ours now: no scroll, no browser swipe-back
    follow(t.clientX)
  }

  function onTouchEnd(e: TouchEvent) {
    // a tap on an edge lost its click with the cancelled touchstart: give it back
    const tap = edgeTouch
    edgeTouch = null
    if (tap && !tap.moved && e.type === 'touchend' && tap.target?.isConnected) {
      const el = tap.target.closest<HTMLElement>('input, textarea, select, [contenteditable="true"]')
      el?.focus()
      ;(tap.target as HTMLElement).click?.()
    }
    if (!drag || drag.pointerId !== null) return
    finish(e.type === 'touchcancel')
  }

  onMounted(() => {
    document.addEventListener('touchstart', onTouchStart, { passive: false })
    document.addEventListener('touchmove', onTouchMove, { passive: false })
    document.addEventListener('touchend', onTouchEnd)
    document.addEventListener('touchcancel', onTouchEnd)
  })
  onBeforeUnmount(() => {
    window.clearTimeout(settleTimer)
    document.removeEventListener('touchstart', onTouchStart)
    document.removeEventListener('touchmove', onTouchMove)
    document.removeEventListener('touchend', onTouchEnd)
    document.removeEventListener('touchcancel', onTouchEnd)
  })

  return { dragging, settling, progress, onTabPointerDown, onTabPointerMove, onTabPointerUp, tabClickToggles }
}
