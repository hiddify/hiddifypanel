import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { prefixSums, visibleRange } from '@/shared/composables/windowSlice'

export interface SliceSlot {
  key: string
  index: number
  /** Document position inside the list, when `virtual` is on. */
  top: number
}

/**
 * Mount only the items that overlap the page scroll. The list element keeps the full height, so the page still
 * scrolls as if every item were there. `hold` freezes the mounted set (a drag must not unmount the item under the pointer).
 */
export function useWindowSlice(
  keys: Ref<readonly string[]>,
  options: { enabled: Ref<boolean>; estimate: (key: string) => number; gap: number; overscan?: number; hold?: Ref<boolean> },
) {
  const root = ref<HTMLElement | null>(null)
  const scrollY = ref(0)
  const viewHeight = ref(800)
  const listTop = ref(0)
  const version = ref(0)
  const known = new Map<string, number>()
  const elements = new Map<string, HTMLElement>()
  let frame = 0

  const overscan = options.overscan ?? 600
  let dirty = false

  function readScroll() {
    if (options.hold?.value) return
    scrollY.value = window.scrollY
    viewHeight.value = window.innerHeight
    const el = root.value
    if (el) listTop.value = el.getBoundingClientRect().top + window.scrollY
  }

  function pump() {
    if (frame) return
    frame = requestAnimationFrame(() => {
      frame = 0
      if (dirty && !options.hold?.value) {
        dirty = false
        version.value++
      }
      readScroll()
    })
  }

  function remeasure() {
    if (options.hold?.value) return
    for (const [key, el] of elements) {
      const height = el.offsetHeight
      if (height > 0 && known.get(key) !== height) {
        known.set(key, height)
        dirty = true
      }
    }
    pump()
  }

  /** Record an item's element. A height that differs from the estimate (or the last measurement) rebuilds the offsets. */
  function measure(key: string, el: Element | null) {
    if (!(el instanceof HTMLElement)) {
      elements.delete(key)
      return
    }
    elements.set(key, el)
    if (options.hold?.value) return
    const height = el.offsetHeight
    if (height > 0 && known.get(key) !== height) {
      known.set(key, height)
      dirty = true
      pump()
    }
  }

  const state = computed(() => {
    const list = keys.value
    if (!options.enabled.value) {
      return { virtual: false, total: 0, slots: list.map((key, index): SliceSlot => ({ key, index, top: 0 })) }
    }
    version.value
    const heights = list.map((key) => known.get(key) ?? options.estimate(key))
    const prefix = prefixSums(heights, options.gap)
    const range = visibleRange(prefix, scrollY.value - listTop.value, scrollY.value - listTop.value + viewHeight.value, overscan)
    const slots: SliceSlot[] = []
    for (let i = range.start; i < range.end; i++) slots.push({ key: list[i]!, index: i, top: prefix[i]! })
    return { virtual: true, total: prefix[list.length] ?? 0, slots }
  })

  onMounted(() => {
    readScroll()
    window.addEventListener('scroll', pump, { passive: true })
    window.addEventListener('resize', remeasure)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', pump)
    window.removeEventListener('resize', remeasure)
    if (frame) cancelAnimationFrame(frame)
  })
  watch(options.enabled, async (on) => {
    if (!on) return
    await nextTick()
    readScroll()
  })
  watch(keys, () => pump())

  return {
    root,
    virtual: computed(() => state.value.virtual),
    total: computed(() => state.value.total),
    slots: computed(() => state.value.slots),
    measure,
  }
}
