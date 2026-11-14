/**
 * Country flags as SVG images (flag-icons), in place of flag emoji: the same look on every system (Windows has no
 * flag emoji and shows two letters). Each flag is a separate small file, fetched only when shown.
 */
import irLionAndSun from '@/assets/flags/ir-lion-and-sun.svg?no-inline'
const FLAG_URLS = import.meta.glob('../../../node_modules/flag-icons/flags/4x3/*.svg', {
  eager: true,
  query: '?no-inline',
  import: 'default',
}) as Record<string, string>

const BY_CODE: Record<string, string> = Object.fromEntries(
  Object.entries(FLAG_URLS).map(([file, url]) => [file.replace(/^.*\/([a-z0-9-]+)\.svg$/, '$1'), url]),
)
// Iran: the Lion and Sun flag
BY_CODE.ir = irLionAndSun

/** The flag image of a two-letter country code (any case), or '' when there is none. */
export function flagUrl(code: string | null | undefined): string {
  return BY_CODE[(code ?? '').toLowerCase()] ?? ''
}

/** The country code of a flag emoji (two regional indicator letters), e.g. "🇮🇷" → "ir". */
export function flagCodeOfEmoji(emoji: string): string {
  const letters = [...emoji].map((ch) => ch.codePointAt(0)! - 0x1f1e6)
  return letters.length === 2 && letters.every((n) => n >= 0 && n < 26) ? String.fromCharCode(...letters.map((n) => 97 + n)) : ''
}

const BITMAPS = new Map<string, Promise<string>>()

/**
 * The flag drawn once as a picture `scale` times finer than the screen needs (a data: URL), for a flag that is bent
 * and moved afterwards (FlagIcon `waving`): every browser then starts from the same smooth, oversampled picture, also
 * when zoomed in a little. Falls back to the SVG itself when it cannot be drawn.
 */
export function flagBitmap(url: string, cssWidth: number, scale = 2): Promise<string> {
  const width = Math.min(1600, Math.max(160, Math.ceil((cssWidth * (window.devicePixelRatio || 1) * scale) / 40) * 40))
  const key = `${url}@${width}`
  let made = BITMAPS.get(key)
  if (!made) {
    made = new Promise<string>((resolve) => {
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas')
          canvas.width = width
          canvas.height = Math.round((width * 3) / 4)
          const ctx = canvas.getContext('2d')!
          ctx.imageSmoothingEnabled = true
          ctx.imageSmoothingQuality = 'high'
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          resolve(canvas.toDataURL('image/png'))
        } catch {
          resolve(url)
        }
      }
      img.onerror = () => resolve(url)
      img.src = url
    })
    BITMAPS.set(key, made)
  }
  return made
}
