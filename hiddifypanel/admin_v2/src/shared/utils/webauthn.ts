/** Making a passkey in the browser (WebAuthn), with the binary fields as base64url in JSON both ways. */

export function passkeysSupported(): boolean {
  return typeof window !== 'undefined' && !!window.PublicKeyCredential && !!navigator.credentials && window.isSecureContext
}

function toB64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let s = ''
  for (const b of bytes) s += String.fromCharCode(b)
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function fromB64url(s: string): ArrayBuffer {
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4))
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out.buffer
}

interface CreationOptionsJson {
  challenge: string
  user: { id: string; name: string; displayName: string }
  excludeCredentials?: { type: 'public-key'; id: string }[]
  [key: string]: unknown
}

/** The new credential as the panel checks it (public key and authenticator data, no attestation). */
export interface NewPasskeyJson {
  id: string
  type: string
  response: { clientDataJSON: string; authenticatorData: string; publicKey: string | null; publicKeyAlgorithm: number }
}

/** Thrown when the admin closed the browser's passkey prompt (not an error to report). */
export class PasskeyCancelled extends Error {}

/** Thrown when this device already holds one of my passkeys for this domain (the panel listed it to exclude). */
export class PasskeyExists extends Error {}

/** Ask the browser (and the admin's device) for a new passkey with the panel's options. */
export async function createPasskey(json: Record<string, unknown>): Promise<NewPasskeyJson> {
  const o = json as unknown as CreationOptionsJson
  const publicKey = {
    ...o,
    challenge: fromB64url(o.challenge),
    user: { ...o.user, id: fromB64url(o.user.id) },
    excludeCredentials: (o.excludeCredentials ?? []).map((c) => ({ type: c.type, id: fromB64url(c.id) })),
  } as unknown as PublicKeyCredentialCreationOptions
  let cred: Credential | null
  try {
    cred = await navigator.credentials.create({ publicKey })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'NotAllowedError') throw new PasskeyCancelled()
    if (e instanceof DOMException && e.name === 'InvalidStateError') throw new PasskeyExists()
    throw e
  }
  if (!cred) throw new PasskeyCancelled()
  const pk = cred as PublicKeyCredential
  const r = pk.response as AuthenticatorAttestationResponse
  const key = r.getPublicKey()
  return {
    id: pk.id,
    type: pk.type,
    response: {
      clientDataJSON: toB64url(r.clientDataJSON),
      authenticatorData: toB64url(r.getAuthenticatorData()),
      publicKey: key ? toB64url(key) : null,
      publicKeyAlgorithm: r.getPublicKeyAlgorithm(),
    },
  }
}
