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
  return timestamps.map((at) =>
    new Date(at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  )
}
