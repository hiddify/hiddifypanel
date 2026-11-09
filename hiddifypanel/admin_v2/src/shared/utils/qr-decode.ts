/**
 * Reads a QR code from an image, a canvas or a video frame, in the browser (nothing is uploaded).
 * Uses the browser's own BarcodeDetector where there is one (Chrome, Edge, Android), else ZXing (WebAssembly,
 * loaded on first use). jsQR was tried and misses most dotted codes like Hiddify's; ZXing reads them.
 */

/** The part of the Shape Detection API used here (not in TypeScript's DOM types yet). */
interface DetectedBarcode {
  rawValue: string
}
interface BarcodeDetectorLike {
  detect(source: CanvasImageSource): Promise<DetectedBarcode[]>
}
interface BarcodeDetectorConstructor {
  new (options: { formats: string[] }): BarcodeDetectorLike
  getSupportedFormats(): Promise<string[]>
}

type ZxingReader = typeof import('zxing-wasm/reader')

/** Larger images are scaled down first: faster, and codes are still found at this size. */
const MAX_SIDE = 1280

let nativePromise: Promise<BarcodeDetectorLike | null> | null = null
function nativeDetector(): Promise<BarcodeDetectorLike | null> {
  nativePromise ??= (async () => {
    const Detector = (window as unknown as { BarcodeDetector?: BarcodeDetectorConstructor }).BarcodeDetector
    if (!Detector) return null
    try {
      const formats = await Detector.getSupportedFormats()
      return formats.includes('qr_code') ? new Detector({ formats: ['qr_code'] }) : null
    } catch {
      return null
    }
  })()
  return nativePromise
}

let zxingPromise: Promise<ZxingReader> | null = null
function loadZxing(): Promise<ZxingReader> {
  zxingPromise ??= Promise.all([import('zxing-wasm/reader'), import('zxing-wasm/reader/zxing_reader.wasm?url')])
    .then(([reader, wasm]) => {
      // The .wasm is served by the panel itself; by default ZXing would fetch it from a CDN.
      reader.prepareZXingModule({ overrides: { locateFile: (path: string, prefix: string) => (path.endsWith('.wasm') ? wasm.default : prefix + path) } })
      return reader
    })
    .catch((err: unknown) => {
      zxingPromise = null // let a later scan try again
      throw err
    })
  return zxingPromise
}

let scratch: HTMLCanvasElement | null = null

function sourceSize(source: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement | ImageBitmap): [number, number] {
  if (source instanceof HTMLVideoElement) return [source.videoWidth, source.videoHeight]
  if (source instanceof HTMLImageElement) return [source.naturalWidth, source.naturalHeight]
  return [source.width, source.height]
}

export interface DecodeOptions {
  /** Look harder (rotations, light-on-dark): worth it for an image file, too slow for every camera frame. */
  thorough?: boolean
}

/** The text of the first QR code found, or null when there is none. */
export async function decodeQr(
  source: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement | ImageBitmap,
  options: DecodeOptions = {},
): Promise<string | null> {
  const [width, height] = sourceSize(source)
  if (!width || !height) return null

  const native = await nativeDetector()
  if (native) {
    try {
      const found = await native.detect(source)
      if (found[0]?.rawValue) return found[0].rawValue
      if (!options.thorough) return null
      // BarcodeDetector does not read every light-on-dark code: ZXing gets a try below.
    } catch {
      // Some sources (a tainted or zero-size frame) fail natively: ZXing below.
    }
  }

  const scale = Math.min(1, MAX_SIDE / Math.max(width, height))
  const w = Math.max(1, Math.round(width * scale))
  const h = Math.max(1, Math.round(height * scale))
  scratch ??= document.createElement('canvas')
  scratch.width = w
  scratch.height = h
  const ctx = scratch.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  ctx.drawImage(source, 0, 0, w, h)
  const pixels = ctx.getImageData(0, 0, w, h)
  const { readBarcodes } = await loadZxing()
  const results = await readBarcodes(pixels, {
    formats: ['QRCode'],
    maxNumberOfSymbols: 1,
    tryHarder: !!options.thorough,
    tryInvert: !!options.thorough,
    tryRotate: !!options.thorough,
  })
  return results.find((r) => r.isValid && r.text)?.text ?? null
}

/** Reads a QR code from an image file (upload, drop or paste). */
export async function decodeQrFile(file: Blob): Promise<string | null> {
  const bitmap = await createImageBitmap(file)
  try {
    return await decodeQr(bitmap, { thorough: true })
  } finally {
    bitmap.close()
  }
}
