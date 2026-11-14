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

const BITMAPS = new Map<string, Promise<HTMLCanvasElement>>()

/**
 * The flag drawn once as a picture of exactly `width` x `height` pixels, for a flag that is bent and moved afterwards
 * (FlagIcon `waving` draws thin slices of it every frame; drawing the SVG itself that often would be slow, and each
 * browser would smooth it differently). Rejects when the picture cannot be drawn.
 */
export function flagBitmap(url: string, width: number, height: number): Promise<HTMLCanvasElement> {
  const key = `${url}@${width}x${height}`
  let made = BITMAPS.get(key)
  if (!made) {
    made = new Promise<HTMLCanvasElement>((resolve, reject) => {
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) return reject(new Error('no canvas'))
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'
        ctx.drawImage(img, 0, 0, width, height)
        resolve(canvas)
      }
      img.onerror = () => reject(new Error('flag image failed'))
      img.src = url
    })
    made.catch(() => BITMAPS.delete(key))
    BITMAPS.set(key, made)
  }
  return made
}
