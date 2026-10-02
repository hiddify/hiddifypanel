const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
export const ONE_GB = 1024 ** 3

/** Compact byte size, e.g. `1.24 TB`. */
export function formatBytes(bytes: number, digits?: number): string {
  const value = Number(bytes) || 0
  if (value <= 0) return '0 B'
  const exponent = Math.min(BYTE_UNITS.length - 1, Math.floor(Math.log(value) / Math.log(1024)))
  const scaled = value / 1024 ** exponent
  const precision = digits ?? (scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2)
  return `${scaled.toFixed(precision)} ${BYTE_UNITS[exponent]}`
}

export function formatGb(gigabytes: number, digits?: number): string {
  return formatBytes((Number(gigabytes) || 0) * ONE_GB, digits)
}

export function bytesToGb(bytes: number): number {
  return (Number(bytes) || 0) / ONE_GB
}

/** Throughput in bits per second from a byte count, e.g. `12.4 Mb/s`. */
export function formatBitRate(bytesPerSecond: number): string {
  const bits = Math.max(0, Number(bytesPerSecond) || 0) * 8
  const units = ['b/s', 'Kb/s', 'Mb/s', 'Gb/s']
  let value = bits
  let unit = 0
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000
    unit += 1
  }
  const precision = value >= 100 ? 0 : value >= 10 ? 1 : 2
  return `${value.toFixed(precision)} ${units[unit]}`
}

export function formatPercent(value: number, digits = 0): string {
  return `${(Number(value) || 0).toFixed(digits)}%`
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(
    Number(value) || 0,
  )
}

/** Coarse uptime split into whole days, hours and minutes. */
export function durationParts(seconds: number): { days: number; hours: number; minutes: number } {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  return {
    days: Math.floor(total / 86400),
    hours: Math.floor((total % 86400) / 3600),
    minutes: Math.floor((total % 3600) / 60),
  }
}

export function formatDayLabel(isoDate: string, locale?: string): string {
  const date = new Date(`${isoDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return isoDate
  return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' })
}

export function formatClock(date: Date | null, locale?: string): string {
  if (!date) return '—'
  return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
