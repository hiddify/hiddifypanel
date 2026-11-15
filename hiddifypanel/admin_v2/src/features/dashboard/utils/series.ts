/** Trailing average over `window` samples; the first samples use what exists. */
export function rollingAverage(values: number[], window: number): number[] {
  return values.map((_, index) => {
    const start = Math.max(0, index - window + 1)
    const slice = values.slice(start, index + 1)
    return Math.round(slice.reduce((sum, value) => sum + value, 0) / slice.length)
  })
}

/** Clock labels (`HH:MM:SS`) for live samples. */
export function timeLabels(timestamps: number[], locale?: string): string[] {
  // A 24-hour clock: "18:19:02" is three letters shorter than "06:19:02 PM", so the live charts' time axis has room on
  // a phone (it spans a minute or two, so the seconds stay)
  return timestamps.map((at) =>
    new Date(at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }),
  )
}
