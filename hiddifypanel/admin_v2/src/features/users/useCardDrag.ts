import { onBeforeUnmount, ref } from 'vue'

/** How close (px) to the screen's top or bottom edge the page starts scrolling under a dragged card. */
const EDGE = 72

interface Drag {
  handle: HTMLElement
  uuids: string[]
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
 * Phones: a user card moved by its handle, like a table row on a desktop. Pointer events, so a finger and a mouse
 * work alike: the card follows the pointer, the cards it passes make room, and near the screen's top or bottom
 * edge the page scrolls. On release `onDrop(uuids, from, to)` gets the cards' order before the move.
 * The cards are found by `[data-card-uuid]`.
 */
export function useCardDrag(onDrop: (uuids: string[], from: number, to: number) => void) {
  /** The uuid of the card being moved. */
  const dragging = ref<string | null>(null)
  /** Right after a drop: the cards jump to their new places without sliding back first. */
  const settling = ref(false)
  const offsets = ref<Record<string, number>>({})
  let drag: Drag | null = null

  function start(e: PointerEvent, uuid: string, uuids: string[]) {
    if (drag || e.button !== 0) return
    const cards = uuids.map((u) => document.querySelector<HTMLElement>(`[data-card-uuid="${u}"]`))
    if (cards.some((c) => !c)) return
    e.preventDefault()
    const handle = e.currentTarget as HTMLElement
    handle.setPointerCapture(e.pointerId)
    const rects = cards.map((c) => c!.getBoundingClientRect())
    const from = uuids.indexOf(uuid)
    drag = {
      handle,
      uuids,
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
    dragging.value = uuid
    navigator.vibrate?.(8)
    drag.raf = requestAnimationFrame(frame)
  }

  function move(e: PointerEvent) {
    if (drag) drag.clientY = e.clientY
  }

  /** Each frame: scroll near an edge, then place the moved card under the pointer and the others around it. */
  function frame() {
    if (!drag) return
    const y = drag.clientY
    const speed = y < EDGE ? -(EDGE - y) / 4 : y > window.innerHeight - EDGE ? (y - (window.innerHeight - EDGE)) / 4 : 0
    if (speed) window.scrollBy(0, speed)
    const { from, tops, heights, uuids } = drag
    const dy = y + window.scrollY - drag.startY
    const center = tops[from]! + heights[from]! / 2 + dy
    let to = 0
    uuids.forEach((_, i) => {
      if (i !== from && tops[i]! + heights[i]! / 2 < center) to++
    })
    const room = heights[from]! + drag.gap
    const next: Record<string, number> = { [uuids[from]!]: dy }
    uuids.forEach((u, i) => {
      if (from < to && i > from && i <= to) next[u] = -room
      else if (from > to && i >= to && i < from) next[u] = room
    })
    offsets.value = next
    drag.to = to
    drag.raf = requestAnimationFrame(frame)
  }

  function end(commit: boolean) {
    if (!drag) return
    const { handle, uuids, from, to, raf } = drag
    drag = null
    cancelAnimationFrame(raf)
    handle.removeEventListener('pointermove', move)
    handle.removeEventListener('pointerup', drop)
    handle.removeEventListener('pointercancel', cancel)
    settling.value = true
    dragging.value = null
    offsets.value = {}
    if (commit && from !== to) onDrop(uuids, from, to)
    requestAnimationFrame(() => requestAnimationFrame(() => (settling.value = false)))
  }
  const drop = () => end(true)
  const cancel = () => end(false)
  onBeforeUnmount(cancel)

  /** The card's shift while a card is moved. */
  function styleOf(uuid: string): Record<string, string> | undefined {
    const y = offsets.value[uuid]
    return y ? { transform: `translateY(${y}px)` } : undefined
  }

  return { dragging, settling, start, styleOf }
}
