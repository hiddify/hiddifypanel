import QRCode from 'qrcode'
import logoUrl from '@/assets/images/hiddify-qr-logo.png'

/**
 * QR codes like hiddify-user-front's (react-qrcode-logo there, qrStyle "dots"): 75% dots with gaps,
 * soft rounded eyes, black on white, and the Hiddify logo in the middle with only
 * the dots that would touch it removed.
 */
export interface HiddifyQrOptions {
  /** CSS pixels of the code (without the quiet zone). */
  size: number
  /** Blank margin around the code, in CSS pixels (user-front shows 0; exports need some to scan well). */
  quietZone?: number
  /** Null: transparent. */
  background?: string | null
  /** Pixel density; defaults to the screen's. */
  scale?: number
}

const INK = '#000000'
/** Background; the logo's outline is white, so the logo blends into it. */
export const QR_CARD_COLOR = '#ffffff'
/** Logo width / code width. */
const LOGO_RATIO = 0.25
/** Clear margin around the logo, in modules: just enough that no dot touches it. */
const LOGO_MARGIN = 0.6
/** Dot diameter / module size (react-qrcode-logo "dots": 75%). */
const DOT_RATIO = 0.75
/** Eye corner radius / code size (user-front: eyeRadius 5 on a 150px code). */
const EYE_RADIUS_RATIO = 5 / 150

interface Logo {
  /** The logo with its gray turned black, to match the code. */
  image: HTMLCanvasElement
  /** Alpha channel at natural size, to clear dots only where the logo actually is. */
  alpha: Uint8ClampedArray
  width: number
  height: number
}

let logoPromise: Promise<Logo> | null = null
function loadLogo(): Promise<Logo> {
  logoPromise ??= new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const width = image.naturalWidth
      const height = image.naturalHeight
      const c = document.createElement('canvas')
      c.width = width
      c.height = height
      const cx = c.getContext('2d')
      if (!cx) return reject(new Error('no 2d context'))
      cx.drawImage(image, 0, 0)
      const pixels = cx.getImageData(0, 0, width, height)
      const data = pixels.data
      const alpha = new Uint8ClampedArray(width * height)
      for (let i = 0; i < alpha.length; i++) {
        alpha[i] = data[i * 4 + 3]!
        // Gray glyph (#495057) -> black; the white outline keeps its lightness (anti-aliased edges scale with it).
        const lightness = Math.max(0, (data[i * 4]! - 73) / (255 - 73))
        data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = Math.round(lightness * 255)
      }
      cx.putImageData(pixels, 0, 0)
      resolve({ image: c, alpha, width, height })
    }
    image.onerror = reject
    image.src = logoUrl
  })
  return logoPromise
}

/** Whether any opaque logo pixel lies within `reach` of (x, y); coordinates in logo-box pixels. */
function nearLogo(logo: Logo, boxW: number, boxH: number, x: number, y: number, reach: number): boolean {
  const sx = logo.width / boxW
  const sy = logo.height / boxH
  const steps = 6
  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const px = x - reach + (2 * reach * i) / steps
      const py = y - reach + (2 * reach * j) / steps
      if ((px - x) ** 2 + (py - y) ** 2 > reach * reach) continue
      if (px < 0 || py < 0 || px >= boxW || py >= boxH) continue
      if (logo.alpha[Math.floor(py * sy) * logo.width + Math.floor(px * sx)]! > 24) return true
    }
  }
  return false
}

/** react-qrcode-logo's eye square: stroke inside the box edges, soft (quadratic) corners. */
function eyeSquare(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, lineWidth: number, radius: number, fill: boolean) {
  ctx.lineWidth = lineWidth
  x += lineWidth / 2
  y += lineWidth / 2
  size -= lineWidth
  const r = Math.max(0, Math.min(radius, size / 2))
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + size - r, y)
  ctx.quadraticCurveTo(x + size, y, x + size, y + r)
  ctx.lineTo(x + size, y + size - r)
  ctx.quadraticCurveTo(x + size, y + size, x + size - r, y + size)
  ctx.lineTo(x + r, y + size)
  ctx.quadraticCurveTo(x, y + size, x, y + size - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
  ctx.stroke()
  if (fill) ctx.fill()
}

/** Draws `text` onto `canvas` (resized to fit). */
export async function drawHiddifyQr(canvas: HTMLCanvasElement, text: string, options: HiddifyQrOptions): Promise<void> {
  const { size, quietZone = 0, background = null } = options
  const scale = options.scale ?? Math.max(1, window.devicePixelRatio || 1)
  // A centered logo hides part of the code: high error correction keeps long links scannable.
  const qr = QRCode.create(text, { errorCorrectionLevel: 'H' })
  const count = qr.modules.size
  const cell = size / count
  const total = size + quietZone * 2

  canvas.width = Math.round(total * scale)
  canvas.height = Math.round(total * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(scale, 0, 0, scale, 0, 0)
  ctx.clearRect(0, 0, total, total)
  if (background) {
    ctx.fillStyle = background
    ctx.fillRect(0, 0, total, total)
  }
  ctx.translate(quietZone, quietZone)

  let logo: Logo | null = null
  try {
    logo = await loadLogo()
  } catch {
    // Without the logo nothing is cleared and the code is complete.
  }
  const ratio = logo ? logo.width / logo.height || 1 : 1
  const logoW = ratio >= 1 ? size * LOGO_RATIO : size * LOGO_RATIO * ratio
  const logoH = ratio >= 1 ? (size * LOGO_RATIO) / ratio : size * LOGO_RATIO
  const logoX = (size - logoW) / 2
  const logoY = (size - logoH) / 2

  const dotRadius = (cell / 2) * DOT_RATIO
  // A dot is dropped only if it would come closer than LOGO_MARGIN modules to the logo's own
  // pixels, so the clear area follows the logo's shape instead of a wide square.
  const margin = cell * LOGO_MARGIN + dotRadius
  const behindLogo = (cx: number, cy: number) =>
    logo !== null &&
    cx > logoX - margin &&
    cx < logoX + logoW + margin &&
    cy > logoY - margin &&
    cy < logoY + logoH + margin &&
    nearLogo(logo, logoW, logoH, cx - logoX, cy - logoY, margin)

  // Finder patterns ("eyes") are drawn as rounded squares, not dots.
  const eyes: [number, number][] = [
    [0, 0],
    [0, count - 7],
    [count - 7, 0],
  ]
  const inEye = (row: number, col: number) => eyes.some(([r, c]) => row >= r && row < r + 7 && col >= c && col < c + 7)

  ctx.fillStyle = INK
  for (let row = 0; row < count; row++) {
    for (let col = 0; col < count; col++) {
      if (!qr.modules.get(row, col) || inEye(row, col)) continue
      const cx = col * cell + cell / 2
      const cy = row * cell + cell / 2
      if (behindLogo(cx, cy)) continue
      ctx.beginPath()
      ctx.arc(cx, cy, dotRadius, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  ctx.strokeStyle = INK
  const eyeLine = cell
  const eyeRadius = size * EYE_RADIUS_RATIO
  for (const [r, c] of eyes) {
    eyeSquare(ctx, c * cell, r * cell, cell * 7, eyeLine, eyeRadius, false)
    // Inner block: a rounded square, not a dot.
    eyeSquare(ctx, c * cell + cell * 2, r * cell + cell * 2, cell * 3, eyeLine, cell * 0.5, true)
  }

  if (logo) ctx.drawImage(logo.image, logoX, logoY, logoW, logoH)
}
/** A PNG of the code on the same light card color, with a quiet zone so it scans from anywhere. */
export async function hiddifyQrPng(text: string, size = 600): Promise<Blob> {
  const canvas = document.createElement('canvas')
  await drawHiddifyQr(canvas, text, { size, quietZone: Math.round(size * 0.07), background: QR_CARD_COLOR, scale: 1 })
  return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png'))
}

function canWriteRichClipboard(): boolean {
  return typeof ClipboardItem !== 'undefined' && typeof navigator.clipboard?.write === 'function'
}

/** Copies the QR code of `value` as an image. Rejects where the browser can not copy images (some browsers, plain http). */
export async function copyQrImage(value: string): Promise<void> {
  if (!canWriteRichClipboard()) throw new Error('unsupported')
  // The promise is passed straight to ClipboardItem so Safari keeps the click's permission.
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': hiddifyQrPng(value) })])
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]!)
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

/**
 * Copies `message` together with the QR code of `qrValue`: plain text, an HTML version with the image
 * (rich editors and mail paste both), and the image itself (apps that take images).
 * Resolves `true` when the image went along, `false` when only the text could be copied.
 */
export async function copyMessageWithQr(message: string, qrValue: string): Promise<boolean> {
  if (canWriteRichClipboard()) {
    try {
      const png = hiddifyQrPng(qrValue)
      const html = png.then(async (blob) => {
        const src = await blobToDataUrl(blob)
        const body = escapeHtml(message).replace(/\n/g, '<br>')
        return new Blob([`<div>${body}</div><p><img src="${src}" alt="QR" width="240" height="240"></p>`], { type: 'text/html' })
      })
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/plain': new Blob([message], { type: 'text/plain' }),
          'text/html': html,
          'image/png': png,
        }),
      ])
      return true
    } catch {
      // Some browsers refuse several types at once: fall back to the text alone.
    }
  }
  await navigator.clipboard.writeText(message)
  return false
}

/** Saves the QR code of `value` as a PNG file. */
export async function downloadQrPng(value: string, fileName: string): Promise<void> {
  const url = URL.createObjectURL(await hiddifyQrPng(value))
  const a = document.createElement('a')
  a.href = url
  a.download = fileName.endsWith('.png') ? fileName : `${fileName}.png`
  a.click()
  URL.revokeObjectURL(url)
}

/** Splits `text` into lines that fit `maxWidth`, breaking anywhere (links have no spaces). */
function wrapAnywhere(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const ch of text) {
    if (line && ctx.measureText(line + ch).width > maxWidth) {
      lines.push(line)
      line = ch
    } else {
      line += ch
    }
  }
  if (line) lines.push(line)
  return lines
}

/**
 * A share card: the QR code with a title and the link written under it, so the link still reaches
 * apps that keep only the image from a share (e.g. Notes on macOS). Never put secrets in `caption`.
 */
export async function hiddifyQrCardPng(value: string, card: { title?: string; caption: string }): Promise<Blob> {
  const width = 720
  const pad = 48
  const qrSize = width - pad * 2
  const qr = document.createElement('canvas')
  await drawHiddifyQr(qr, value, { size: qrSize, background: '#ffffff', scale: 1 })

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) return hiddifyQrPng(value)
  const font = 'system-ui, -apple-system, "Segoe UI", Roboto, Vazirmatn, sans-serif'
  const mono = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
  ctx.font = `500 26px ${mono}`
  const captionLines = wrapAnywhere(ctx, card.caption, qrSize)
  const titleHeight = card.title ? 56 : 0
  const height = pad + qrSize + 28 + titleHeight + captionLines.length * 36 + pad

  canvas.width = width
  canvas.height = height
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)
  ctx.drawImage(qr, pad, pad)

  let y = pad + qrSize + 28
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  if (card.title) {
    ctx.fillStyle = '#000000'
    ctx.font = `700 36px ${font}`
    ctx.fillText(card.title, width / 2, y, qrSize)
    y += titleHeight
  }
  ctx.fillStyle = '#374151'
  ctx.font = `500 26px ${mono}`
  for (const line of captionLines) {
    ctx.fillText(line, width / 2, y)
    y += 36
  }
  return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png'))
}

/** The share card of `value` (QR + title + link) as a PNG file, ready to share. */
export async function qrPngFile(value: string, fileName: string, card?: { title?: string; caption: string }): Promise<File> {
  const blob = card ? await hiddifyQrCardPng(value, card) : await hiddifyQrPng(value)
  return new File([blob], fileName.endsWith('.png') ? fileName : `${fileName}.png`, { type: 'image/png' })
}

/** Whether this browser can share an image file through the system share sheet (Telegram, WhatsApp, mail…). */
export function canShareImages(): boolean {
  try {
    const probe = new File([new Uint8Array([0])], 'probe.png', { type: 'image/png' })
    return typeof navigator.share === 'function' && typeof navigator.canShare === 'function' && navigator.canShare({ files: [probe] })
  } catch {
    return false
  }
}

/**
 * Sends `text` (and on Apple devices `url`) with the image through the share sheet, the only way the
 * receiving app gets both (from the clipboard, most apps paste just the text). Pass a file made in advance: browsers only
 * allow sharing right after the click, so there is no time to draw the image then.
 */
export async function shareWithImage(text: string, file: File, url?: string): Promise<'shared' | 'cancelled' | 'failed'> {
  // macOS / iOS give apps a URL as its own item, which they keep next to an image (Notes drops plain
  // text there). Elsewhere (Android) the URL is glued onto the text, so it would show twice.
  const apple = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent)
  const data: ShareData = { text, files: [file] }
  if (url && apple) {
    data.url = url
    if (text.trim() === url) delete data.text
  }
  try {
    await navigator.share(data)
    return 'shared'
  } catch (err) {
    return (err as { name?: string })?.name === 'AbortError' ? 'cancelled' : 'failed'
  }
}
