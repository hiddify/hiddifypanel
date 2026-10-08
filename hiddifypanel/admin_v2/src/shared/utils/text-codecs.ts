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

/**
 * The text a string decodes to when it clearly is Base64 (standard or URL-safe, optional padding): at least 8
 * characters, valid UTF-8 and printable. Anything else (a normal word, a sentence) is null.
 */
export function decodeIfBase64(text: string): string | null {
  const compact = text.replace(/\s+/g, '')
  if (compact.length < 8 || !/^[A-Za-z0-9+/_-]+={0,2}$/.test(compact)) return null
  try {
    const padded = compact.replace(/-/g, '+').replace(/_/g, '/')
    const bytes = binaryToBytes(atob(padded + '='.repeat((4 - (padded.length % 4)) % 4)))
    const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    // eslint-disable-next-line no-control-regex
    return decoded.length > 0 && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffd]/.test(decoded) ? decoded : null
  } catch {
    return null
  }
}

/** `vmess://abc` -> ['vmess://', 'abc']: the protocol in front is not part of the Base64. */
export function splitProtocolPrefix(text: string): [string, string] {
  const match = text.match(/^\s*([a-z][a-z0-9+.-]*:\/\/)/i)
  return match ? [match[1]!, text.slice(match[0].length)] : ['', text]
}
