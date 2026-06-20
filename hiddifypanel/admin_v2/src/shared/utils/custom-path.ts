const PATH_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'

export function generateCustomPath(): string {
  let segment = ''
  const bytes = crypto.getRandomValues(new Uint8Array(12))
  for (let i = 0; i < 12; i++) {
    segment += PATH_ALPHABET[bytes[i]! % PATH_ALPHABET.length]
  }
  return `/${segment}`
}
