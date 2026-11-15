/**
 * Days and months for the dashboard's period picker, in the page's own calendar (Persian in Persian, Gregorian
 * elsewhere), from the browser's Intl: no calendar library. Days are local dates ``YYYY-MM-DD``, as the API sends them.
 */

/** Usage is kept per day for this long (the longest range the dashboard API returns) */
export const MAX_DAYS = 365
/** The ranges the API accepts; a picked period asks for the shortest one that covers it */
export const API_DAYS = [7, 14, 30, 90, 180, 365] as const

export const QUICK_PRESETS = ['today', 'yesterday', 'last7', 'last14', 'last30', 'thisMonth', 'lastMonth', 'last90', 'last180', 'last365'] as const
export type QuickPreset = (typeof QUICK_PRESETS)[number]

/** A picked period: a quick preset (kept as such, so "This month" stays this month tomorrow) or two fixed days */
export interface CustomRange {
  preset?: QuickPreset
  start: string
  end: string
}

export const iso = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
/** Noon: no daylight-saving edge moves it to another day */
export const fromIso = (day: string) => new Date(`${day}T12:00:00`)
export const addDays = (date: Date, days: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}
export const today = () => {
  const now = new Date()
  now.setHours(12, 0, 0, 0)
  return now
}
export const daysBetween = (start: string, end: string) => Math.round((fromIso(end).getTime() - fromIso(start).getTime()) / 86400000) + 1

export const persian = (locale: string) => locale.startsWith('fa')
const calendarLocale = (locale: string) => (persian(locale) ? 'fa-IR-u-ca-persian-nu-latn' : 'en-u-ca-gregory-nu-latn')

/** A date's year / month / day in the page's calendar */
export function calendarParts(date: Date, locale: string): { y: number; m: number; d: number } {
  const parts = new Intl.DateTimeFormat(calendarLocale(locale), { year: 'numeric', month: 'numeric', day: 'numeric' }).formatToParts(date)
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value.replace(/\D/g, '') ?? 0)
  return { y: get('year'), m: get('month'), d: get('day') }
}

/** The first and last day of the calendar month holding ``date`` */
export function monthBounds(date: Date, locale: string): { first: Date; last: Date } {
  const { d } = calendarParts(date, locale)
  const first = addDays(date, 1 - d)
  let last = first
  const month = calendarParts(first, locale).m
  while (calendarParts(addDays(last, 1), locale).m === month) last = addDays(last, 1)
  return { first, last }
}

/** A quick preset's days, as of today */
export function presetRange(preset: QuickPreset, locale: string): CustomRange {
  const now = today()
  const days = (n: number) => ({ preset, start: iso(addDays(now, 1 - n)), end: iso(now) })
  switch (preset) {
    case 'today':
      return { preset, start: iso(now), end: iso(now) }
    case 'yesterday':
      return { preset, start: iso(addDays(now, -1)), end: iso(addDays(now, -1)) }
    case 'thisMonth':
      return { preset, start: iso(monthBounds(now, locale).first), end: iso(now) }
    case 'lastMonth': {
      const last = addDays(monthBounds(now, locale).first, -1)
      return { preset, start: iso(monthBounds(last, locale).first), end: iso(last) }
    }
    default:
      return days(Number(preset.replace('last', '')))
  }
}

export interface MonthGrid {
  title: string
  /** Weekday initials, in the week's order (Saturday first in Persian, Monday elsewhere) */
  weekdays: string[]
  /** Blank cells before the first day, then the days */
  lead: number
  days: { iso: string; label: string }[]
  first: Date
  last: Date
}

export function monthGrid(anchor: Date, locale: string): MonthGrid {
  const { first, last } = monthBounds(anchor, locale)
  const fa = persian(locale)
  const weekStart = fa ? 6 : 1
  const dayFormat = new Intl.DateTimeFormat(fa ? 'fa-IR-u-ca-persian' : locale, { day: 'numeric' })
  const days: MonthGrid['days'] = []
  for (let day = first; day <= last; day = addDays(day, 1)) days.push({ iso: iso(day), label: dayFormat.format(day) })
  const weekdayFormat = new Intl.DateTimeFormat(fa ? 'fa-IR' : locale, { weekday: 'narrow' })
  // 2024-01-01 was a Monday
  const weekdays = Array.from({ length: 7 }, (_, i) => weekdayFormat.format(new Date(2024, 0, 1 + ((weekStart - 1 + i + 7) % 7), 12)))
  return {
    title: new Intl.DateTimeFormat(fa ? 'fa-IR-u-ca-persian' : locale, { month: 'long', year: 'numeric' }).format(first),
    weekdays,
    lead: (first.getDay() - weekStart + 7) % 7,
    days,
    first,
    last,
  }
}

/** A short day in the page's calendar: "10 Nov", «۱۰ آبان» */
export function shortDay(day: string, locale: string): string {
  return new Intl.DateTimeFormat(persian(locale) ? 'fa-IR-u-ca-persian' : locale, { month: 'short', day: 'numeric' }).format(fromIso(day))
}
