/** Dates in the admin's language: Persian shows the Persian (Jalali) calendar, everything else the Gregorian one. */

export function dateLocale(locale: string): string {
  return locale.toLowerCase().startsWith('fa') ? 'fa-IR-u-ca-persian' : locale
}

/** "14 October 2026" (Jalali in Persian) of a moment (an ISO string with its time zone). */
export function longDate(iso: string | null, locale: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(dateLocale(locale), { year: 'numeric', month: 'long', day: 'numeric' })
}

/** Whole days from now until ``iso`` (0 when it is past or today); null without a date. */
export function daysUntil(iso: string | null, now: number = Date.now()): number | null {
  if (!iso) return null
  const at = Date.parse(iso)
  return Number.isNaN(at) ? null : Math.max(0, Math.floor((at - now) / 86_400_000))
}
