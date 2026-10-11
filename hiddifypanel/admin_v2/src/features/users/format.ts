/** Display helpers shared by the users list and form (relative times as the classic user list shows them). */

import { unitLabel } from '@/shared/utils/format-metrics'

export type Tone = 'ok' | 'warn' | 'danger' | 'muted'

export const ONE_GIG = 1024 ** 3

/** Stable colors for the per-node usage breakdown (same node id → same color everywhere). */
export const NODE_COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#84cc16', '#f43f5e'] as const

export function nodeColor(childId: number): string {
  return NODE_COLORS[Math.abs(childId) % NODE_COLORS.length]!
}

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

/** A user's data amount from GB, never smaller than MB: `40 MB`, `12.5 GB` (`۴۰ مگ`, `۱۲٫۵ گیگ` in Persian). */
export function sizeText(gigabytes: number, locale: string): string {
  const value = Number(gigabytes) || 0
  const number = (n: number, max: number) => new Intl.NumberFormat(locale, { maximumFractionDigits: max }).format(n)
  if (value >= 1024) return `${number(value / 1024, 2)} ${unitLabel('TB', locale)}`
  if (value >= 1) return `${number(value, value < 100 ? 2 : 1)} ${unitLabel('GB', locale)}`
  const mb = value * 1024
  return `${number(mb, mb < 10 ? 1 : 0)} ${unitLabel('MB', locale)}`
}

/** `0.029`, `12.5`, `3000`: GB without needless zeros. */
export function gb(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: value < 1 ? 3 : value < 100 ? 2 : 1 }).format(value || 0)
}

/** Persian shows the Persian (Jalali) calendar, everything else the Gregorian one. */
export function dateLocale(locale: string): string {
  return locale.toLowerCase().startsWith('fa') ? 'fa-IR-u-ca-persian' : locale
}

export function shortDate(iso: string | null, locale: string): string {
  if (!iso) return ''
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(dateLocale(locale), { year: 'numeric', month: 'short', day: 'numeric' })
}

/** "Tuesday, 14 October 2026" (Jalali in Persian): the full date, for a long press. */
export function exactDate(iso: string | null, locale: string): string {
  if (!iso) return ''
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(dateLocale(locale), { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

/** Date and time, e.g. for a last-online tooltip. */
export function exactDateTime(iso: string | null, locale: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(dateLocale(locale), { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** Days from today to an ISO date (negative: in the past). */
export function daysFromToday(iso: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((new Date(`${iso.slice(0, 10)}T00:00:00`).getTime() - today.getTime()) / 86400000)
}
