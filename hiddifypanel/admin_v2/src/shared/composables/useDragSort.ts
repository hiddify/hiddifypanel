import { nextTick, onBeforeUnmount, ref } from 'vue'

/** How close (px) to the screen's top or bottom edge the page starts scrolling under a dragged item. */
const EDGE = 72
/** The landing glide after a drop (ms); the CSS transition of the items is the same length. */
export const DRAG_SETTLE_MS = 200

type Key = string | number

interface Drag {
  handle: HTMLElement
  pointerId: number
  keys: Key[]
  tops: number[]
  heights: number[]
  gap: number
  from: number
  to: number
  startY: number
  clientY: number
  raf: number
}

/**
 * A list reordered by dragging an item's handle, live: the item follows the pointer (mouse, finger or pen alike),
 * the items it passes slide aside to make room, near the screen's top or bottom edge the page scrolls, and on
 * release it glides into its new place. Escape (or a cancelled touch) puts it back.
 *
 * `item(key)` finds an item's element. `onDrop(keys, from, to)` gets the items' order before the move and returns
 * whether the move was taken (false: the item glides back). Bind `styleOf(key)` and the `lifted` / `held` /
 * `moving` flags: the items need `transition: translate DRAG_SETTLE_MS` while `moving` is set, none on the `held`
 * one and none at all while `settling`.
 */
export function useDragSort(opts: { item: (key: Key) => HTMLElement | null | undefined; onDrop: (keys: Key[], from: number, to: number) => boolean }) {
  /** The key of the item being moved (and while it lands). */
  const lifted = ref<Key | null>(null)
  /** The key of the item under the pointer: it follows the pointer exactly (no transition), until released. */
  const held = ref<Key | null>(null)
  /** While an item is moved or lands: the items slide. */
  const moving = ref(false)
  /** Right after a drop: the items jump to their new places in one frame, without sliding. */
  const settling = ref(false)
  const offsets = ref<Map<Key, number>>(new Map())
  let drag: Drag | null = null
  let landing = 0

  function start(e: PointerEvent, key: Key, keys: Key[]) {
    if (drag || e.button !== 0) return
    const els = keys.map((k) => opts.item(k))
    if (els.some((el) => !el)) return
    e.preventDefault()
    window.clearTimeout(landing)
    const handle = e.currentTarget as HTMLElement
    handle.setPointerCapture(e.pointerId)
    const rects = els.map((el) => el!.getBoundingClientRect())
    const from = keys.indexOf(key)
    drag = {
      handle,
      pointerId: e.pointerId,
      keys,
      tops: rects.map((r) => r.top + window.scrollY),
      heights: rects.map((r) => r.height),
      gap: rects.length > 1 ? rects[1]!.top - rects[0]!.bottom : 0,
      from,
      to: from,
      startY: e.clientY + window.scrollY,
      clientY: e.clientY,
      raf: 0,
    }
    handle.addEventListener('pointermove', move)
    handle.addEventListener('pointerup', drop)
    handle.addEventListener('pointercancel', cancel)
    window.addEventListener('keydown', onKey, true)
    settling.value = false
    lifted.value = key
    held.value = key
    moving.value = true
    if (e.pointerType !== 'mouse') navigator.vibrate?.(8)
    drag.raf = requestAnimationFrame(frame)
  }

  function move(e: PointerEvent) {
    if (drag) drag.clientY = e.clientY
  }
  function onKey(e: KeyboardEvent) {
    if (e.key !== 'Escape' || !drag) return
    e.preventDefault()
    e.stopPropagation()
    cancel()
  }

  /** The moved item's offset from where it started. */
  const dyOf = (d: Drag) => d.clientY + window.scrollY - d.startY

  /** Each frame: scroll near an edge, then place the moved item under the pointer and the others around it. */
  function frame() {
    if (!drag) return
    const y = drag.clientY
    const speed = y < EDGE ? -(EDGE - y) / 4 : y > window.innerHeight - EDGE ? (y - (window.innerHeight - EDGE)) / 4 : 0
    if (speed) window.scrollBy(0, speed)
    const { from, tops, heights, keys } = drag
    const dy = dyOf(drag)
    const center = tops[from]! + heights[from]! / 2 + dy
    let to = 0
    keys.forEach((_, i) => {
      if (i !== from && tops[i]! + heights[i]! / 2 < center) to++
    })
    const room = heights[from]! + drag.gap
    const next = new Map<Key, number>([[keys[from]!, dy]])
    keys.forEach((k, i) => {
      if (from < to && i > from && i <= to) next.set(k, -room)
      else if (from > to && i >= to && i < from) next.set(k, room)
    })
    offsets.value = next
    drag.to = to
    drag.raf = requestAnimationFrame(frame)
  }

  function end(commit: boolean) {
    const d = drag
    if (!d) return
    drag = null
    cancelAnimationFrame(d.raf)
    d.handle.removeEventListener('pointermove', move)
    d.handle.removeEventListener('pointerup', drop)
    d.handle.removeEventListener('pointercancel', cancel)
    window.removeEventListener('keydown', onKey, true)
    if (d.handle.hasPointerCapture(d.pointerId)) d.handle.releasePointerCapture(d.pointerId)
    const key = d.keys[d.from]!
    const dy = dyOf(d)
    held.value = null
    const taken = commit && d.from !== d.to && opts.onDrop(d.keys, d.from, d.to)
    if (taken) {
      // The list is in its new order now: every item jumps to its place at once (the others are there already),
      // the moved one stays where it was let go, then glides into its slot.
      const { tops, heights, from, to } = d
      const slot = to > from ? tops[to]! + heights[to]! - heights[from]! : tops[to]!
      settling.value = true
      offsets.value = new Map([[key, tops[from]! + dy - slot]])
      // Two frames: the browser has to draw it at the drop point once, or there is nothing to glide from.
      void nextTick(() =>
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            settling.value = false
            offsets.value = new Map()
          }),
        ),
      )
    } else {
      // Back to where it was: the others slide back too.
      offsets.value = new Map()
    }
    landing = window.setTimeout(() => {
      lifted.value = null
      moving.value = false
    }, DRAG_SETTLE_MS + 40)
  }
  const drop = () => end(true)
  const cancel = () => end(false)
  onBeforeUnmount(() => {
    cancel()
    window.clearTimeout(landing)
  })

  /** The item's shift while an item is moved: `translate`, so an entry animation that holds `transform` can't undo it. */
  function styleOf(key: Key): Record<string, string> | undefined {
    const y = offsets.value.get(key)
    return y ? { translate: `0 ${y}px` } : undefined
  }

  return { lifted, held, moving, settling, start, styleOf }
}
