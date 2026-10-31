/**
 * The support box of the user page, drawn in a sandboxed iframe (no scripts run in it): the editor's visual mode and the
 * "View" preview show the text as users see it.
 *
 * The user page resets headings, lists, paragraphs and links to plain text (Tailwind's preflight), so the frame does the
 * same, and the editor's tools write inline styles for them (BLOCK_STYLES): what looks right here looks right there.
 */

export interface FrameLabels {
  title: string
  more: string
  placeholder: string
}

export const USER_PAGE_BOX_WIDTH = 360

/** Inline styles the tools give to what they create, so the user page shows them like the editor does. */
export const BLOCK_STYLES: Record<string, string> = {
  h1: 'font-size: 2em; font-weight: 700; line-height: 1.25; margin: 0 0 0.5em',
  h2: 'font-size: 1.5em; font-weight: 700; line-height: 1.3; margin: 0 0 0.5em',
  h3: 'font-size: 1.25em; font-weight: 600; line-height: 1.35; margin: 0 0 0.5em',
  h4: 'font-size: 1.1em; font-weight: 600; margin: 0 0 0.5em',
  h5: 'font-size: 1em; font-weight: 600; margin: 0 0 0.5em',
  h6: 'font-size: 0.9em; font-weight: 600; margin: 0 0 0.5em',
  p: 'margin: 0 0 0.5em',
  pre: 'margin: 0 0 0.5em; padding: 0.75em; border-radius: 8px; background: #f1f3f5; font-family: ui-monospace, monospace; white-space: pre-wrap',
  blockquote: 'margin: 0 0 0.5em; padding: 0.5em 1em; border-inline-start: 4px solid #455fe9; border-radius: 6px; background: #eef1fd',
  ul: 'list-style: disc; margin: 0 0 0.5em; padding-inline-start: 1.5em',
  ol: 'list-style: decimal; margin: 0 0 0.5em; padding-inline-start: 1.5em',
  a: 'color: #455fe9; text-decoration: underline',
}

export const SNIPPETS = {
  hr: '<hr style="border: 0; border-top: 1px solid #dee2e6; margin: 12px 0">',
  box: (text: string) =>
    `<div style="margin: 0 0 8px; padding: 12px 14px; border-radius: 12px; background: #eef1fd; border: 1px solid #d7ddfb">${text}</div>`,
  button: (text: string, href: string) =>
    `<a href="${escapeAttr(href)}" target="_blank" style="display: inline-block; padding: 8px 18px; border-radius: 999px; background: #455fe9; color: #ffffff; font-weight: 600; text-decoration: none">${text}</a>`,
  table: (rows: number, cols: number) => {
    const cell = '<td style="border: 1px solid #dee2e6; padding: 6px 8px">&nbsp;</td>'
    const row = `<tr>${cell.repeat(cols)}</tr>`
    return `<table style="width: 100%; border-collapse: collapse; margin: 0 0 8px"><tbody>${row.repeat(rows)}</tbody></table>`
  },
  faq: (question: string, answer: string) =>
    `<details style="margin: 0 0 8px; padding: 10px 12px; border-radius: 10px; background: #ffffff; border: 1px solid #dee2e6"><summary style="font-weight: 600">${escapeText(question)}</summary><p style="margin: 8px 0 0">${escapeText(answer)}</p></details>`,
  image: (src: string, alt: string, width: string) =>
    `<img src="${escapeAttr(src)}" alt="${escapeAttr(alt)}"${width ? ` width="${escapeAttr(width)}"` : ''} style="max-width: 100%; height: auto; border-radius: 8px">`,
}

const BLOCK_TAGS = /^(P|DIV|H[1-6]|LI|BLOCKQUOTE|PRE|TD|TH)$/

/** The block (a direct or nested block element of ``content``) the caret is in; null when the caret is in no block. */
export function caretBlock(doc: Document, content: HTMLElement): HTMLElement | null {
  const range = doc.getSelection()?.rangeCount ? doc.getSelection()!.getRangeAt(0) : null
  if (!range) return null
  let node: Node | null = range.startContainer
  // the caret between children of an element (an empty line): the child it is at. (Nodes of the frame are not
  // ``instanceof`` this window's classes: compare node types.)
  if (node.nodeType === Node.ELEMENT_NODE && node.childNodes.length) node = node.childNodes[Math.min(range.startOffset, node.childNodes.length - 1)]
  let el = node.nodeType === Node.ELEMENT_NODE ? (node as HTMLElement) : node.parentElement
  while (el && el !== content && !BLOCK_TAGS.test(el.tagName)) el = el.parentElement
  return el && el !== content && content.contains(el) ? el : null
}

export function escapeAttr(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeText(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** The frame's document: the user page around the box; ``#content`` holds the text (editable in the editor). */
export function frameDocument(labels: FrameLabels, dir: 'ltr' | 'rtl', editable: boolean): string {
  return `<!doctype html><html dir="${dir}"><head><meta charset="utf-8"><style>
html, body { margin: 0; color-scheme: light; }
body { min-height: 100vh; box-sizing: border-box; padding: 28px 16px; display: flex; justify-content: center; align-items: flex-start;
  background: radial-gradient(circle at 1px 1px, #dfe3f0 1px, transparent 0) 0 0 / 16px 16px, #f4f5fa;
  font: 14px/1.5 Roboto, "Segoe UI", system-ui, -apple-system, Vazirmatn, Tahoma, sans-serif; color: #495057; }
*, ::before, ::after { box-sizing: border-box; }
.card { width: ${USER_PAGE_BOX_WIDTH}px; max-width: 100%; padding: 16px; border-radius: 16px; background: #e9ebf6;
  box-shadow: 0 1px 2px rgb(15 23 42 / 6%), 0 12px 32px -18px rgb(15 23 42 / 30%); }
.title { font-size: 18px; font-weight: 500; color: #000; margin-bottom: 16px; }
.more { display: flex; justify-content: flex-end; margin-top: 20px; }
.more span { border: 1px solid #455fe9; color: #455fe9; border-radius: 8px; padding: 6px 12px; font-size: 14px; }
/* the user page's reset (Tailwind preflight) */
h1, h2, h3, h4, h5, h6 { font-size: inherit; font-weight: inherit; margin: 0; }
p, blockquote, figure, pre, hr { margin: 0; }
ol, ul { list-style: none; margin: 0; padding: 0; }
a { color: inherit; text-decoration: inherit; }
img, video { max-width: 100%; height: auto; }
table { border-collapse: collapse; }
#content { min-height: 72px; outline: none; overflow-wrap: anywhere; caret-color: #455fe9; }
#content:empty::before { content: attr(data-placeholder); color: #adb5bd; pointer-events: none; }
${editable ? '#content { border-radius: 8px; box-shadow: 0 0 0 1px transparent; transition: box-shadow .2s; } #content:focus { box-shadow: 0 0 0 2px rgb(69 95 233 / 25%); } #content a { cursor: text; } #content td { min-width: 2em; }' : ''}
</style></head><body><div class="card"><div class="title">${escapeText(labels.title)}</div>
<div id="content"${editable ? ' contenteditable="true" spellcheck="false"' : ''} data-placeholder="${escapeAttr(labels.placeholder)}"></div>
<div class="more"><span>${escapeText(labels.more)}</span></div></div></body></html>`
}
