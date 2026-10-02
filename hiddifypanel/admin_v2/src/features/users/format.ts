/** Display helpers shared by the users list and form (relative times as the classic user list shows them). */

export type Tone = 'ok' | 'warn' | 'danger' | 'muted'

const DAY_UNITS: [Intl.RelativeTimeFormatUnit, number, number][] = [
  // unit, size in days, used below this many days
  ['day', 1, 14],
  ['week', 7, 60],
  ['month', 30, 730],
  ['year', 365, Infinity],
]

/** "in 3 months", "2 weeks ago", "today": a day count relative to today. */
export function relativeDays(days: number, locale: string): string {
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const abs = Math.abs(days)
  for (const [unit, size, below] of DAY_UNITS) {
    if (abs < below) return rtf.format(Math.round(days / size), unit)
  }
  return rtf.format(days, 'day')
}

/** Expiry color, as the classic list: more than a week left ok, some left warn, none danger. */
export function expireTone(remainingDays: number): Tone {
  return remainingDays > 7 ? 'ok' : remainingDays >= 0 ? 'warn' : 'danger'
}

export interface LastSeen {
  text: string
  tone: Tone
  online: boolean
}

/** Last connection: "Online" within 2 minutes, else relative; green within a day, yellow within 3, red after. */
export function lastSeen(iso: string | null, now: number, locale: string, labels: { online: string; never: string }): LastSeen {
  if (!iso) return { text: labels.never, tone: 'muted', online: false }
  const seconds = (new Date(iso).getTime() - now) / 1000
  if (seconds > -120) return { text: labels.online, tone: 'ok', online: true }
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const abs = Math.abs(seconds)
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const [unit, size] = units.find(([, s]) => abs >= s) ?? ['minute', 60]
  const days = abs / 86400
  return { text: rtf.format(Math.round(seconds / size), unit), tone: days <= 1 ? 'ok' : days <= 3 ? 'warn' : 'danger', online: false }
}

/** `0.029`, `12.5`, `3000`: GB without needless zeros. */
export function gb(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: value < 1 ? 3 : value < 100 ? 2 : 1 }).format(value || 0)
}

export function shortDate(iso: string | null, locale: string): string {
  if (!iso) return ''
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
}

/** Days from today to an ISO date (negative: in the past). */
export function daysFromToday(iso: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((new Date(`${iso.slice(0, 10)}T00:00:00`).getTime() - today.getTime()) / 86400000)
}
