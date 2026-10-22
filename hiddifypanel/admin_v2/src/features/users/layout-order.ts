import type { UsersLayout } from '@/features/users/api'

interface Ordered {
  uuid: string
  id: number
}

/** Pinned users first (in pin order), then the admin's order, then the users not placed yet (new ones), by id. */
export function orderRows<T extends Ordered>(rows: T[], layout: UsersLayout): T[] {
  const rank = new Map<string, number>()
  layout.pinned.forEach((u, i) => rank.set(u, i))
  const base = layout.pinned.length
  layout.order.forEach((u, i) => {
    if (!rank.has(u)) rank.set(u, base + i)
  })
  const unplaced = base + layout.order.length
  return [...rows].sort((a, b) => (rank.get(a.uuid) ?? unplaced + a.id) - (rank.get(b.uuid) ?? unplaced + b.id))
}

/**
 * `all` in its current order, with the users of `shown` (a search, filter or page of it) put in `shown`'s new
 * order, in the places those users had: the hidden ones keep theirs.
 */
export function mergeVisible(all: string[], shown: string[]): string[] {
  const picked = new Set(shown)
  let next = 0
  return all.map((u) => (picked.has(u) ? shown[next++]! : u))
}

/**
 * A drag result (`shown`: the listed users in their new order) applied to the layout. `null` when it would mix the
 * groups: a pinned user below an unpinned one; pinning or unpinning is what moves a user between them.
 */
export function reorder(layout: UsersLayout, allOrdered: string[], shown: string[]): UsersLayout | null {
  const pinned = new Set(layout.pinned)
  const firstUnpinned = shown.findIndex((u) => !pinned.has(u))
  if (firstUnpinned >= 0 && shown.slice(firstUnpinned).some((u) => pinned.has(u))) return null
  const newPinned = mergeVisible(layout.pinned, shown.filter((u) => pinned.has(u)))
  const unpinnedAll = allOrdered.filter((u) => !pinned.has(u))
  const newOrder = mergeVisible(unpinnedAll, shown.filter((u) => !pinned.has(u)))
  return { ...layout, pinned: newPinned, order: newOrder }
}

/** Pin: to the top row. Unpin: back to the top of the others, just below the pinned users. */
export function togglePin(layout: UsersLayout, allOrdered: string[], uuid: string): UsersLayout {
  const unpinnedAll = allOrdered.filter((u) => !layout.pinned.includes(u) && u !== uuid)
  if (layout.pinned.includes(uuid)) {
    return { ...layout, pinned: layout.pinned.filter((u) => u !== uuid), order: [uuid, ...unpinnedAll] }
  }
  return { ...layout, pinned: [uuid, ...layout.pinned], order: unpinnedAll }
}
