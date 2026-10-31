/**
 * Full mode's tools that work on the frame's DOM directly: table rows and columns, find & replace, clean-up.
 * (Nodes of the frame are not ``instanceof`` this window's classes: node types and tag names are compared instead.)
 */

const ELEMENT = 1
const TEXT = 3

export function closestIn(node: Node | null | undefined, selector: string, root: HTMLElement): HTMLElement | null {
  const el = node ? (node.nodeType === ELEMENT ? (node as Element) : node.parentElement) : null
  const found = el?.closest<HTMLElement>(selector) ?? null
  return found && root.contains(found) && found !== root ? found : null
}

// ---- tables ----

export type TableAction = 'rowAbove' | 'rowBelow' | 'colBefore' | 'colAfter' | 'rowDelete' | 'colDelete' | 'tableDelete'

/** Runs ``action`` on the table around ``cell``; returns the cell to put the caret in (null: the table is gone). */
export function tableAction(cell: HTMLTableCellElement, action: TableAction): HTMLElement | null {
  const row = cell.parentElement as HTMLTableRowElement
  const table = cell.closest('table') as HTMLTableElement
  const doc = cell.ownerDocument
  const index = Array.from(row.children).indexOf(cell)
  const rows = Array.from(table.querySelectorAll('tr')) as HTMLTableRowElement[]
  const blankCell = (like: Element) => {
    const c = doc.createElement(like.tagName.toLowerCase())
    const style = like.getAttribute('style')
    if (style) c.setAttribute('style', style)
    c.innerHTML = '&nbsp;'
    return c
  }
  switch (action) {
    case 'rowAbove':
    case 'rowBelow': {
      const copy = doc.createElement('tr')
      for (const c of Array.from(row.children)) copy.appendChild(blankCell(c))
      row.parentElement!.insertBefore(copy, action === 'rowAbove' ? row : row.nextSibling)
      return copy.children[index] as HTMLElement
    }
    case 'colBefore':
    case 'colAfter': {
      for (const r of rows) {
        const ref = r.children[Math.min(index, r.children.length - 1)]
        if (!ref) continue
        r.insertBefore(blankCell(ref), action === 'colBefore' ? ref : ref.nextSibling)
      }
      return row.children[action === 'colBefore' ? index : index + 1] as HTMLElement
    }
    case 'rowDelete': {
      if (rows.length <= 1) return tableAction(cell, 'tableDelete')
      const next = (row.nextElementSibling ?? row.previousElementSibling) as HTMLTableRowElement | null
      row.remove()
      return (next?.children[Math.min(index, next.children.length - 1)] as HTMLElement) ?? null
    }
    case 'colDelete': {
      if (row.children.length <= 1) return tableAction(cell, 'tableDelete')
      for (const r of rows) r.children[Math.min(index, r.children.length - 1)]?.remove()
      return row.children[Math.min(index, row.children.length - 1)] as HTMLElement
    }
    case 'tableDelete':
      table.remove()
      return null
  }
}

// ---- find & replace (in the text, not in tags) ----

function textNodes(root: HTMLElement): Text[] {
  const walker = root.ownerDocument.createTreeWalker(root, 4 /* NodeFilter.SHOW_TEXT */)
  const out: Text[] = []
  for (let n = walker.nextNode(); n; n = walker.nextNode()) out.push(n as Text)
  return out
}

function pattern(find: string, matchCase: boolean): RegExp {
  return new RegExp(find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), matchCase ? 'g' : 'gi')
}

export function countMatches(root: HTMLElement, find: string, matchCase: boolean): number {
  if (!find) return 0
  const re = pattern(find, matchCase)
  return textNodes(root).reduce((n, node) => n + (node.data.match(re)?.length ?? 0), 0)
}

export function replaceAll(root: HTMLElement, find: string, replacement: string, matchCase: boolean): number {
  if (!find) return 0
  const re = pattern(find, matchCase)
  let count = 0
  for (const node of textNodes(root)) {
    const next = node.data.replace(re, () => {
      count++
      return replacement
    })
    if (next !== node.data) node.data = next
  }
  return count
}

/** Selects the next match after the caret (wrapping around); false when there is none. */
export function selectNext(root: HTMLElement, find: string, matchCase: boolean): boolean {
  if (!find) return false
  const doc = root.ownerDocument
  const sel = doc.getSelection()
  const after = sel?.rangeCount ? sel.getRangeAt(0) : null
  const nodes = textNodes(root)
  const hits: { node: Text; start: number }[] = []
  const re = pattern(find, matchCase)
  for (const node of nodes) for (const m of node.data.matchAll(re)) hits.push({ node, start: m.index ?? 0 })
  if (!hits.length) return false
  const isAfter = (h: { node: Text; start: number }) => {
    if (!after) return true
    const r = doc.createRange()
    r.setStart(h.node, h.start)
    return r.compareBoundaryPoints(Range.END_TO_END, after) > 0 || (h.node === after.endContainer && h.start >= after.endOffset)
  }
  const hit = hits.find(isAfter) ?? hits[0]
  const range = doc.createRange()
  range.setStart(hit.node, hit.start)
  range.setEnd(hit.node, hit.start + find.length)
  sel?.removeAllRanges()
  sel?.addRange(range)
  hit.node.parentElement?.scrollIntoView({ block: 'nearest' })
  return true
}

// ---- clean-up ----

const INLINE = new Set(['SPAN', 'FONT', 'B', 'STRONG', 'I', 'EM', 'U', 'S', 'STRIKE', 'SMALL', 'BIG', 'MARK', 'SUB', 'SUP'])

/** What pasting and editing leave behind: empty styles and inline tags, spans without attributes, trailing empty
 * lines, Word/Docs class and data attributes. Returns how many things it removed. */
export function cleanUp(root: HTMLElement): number {
  let removed = 0
  for (const el of Array.from(root.querySelectorAll<HTMLElement>('*'))) {
    for (const attr of Array.from(el.attributes)) {
      if (attr.name.startsWith('data-') || attr.name === 'class' || attr.name === 'id' || (attr.name === 'style' && !attr.value.trim())) {
        el.removeAttribute(attr.name)
        removed++
      }
    }
  }
  // innermost first, so an emptied parent goes too
  for (const el of Array.from(root.querySelectorAll<HTMLElement>('*')).reverse()) {
    if (!INLINE.has(el.tagName)) continue
    if (!el.textContent?.length && !el.querySelector('img, br, video, audio')) {
      el.remove()
      removed++
    } else if ((el.tagName === 'SPAN' || el.tagName === 'FONT') && !el.attributes.length) {
      el.replaceWith(...Array.from(el.childNodes))
      removed++
    }
  }
  // empty lines at the end
  for (let last = root.lastChild; last; last = root.lastChild) {
    const empty =
      (last.nodeType === TEXT && !last.textContent?.trim()) ||
      (last.nodeType === ELEMENT && ['P', 'DIV', 'BR'].includes((last as Element).tagName) && !(last as Element).textContent?.trim() && !(last as Element).querySelector('img, video, table'))
    if (!empty) break
    last.remove()
    removed++
  }
  root.normalize()
  return removed
}
