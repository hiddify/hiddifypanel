/** Start offsets: `prefix[i]` is where item `i` begins, `prefix[n]` is the list height. A `gap` follows every item. */
export function prefixSums(heights: readonly number[], gap: number): number[] {
  const prefix = new Array<number>(heights.length + 1)
  prefix[0] = 0
  for (let i = 0; i < heights.length; i++) prefix[i + 1] = prefix[i]! + heights[i]! + gap
  return prefix
}

/**
 * Items whose box intersects `[top, bottom)`, widened by `overscan` px.
 * Item `i` occupies `[prefix[i], prefix[i + 1])`.
 */
export function visibleRange(prefix: readonly number[], top: number, bottom: number, overscan = 0): { start: number; end: number } {
  const n = prefix.length - 1
  if (n <= 0 || bottom + overscan <= 0) return { start: 0, end: 0 }
  const from = top - overscan
  const to = bottom + overscan
  if (from >= prefix[n]!) return { start: n, end: n }

  // First item that ends after `from`.
  let lo = 0
  let hi = n
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (prefix[mid + 1]! <= from) lo = mid + 1
    else hi = mid
  }
  const start = lo

  // First item that starts at or after `to`.
  lo = start
  hi = n
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (prefix[mid]! < to) lo = mid + 1
    else hi = mid
  }
  return { start, end: lo }
}
