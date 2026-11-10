import { dateLocale } from '@/shared/utils/dates'

/** 0.5 → { amount: 512, unit: 'mb' }; 2 → { amount: 2, unit: 'gb' } (megabytes under one gigabyte). */
export function splitData(usageGb: number): { amount: number; unit: 'mb' | 'gb' } {
  return usageGb < 1 ? { amount: Math.round(usageGb * 1024), unit: 'mb' } : { amount: Math.round(usageGb * 100) / 100, unit: 'gb' }
}

/** The time today, the weekday this week, else the date. */
export function shortWhen(iso: string | null, locale: string, now: number = Date.now()): string {
  if (!iso) return ''
  const date = new Date(iso)
  const tag = dateLocale(locale)
  const days = Math.floor((now - date.getTime()) / 86_400_000)
  if (date.toDateString() === new Date(now).toDateString()) return date.toLocaleTimeString(tag, { hour: '2-digit', minute: '2-digit' })
  if (days < 6) return date.toLocaleDateString(tag, { weekday: 'short' })
  return date.toLocaleDateString(tag, { month: 'short', day: 'numeric' })
}

export function clock(iso: string, locale: string): string {
  return new Date(iso).toLocaleTimeString(dateLocale(locale), { hour: '2-digit', minute: '2-digit' })
}

export function dayLabel(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(dateLocale(locale), { weekday: 'long', month: 'long', day: 'numeric' })
}

/** One or two letters for an avatar. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return (parts.length > 1 ? `${[...parts[0]][0]}${[...parts[1]][0]}` : [...(parts[0] ?? '?')].slice(0, 1).join('')).toUpperCase()
}

const HUES = [210, 262, 330, 20, 150, 185, 45]
/** A steady colour per person. */
export function avatarHue(id: number): number {
  return HUES[id % HUES.length]
}
