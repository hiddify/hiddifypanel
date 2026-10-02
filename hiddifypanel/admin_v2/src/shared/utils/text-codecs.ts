function bytesToBinary(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return binary
}

function binaryToBytes(binary: string): Uint8Array {
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

export function encodeUtf8Base64(text: string, urlSafe = false): string {
  const b64 = btoa(bytesToBinary(new TextEncoder().encode(text)))
  if (!urlSafe) return b64
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function decodeUtf8Base64(text: string): string {
  const compact = text.replace(/\s+/g, '')
  if (!compact) return ''
  const padded = compact.replace(/-/g, '+').replace(/_/g, '/')
  const withPad = padded + '='.repeat((4 - (padded.length % 4)) % 4)
  return new TextDecoder().decode(binaryToBytes(atob(withPad)))
}

export function tryDecodeUtf8Base64(text: string): string | null {
  try {
    return decodeUtf8Base64(text)
  } catch {
    return null
  }
}

export function encodeUrl(text: string): string {
  return encodeURIComponent(text)
}

export function decodeUrl(text: string): string {
  return decodeURIComponent(text.replace(/\+/g, '%20'))
}

export function safeDecodeUriComponent(text: string): string {
  try {
    return decodeURIComponent(text.replace(/\+/g, '%20'))
  } catch {
    return text
  }
}
