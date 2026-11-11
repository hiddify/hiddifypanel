import QRCode from 'qrcode'
import { drawHiddifyQr, hiddifyQrPng, QR_CARD_COLOR } from '@/shared/utils/hiddify-qr'
import { unwrapSubscriptionText } from '@/shared/utils/sublink-pretty'

/**
 * Hiddify: dots and the logo, like the user page (high error correction, so it holds less text).
 * Plain: square modules without a logo, medium error correction: about twice as much text fits.
 */
export type QrStyle = 'hiddify' | 'plain'

const PLAIN_LEVEL = 'M'
const HIDDIFY_LEVEL = 'H'

/** Whether `text` fits in one QR code of this style. */
export function qrFits(text: string, style: QrStyle): boolean {
  try {
    QRCode.create(text, { errorCorrectionLevel: style === 'hiddify' ? HIDDIFY_LEVEL : PLAIN_LEVEL })
    return true
  } catch {
    return false
  }
}

/** Draws the code onto `canvas` at `size` CSS pixels (no quiet zone: the card around it gives the margin). */
export async function drawQr(canvas: HTMLCanvasElement, text: string, style: QrStyle, size: number): Promise<void> {
  if (style === 'hiddify') return drawHiddifyQr(canvas, text, { size, background: QR_CARD_COLOR })
  const scale = Math.max(1, window.devicePixelRatio || 1)
  await QRCode.toCanvas(canvas, text, {
    errorCorrectionLevel: PLAIN_LEVEL,
    margin: 0,
    width: Math.round(size * scale),
    color: { dark: '#000000', light: QR_CARD_COLOR },
  })
  // qrcode sets the canvas's CSS size to its pixel size (size × devicePixelRatio): on a phone that is 3× the
  // preview, filling the page. Show it at `size` CSS pixels like the Hiddify style.
  canvas.style.width = `${size}px`
  canvas.style.height = 'auto'
}

/** A PNG of the code with a white quiet zone, ready to save or copy. */
export async function qrPng(text: string, style: QrStyle, size = 600): Promise<Blob> {
  if (style === 'hiddify') return hiddifyQrPng(text, size)
  const canvas = document.createElement('canvas')
  await QRCode.toCanvas(canvas, text, { errorCorrectionLevel: PLAIN_LEVEL, margin: 4, width: size, color: { dark: '#000000', light: QR_CARD_COLOR } })
  return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png'))
}

/** Bytes the text takes in the code (UTF-8). */
export function utf8Length(text: string): number {
  return new TextEncoder().encode(text).length
}

/** A web address that can be opened in a new tab. */
export function isWebUrl(text: string): boolean {
  const value = text.trim()
  if (/\s/.test(value)) return false
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

/** Proxy share links (vless://, vmess://, ss://, …) or a Base64 subscription: something Text Decoders can show. */
export function isShareLinkText(text: string): boolean {
  const { text: unwrapped, unwrapped: wasSubscription } = unwrapSubscriptionText(text.trim())
  if (wasSubscription) return true
  return unwrapped
    .split(/\r?\n/)
    .map((line) => line.trim())
    .some((line) => /^[a-z][a-z0-9+.-]*:\/\/\S+/i.test(line) && !/^https?:\/\//i.test(line))
}
