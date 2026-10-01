/** Terminal colours in log text (ANSI `ESC[..m`) as spans with classes, so a log reads like it does in a console. */

export interface AnsiSpan {
  text: string
  /** e.g. `fg-red bold`; empty for plain text. */
  cls: string
}

const COLORS = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
// eslint-disable-next-line no-control-regex
const SGR = /\x1b\[([0-9;]*)m/g
// Other escape sequences (cursor, clear line, ...): dropped.
// eslint-disable-next-line no-control-regex
const OTHER = /\x1b\[[0-9;?]*[A-Za-ln-z]/g

export class AnsiParser {
  private fg = ''
  private bold = false

  /** Keeps the current colour between chunks (a colour may be set in one chunk and reset in a later one). */
  parse(input: string): AnsiSpan[] {
    const text = input.replace(OTHER, '').replace(/\r(?!\n)/g, '\n')
    const spans: AnsiSpan[] = []
    let last = 0
    const push = (chunk: string) => {
      if (!chunk) return
      const cls = [this.fg && `fg-${this.fg}`, this.bold && 'bold'].filter(Boolean).join(' ')
      spans.push({ text: chunk, cls })
    }
    for (const m of text.matchAll(SGR)) {
      push(text.slice(last, m.index))
      last = (m.index ?? 0) + m[0].length
      for (const code of (m[1] || '0').split(';').map(Number)) {
        if (code === 0) {
          this.fg = ''
          this.bold = false
        } else if (code === 1) this.bold = true
        else if (code === 22) this.bold = false
        else if (code >= 30 && code <= 37) this.fg = COLORS[code - 30]!
        else if (code >= 90 && code <= 97) this.fg = `bright-${COLORS[code - 90]}`
        else if (code === 39) this.fg = ''
      }
    }
    push(text.slice(last))
    return spans
  }
}
