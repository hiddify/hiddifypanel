/**
 * A small popover that opens from a button on a card (rename a node, or why it can't be renamed now), the same on the
 * dashboard and the Nodes page:
 * - on a phone it sits in the middle of the card, its arrow still on the button; anywhere it stays fully on screen
 *   (PrimeVue lines it up with the button's start, so near the screen's end it ran off it);
 * - opened from another card's button while it is open, it glides over there (PrimeVue's show() alone keeps it where
 *   it was, with the new content);
 * - it eases in from its arrow (styles: _card-popover.scss, the `card-popover` class on the Popover).
 */
import { nextTick, ref } from 'vue'
import type Popover from 'primevue/popover'

/** PrimeVue's own state: where it points (`target` / `eventTarget`); it has no method to move an open popover */
type PopoverState = { visible: boolean; container: HTMLElement | null; target: Element | null; eventTarget: Element | null; alignOverlay: () => void }

export function useCardPopover(options: { card: string; onPlaced?: () => void }) {
  const pop = ref<InstanceType<typeof Popover> | null>(null)
  const state = () => pop.value as unknown as PopoverState | null
  let moveTimer = 0
  let resize: ResizeObserver | null = null

  /** Open at `target` (the button that was pressed, unless given), or glide there when already open */
  function open(event: Event, target?: HTMLElement | null) {
    const anchor = target ?? (event.currentTarget as HTMLElement)
    const s = state()
    if (!s) return
    if (!s.visible || !s.container) {
      pop.value?.show(event, anchor)
      return
    }
    s.target = anchor
    s.eventTarget = event.currentTarget as HTMLElement
    const container = s.container
    container.classList.add('card-popover--moving')
    window.clearTimeout(moveTimer)
    moveTimer = window.setTimeout(() => container.classList.remove('card-popover--moving'), 260)
    void nextTick(() => {
      // alignOverlay only ever adds "flipped" (opened above the button): start again from below
      unflip(container)
      s.alignOverlay()
      place()
      options.onPlaced?.()
    })
  }

  function hide() {
    pop.value?.hide()
  }

  function unflip(container: HTMLElement) {
    container.classList.remove('p-popover-flipped')
    container.removeAttribute('data-p-popover-flipped')
  }

  /** Centre on the card (or on the button when there is no card), keep it on screen, point the arrow at the button */
  function place() {
    const s = state()
    const container = s?.container
    const anchor = s?.target as HTMLElement | null
    if (!container || !anchor) return
    const width = container.offsetWidth
    const anchorBox = anchor.getBoundingClientRect()
    const card = anchor.closest(options.card)
    const box = card ? card.getBoundingClientRect() : anchorBox
    const margin = 8
    const left = Math.min(Math.max(box.left + (box.width - width) / 2, margin), window.innerWidth - width - margin)
    container.style.left = `${left + window.scrollX}px`
    // PrimeVue decides "flipped" from where the popover is on screen, which is still the old place while it glides
    // to another button: decide from where it is going instead
    if (parseFloat(container.style.top) > anchorBox.top + window.scrollY) unflip(container)
    // the arrow: PrimeVue draws it at --p-popover-arrow-offset + --p-popover-arrow-left from the popover's start
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
    const offset = parseFloat(getComputedStyle(container).getPropertyValue('--p-popover-arrow-offset')) * rem || 0
    const arrow = Math.min(Math.max(anchorBox.left + anchorBox.width / 2 - left - offset, 0), width - 2 * offset)
    container.style.setProperty('--p-popover-arrow-left', `${arrow}px`)
    container.style.setProperty('--card-popover-origin', `${arrow + offset}px`)
  }

  /** The Popover's @show: PrimeVue lines it up again whenever its size changes (its own ResizeObserver, started first) */
  function onShow() {
    const container = state()?.container
    resize?.disconnect()
    if (container) {
      resize = new ResizeObserver(() => place())
      resize.observe(container)
    }
    place()
    options.onPlaced?.()
  }

  /** The Popover's @hide */
  function onHide() {
    resize?.disconnect()
    resize = null
  }

  return { pop, open, hide, onShow, onHide }
}
