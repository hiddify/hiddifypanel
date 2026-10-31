/**
 * Country flags as SVG images (flag-icons), in place of flag emoji: the same look on every system (Windows has no
 * flag emoji and shows two letters). Each flag is a separate small file, fetched only when shown.
 */
const FLAG_URLS = import.meta.glob('../../../node_modules/flag-icons/flags/4x3/*.svg', {
  eager: true,
  query: '?no-inline',
  import: 'default',
}) as Record<string, string>

const BY_CODE: Record<string, string> = Object.fromEntries(
  Object.entries(FLAG_URLS).map(([file, url]) => [file.replace(/^.*\/([a-z0-9-]+)\.svg$/, '$1'), url]),
)

/** The flag image of a two-letter country code (any case), or '' when there is none. */
export function flagUrl(code: string | null | undefined): string {
  return BY_CODE[(code ?? '').toLowerCase()] ?? ''
}

/** The country code of a flag emoji (two regional indicator letters), e.g. "🇮🇷" → "ir". */
export function flagCodeOfEmoji(emoji: string): string {
  const letters = [...emoji].map((ch) => ch.codePointAt(0)! - 0x1f1e6)
  return letters.length === 2 && letters.every((n) => n >= 0 && n < 26) ? String.fromCharCode(...letters.map((n) => 97 + n)) : ''
}
