/** The flag emoji of a country code (two regional indicator letters); '' when there is none. */
export function countryFlag(code: string | null | undefined): string {
  const c = (code ?? '').toUpperCase()
  if (!/^[A-Z]{2}$/.test(c)) return ''
  return String.fromCodePoint(...[...c].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65))
}

/** A country code's name in the given language ("DE" → "Germany"); the code itself when unknown. */
export function countryName(code: string, locale: string): string {
  try {
    return new Intl.DisplayNames([locale], { type: 'region' }).of(code.toUpperCase()) ?? code
  } catch {
    return code
  }
}
