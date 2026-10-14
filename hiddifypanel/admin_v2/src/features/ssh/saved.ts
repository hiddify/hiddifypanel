/**
 * The SSH page's encryption for the signed-in admin (AES-GCM, key derived with PBKDF2 from the admin's uuid): what vault.ts
 * keeps in this browser, and the secret in a connection's link.
 *
 * The uuid is in the admin's own link: this keeps the secrets from lying in plain text in the browser's storage and apart
 * between admins sharing a browser; it does not protect against someone who has both this browser and that link.
 */
import { getHttp } from '@/core/api/client'

const SALT = new TextEncoder().encode('hiddify-ssh-saved-v2')
const ITERATIONS = 150_000

function b64(bytes: ArrayBuffer | Uint8Array): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
}

function unb64(text: string): Uint8Array<ArrayBuffer> {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0))
}

/** Whether this browser can keep them (Web Crypto needs HTTPS). */
export function canSave(): boolean {
  return typeof crypto !== 'undefined' && !!crypto.subtle
}

/** Encrypts for the signed-in admin only: AES-GCM with a key derived (PBKDF2) from its uuid. */
export class ConnectionCipher {
  private constructor(
    private readonly key: CryptoKey,
    /** A hash of the uuid, to name what is stored without showing the uuid. */
    readonly owner: string,
  ) {}

  static async forCurrentAdmin(): Promise<ConnectionCipher> {
    const { data } = await getHttp().get<{ uuid?: string }>('me/')
    const uuid = String(data.uuid ?? '')
    if (!uuid) throw new Error('no admin uuid')
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(uuid))
    const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(uuid), 'PBKDF2', false, ['deriveKey'])
    const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: SALT, iterations: ITERATIONS, hash: 'SHA-256' }, material, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'])
    return new ConnectionCipher(
      key,
      b64(digest)
        .replace(/[^A-Za-z0-9]/g, '')
        .slice(0, 24),
    )
  }

  /** A URL-safe token: 12 bytes of IV, then the ciphertext. */
  async seal(value: unknown): Promise<string> {
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const data = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, this.key, new TextEncoder().encode(JSON.stringify(value))))
    const all = new Uint8Array(iv.length + data.length)
    all.set(iv)
    all.set(data, iv.length)
    return b64(all).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  }

  /** Throws when the token is not this admin's (or is damaged). */
  async open<T>(token: string): Promise<T> {
    const padded = token.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((token.length + 3) % 4)
    const all = unb64(padded)
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: all.slice(0, 12) }, this.key, all.slice(12))
    return JSON.parse(new TextDecoder().decode(plain)) as T
  }
}
